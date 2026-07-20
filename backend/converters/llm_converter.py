"""
LLM-based converter for language pairs where rule-based transpilation cannot
produce readable, correct output (Java->TypeScript, HTML->TypeScript).

Design notes:
- Provider is Groq (OpenAI-compatible chat API); the completion call is isolated
  in `_complete` and can be dependency-injected via `completion_fn` so the unit
  tests run deterministically with NO network and NO API key.
- Output is validated (when a target-language validator is available) through the
  shared ConfidenceCalculator, so confidence reflects "does it parse", not the
  model's self-assessment alone.
- Readable output is the whole product here, so the prompts carry explicit
  type-mapping + idiom rules (Java statics -> TS, drop `throws`, merge overloads,
  enums -> classes, packages -> ES modules, etc.).

ponytail: single-shot per request (no chunking). Fine for single-file/class
inputs; large multi-file repos need tree-sitter dependency-ordered chunking —
add when inputs actually exceed the model context, not before.
"""

import os
import re
import time
from typing import Callable, Optional

from api.models import ConvertResponse
from utils.confidence_calculator import ConfidenceCalculator

# Default Groq model. Override with the GROQ_MODEL env var or the `model` arg.
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

_SHARED_TAIL = """
## FIDELITY (CRITICAL)
Translate the ENTIRE input faithfully - convert EVERY function, class, statement
and declaration, one for one, in the same order. Do NOT summarize, merge,
deduplicate, refactor, generalize, or omit anything, even if the input is long or
repetitive. The output must contain an equivalent of every top-level item in the
input. Never replace repeated code with a single generalized version.
Preserve comments AS comments in the target's comment syntax - NEVER turn
commented-out code into executable code, and do not invent extra scaffolding,
test calls, or a `main` that the input did not contain.

## OUTPUT FORMAT
Return ONLY the converted code inside a single ```{fence} code fence. No prose
before or after. On the LAST line inside the fence add exactly:
// Conversion confidence: HIGH|MEDIUM|LOW - <short reason if not HIGH>
where HIGH = every construct has a clean equivalent, MEDIUM = some constructs
were approximated, LOW = significant constructs have no faithful equivalent.
Mark any lossy/uncertain spot with an inline `// TODO: verify` comment.
"""

_JAVA_TO_TS_PROMPT = """You are an expert code translator converting Java to clean, idiomatic, COMPILABLE TypeScript.

Translate semantics, not syntax. Produce TypeScript a human would happily maintain.

## TYPE MAPPING
- `int`,`short`,`byte`,`double`,`float` -> `number`;  `long` -> `bigint` (or `number` with a `// TODO: verify` if it clearly fits 53 bits)
- `boolean` -> `boolean`;  `char`/`String` -> `string`;  `void` -> `void`;  `Object` -> `unknown`
- `List<T>`/arrays -> `T[]`;  `Map<K,V>` -> `Map<K,V>`;  `Set<T>` -> `Set<T>`
- generics carry over 1:1;  `Optional<T>` -> `T | undefined`

## STRUCTURE & IDIOM
- `package a.b.c;` -> ES modules; keep imports as `import { X } from "./x";`
- classes/interfaces/abstract classes -> TS equivalents (near 1:1)
- `enum` -> a TS class with static instances if it has fields/methods, else a TS `enum`
- method OVERLOADS: TS has no runtime overloading -> merge into one implementation with a union-typed param (or TS overload signatures)
- drop checked-exception `throws` clauses; translate try/catch/finally faithfully
- `System.out.println(x)` -> `console.log(x)`;  getters/setters stay as methods
- static methods/fields -> `static`;  `final` field -> `readonly`

## SEMANTIC HAZARDS (translate but mark `// TODO: verify`)
- `int`/`long` overflow and integer division (JS `number` has neither)
- objects used as Map/Set KEYS rely on `equals`/`hashCode` (JS Map/Set key by reference)
- `Stream` laziness; concurrency (`Thread`/`synchronized`/`ExecutorService` have NO faithful mapping)
""" + _SHARED_TAIL.format(fence="typescript")

_HTML_TO_TS_PROMPT = """You are an expert front-end engineer converting an HTML fragment/document into clean, idiomatic, type-safe TypeScript.

Goal: emit framework-NEUTRAL TypeScript that builds this markup with the typed DOM API, so the result can render in any page.

## RULES
- Export a single function `render(): HTMLElement` (or `HTMLElement[]` for multiple roots) that creates and returns the DOM.
- Use `document.createElement` with correct element types (e.g. `HTMLButtonElement`, `HTMLInputElement`); set properties via typed props (`el.className`, `el.textContent`, `el.type`), not raw string concatenation.
- Map attributes: `class` -> `className`, `for` -> `htmlFor`, inline `style="..."` -> individual `el.style.*` assignments, `onclick="..."` -> `el.addEventListener("click", ...)` with a `// TODO: verify` on inline handler bodies.
- Preserve nesting/order; append children with `append(...)`.
- Escape/keep text content as `textContent` (never `innerHTML`) unless the source clearly contains intentional markup, then mark `// TODO: verify` (XSS).
- Keep it readable: one variable per element, grouped by parent.
""" + _SHARED_TAIL.format(fence="typescript")

PROMPTS = {
    ("java", "typescript"): _JAVA_TO_TS_PROMPT,
    ("html", "typescript"): _HTML_TO_TS_PROMPT,
}

# Readable language names for the generic prompt.
_LANG_NAMES = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "html": "HTML", "cpp": "C++", "csharp": "C#", "c": "C",
    "go": "Go", "rust": "Rust", "ruby": "Ruby", "php": "PHP", "kotlin": "Kotlin",
    "swift": "Swift",
}


def _generic_prompt(source: str, target: str) -> str:
    """A solid default prompt for any language pair without a specialized one."""
    s = _LANG_NAMES.get(source, source)
    t = _LANG_NAMES.get(target, target)
    return f"""You are an expert polyglot code translator converting {s} to clean, idiomatic, CORRECT {t}.

Translate SEMANTICS faithfully - produce code a professional {t} developer would actually write, not a literal token-by-token swap.

## RULES
- Map data structures, standard-library calls, and idioms to their natural {t} equivalents.
- Preserve behavior exactly. Keep names/structure recognizable.
- If the {s} input is a standalone script, emit a runnable {t} program (add the entry point / `main` / imports / class wrapper that {t} requires).
- Where a {s} construct has no faithful {t} equivalent, translate the closest form and mark it with a `// TODO: verify` (or the {t} comment syntax) instead of silently guessing.
- Do not invent APIs. Prefer the {t} standard library.
""" + _SHARED_TAIL.format(fence=target)


class LLMConverter:
    """Groq-backed LLM converter for a specific (source_lang, target_lang) pair."""

    # Small, fast model with a much higher free-tier TPM allowance. Used only
    # when the primary model is rate-limited (large files on the free tier).
    FALLBACK_MODEL = os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")

    BASE_MAX_TOKENS = 4096
    LARGE_FILE_MAX_TOKENS = 16384
    EXTRA_LARGE_FILE_MAX_TOKENS = 32768

    # Multi-key rotation + failover: each free Groq key has its own tokens/min
    # budget, so N keys ~= Nx headroom AND a live key survives one going down.
    _CLIENTS: dict = {}   # key -> Groq client (cached)
    _key_cursor = 0       # class-level round-robin start, spreads load across keys

    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        completion_fn: Optional[Callable[[str, str, int], str]] = None,
    ):
        """
        Args:
            source_lang, target_lang: language pair; must be in PROMPTS.
            api_key: Groq key; defaults to GROQ_API_KEY env var.
            model: Groq model id (override via GROQ_MODEL env var).
            completion_fn: (system_prompt, user_prompt, max_tokens) -> raw text.
                Injected in tests to avoid any network/API-key dependency.
        """
        self.source_lang = source_lang.lower()
        self.target_lang = target_lang.lower()
        # Any pair is allowed: specialized prompt if we have one, else a generic
        # translator prompt (LLMs handle mainstream languages in any direction).
        self._keys = self._collect_keys(api_key)
        self.api_key = self._keys[0] if self._keys else None  # back-compat
        self.model = model
        self._completion_fn = completion_fn
        self._confidence = ConfidenceCalculator()
        self._last_finish_reason = None  # set by _complete on the real API path

    # ------------------------------------------------------------------ public
    def convert(self, code: str) -> ConvertResponse:
        if not code.strip():
            return self._response("", 1.0, ["No code provided"], [], level=3, extra={})

        if self._completion_fn is None and not self._keys:
            return self._fallback(
                code,
                "No GROQ API key set. Add GROQ_API_KEY (and optionally "
                "GROQ_API_KEY_2/3 for more headroom) to the environment.",
            )

        system = self._prompt_for(self.source_lang, self.target_lang)
        user = f"Convert this {self.source_lang} to {self.target_lang}:\n\n{code}"
        max_tokens = self._calculate_max_tokens(code)

        try:
            raw = self._complete(system, user, max_tokens)
        except Exception as e:  # network / auth / rate-limit / bad model
            return self._fallback(code, self._friendly_error(e))

        converted = self._extract_code(raw)
        if not converted.strip():
            return self._fallback(code, "LLM returned an empty conversion.")

        self_conf, reason = self._extract_confidence(raw)
        converted = self._strip_confidence_marker(converted)  # keep output clean
        warnings = []
        if reason:
            warnings.append(f"Model confidence: {reason}")

        # Authoritative override: does the output actually parse in the target?
        syntax_valid = self._confidence.validate_output_syntax(converted, self.target_lang)
        if syntax_valid is False:
            confidence = min(self_conf, 0.25)
            warnings.insert(
                0,
                f"Converted {self.target_lang} failed syntax validation - output "
                f"does not parse and needs manual correction.",
            )
        else:
            confidence = self_conf
            if syntax_valid is None:
                warnings.append(
                    f"Output not syntax-validated (no {self.target_lang} validator "
                    f"available); confidence is the model's self-report."
                )

        # Two failure modes the syntax check can't see:
        #  - TRUNCATION: the model hit the output-token cap -> output cut off.
        #  - COLLAPSE: the model summarized instead of translating 1:1.
        truncated = self._last_finish_reason == "length"
        if truncated:
            warnings.insert(0, "Output was truncated at the token limit - the conversion "
                              "is likely incomplete. Convert it in smaller pieces.")
        survival = self._surviving_fraction(code, converted, self.source_lang)
        if survival < 0.70:
            warnings.insert(0, f"Conversion may be incomplete - only {survival:.0%} of source "
                              f"declarations were found in the output. Try smaller pieces.")
        if truncated or survival < 0.70:
            confidence = min(confidence, 0.4)

        unsupported = self._detect_unsupported(converted)
        return self._response(
            converted, confidence, warnings, unsupported, level=3,
            extra={
                "method": "llm",
                "provider": "groq",
                "model": self.model,
                "source_lines": len(code.splitlines()),
                "target_lines": len(converted.splitlines()),
                "syntax_validated": syntax_valid,
                "finish_reason": self._last_finish_reason,
                "name_survival": round(survival, 2),
            },
        )

    # --------------------------------------------------------------- internals
    @staticmethod
    def _prompt_for(source: str, target: str) -> str:
        return PROMPTS.get((source, target)) or _generic_prompt(source, target)

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        """
        Isolated LLM call. Injected in tests; hits Groq in production.
        Retries transient failures (rate-limit / timeout / 5xx) with a short,
        capped backoff so a small burst of demo conversions recovers instead of
        returning a blank box. Persistent failures propagate to the caller, which
        falls back to the rule-based converter or a friendly error.
        """
        if self._completion_fn is not None:
            return self._completion_fn(system, user, max_tokens)
        keys = self._rotated_keys()
        if not keys:
            raise RuntimeError("No GROQ API key configured.")
        last_err = None
        # Two passes over the key pool: a rate-limited or dead key is skipped and
        # the next key tried immediately; a brief backoff separates the two passes.
        for pass_i in range(2):
            for key in keys:
                try:
                    return self._call_key(key, system, user, max_tokens)
                except Exception as e:
                    last_err = e
                    if self._is_transient(e) or self._is_auth(e):
                        continue          # this key is rate-limited/bad -> next key
                    raise                 # genuine error (bad request) -> surface it
            if pass_i == 0:
                time.sleep(self._retry_wait(last_err, 0))

        # Last resort: the big model is rate-limited (free-tier tokens-per-minute
        # is the usual culprit on large files). Retry once on a small, fast model
        # with a much higher TPM allowance — a slightly weaker conversion beats a
        # blank box during a demo.
        if self._is_transient(last_err) and self.model != self.FALLBACK_MODEL:
            for key in keys:
                try:
                    return self._call_key(key, system, user, max_tokens,
                                          model=self.FALLBACK_MODEL)
                except Exception as e:
                    last_err = e
        raise last_err

    def _call_key(self, key: str, system: str, user: str, max_tokens: int,
                  model: Optional[str] = None) -> str:
        resp = self._client_for(key).chat.completions.create(
            model=model or self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        self._last_finish_reason = getattr(choice, "finish_reason", None)
        return choice.message.content or ""

    @staticmethod
    def _collect_keys(explicit: Optional[str] = None) -> list:
        """All configured Groq keys: explicit arg, GROQ_API_KEY, GROQ_API_KEY_2..7,
        and a comma-separated GROQ_API_KEYS. De-duped, order preserved."""
        raw = [explicit, os.environ.get("GROQ_API_KEY")]
        raw += [os.environ.get(f"GROQ_API_KEY_{i}") for i in range(2, 8)]
        csv = os.environ.get("GROQ_API_KEYS")
        if csv:
            raw += [p.strip() for p in csv.split(",")]
        seen, out = set(), []
        for k in raw:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def _rotated_keys(self) -> list:
        """Round-robin the starting key each call so load spreads across keys."""
        keys = self._keys
        if not keys:
            return []
        start = LLMConverter._key_cursor % len(keys)
        LLMConverter._key_cursor = (LLMConverter._key_cursor + 1) % 100000
        return keys[start:] + keys[:start]

    def _client_for(self, key: str):
        client = LLMConverter._CLIENTS.get(key)
        if client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError("groq package required: pip install groq")
            client = Groq(api_key=key, timeout=30.0, max_retries=0)
            LLMConverter._CLIENTS[key] = client
        return client

    @staticmethod
    def _is_auth(e: Exception) -> bool:
        name = type(e).__name__
        s = str(e)
        return ("Authentication" in name or "Permission" in name
                or " 401" in s or " 403" in s)

    @staticmethod
    def _is_transient(e: Exception) -> bool:
        name = type(e).__name__
        s = str(e)
        return ("RateLimit" in name or "APITimeout" in name or "Timeout" in name
                or "APIConnection" in name or "InternalServer" in name
                or " 429" in s or " 500" in s or " 502" in s or " 503" in s)

    @staticmethod
    def _retry_wait(e: Exception, attempt: int) -> float:
        """Respect a Retry-After header if present (capped), else exp backoff."""
        try:
            resp = getattr(e, "response", None)
            if resp is not None:
                hdr = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                if hdr:
                    return min(float(hdr), 12.0)
        except Exception:
            pass
        return min(2.0 * (2 ** attempt), 12.0)  # 2s, 4s (capped 12s)

    @staticmethod
    def _friendly_error(e: Exception) -> str:
        """Human-readable message that NEVER leaks raw vendor text (org id / billing URL)."""
        name = type(e).__name__
        s = str(e)
        if "RateLimit" in name or " 429" in s:
            return ("The AI service is rate-limited right now (free-tier "
                    "tokens-per-minute cap). Please wait a few seconds and retry.")
        if "Authentication" in name or "Permission" in name or " 401" in s or " 403" in s:
            return "The AI service rejected the API key. Check GROQ_API_KEY."
        if "APITimeout" in name or "Timeout" in name or "APIConnection" in name:
            return "The AI service did not respond in time. Please try again."
        return f"AI service error ({name}). Please try again."

    def _calculate_max_tokens(self, code: str) -> int:
        lines = len(code.splitlines())
        est = int((len(code) / 4) * 2.5)  # ~4 chars/token, output ~2.5x input
        if lines > 1000 or est > 20000:
            return self.EXTRA_LARGE_FILE_MAX_TOKENS
        if lines > 500 or est > 10000:
            return self.LARGE_FILE_MAX_TOKENS
        return max(self.BASE_MAX_TOKENS, est + 1000)

    @staticmethod
    def _extract_code(raw: str) -> str:
        """Pull code out of a ```lang ... ``` fence if present, else return raw."""
        if not raw:
            return ""
        m = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", raw, re.DOTALL)
        if m:
            return m.group(1).strip()
        # One-sided / unclosed fence (model omitted the closer): strip what's there.
        s = raw.strip()
        s = re.sub(r"^```[a-zA-Z]*\s*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
        return s.strip()

    @staticmethod
    def _strip_confidence_marker(code: str) -> str:
        """Remove the `Conversion confidence: ...` meta line in any comment style
        (//, #, --, /* */, <!-- -->), so it never leaks into the output."""
        kept = [l for l in code.splitlines()
                if "conversion confidence:" not in l.lower()]
        return "\n".join(kept).rstrip()

    @staticmethod
    def _extract_confidence(raw: str) -> "tuple[float, str]":
        for line in reversed(raw.strip().splitlines()[-6:]):
            low = line.lower()
            if "conversion confidence:" in low:
                reason = line.split(" - ", 1)[1].strip() if " - " in line else ""
                if "high" in low:
                    return 0.95, ""
                if "medium" in low:
                    return 0.75, reason or "some constructs approximated"
                if "low" in low:
                    return 0.50, reason or "significant constructs have no faithful equivalent"
        return 0.80, ""  # unspecified -> cautious default

    # --- completeness guardrail: did the source's declarations survive? --------
    _NAME_PATTERNS = {
        "python": [r"^\s*def\s+(\w+)", r"^\s*class\s+(\w+)"],
        "javascript": [r"\bfunction\s+(\w+)", r"\bclass\s+(\w+)",
                       r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\("],
        "typescript": [r"\bfunction\s+(\w+)", r"\bclass\s+(\w+)", r"\binterface\s+(\w+)",
                       r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\("],
        "java": [r"\bclass\s+(\w+)", r"\b(?:public|private|protected|static|final)\s+[\w<>\[\]]+\s+(\w+)\s*\("],
        "csharp": [r"\bclass\s+(\w+)", r"\b(?:public|private|protected|static)\s+[\w<>\[\]]+\s+(\w+)\s*\("],
        "cpp": [r"\bclass\s+(\w+)"],
        "go": [r"\bfunc\s+(?:\([^)]*\)\s*)?(\w+)", r"\btype\s+(\w+)"],
        "rust": [r"\bfn\s+(\w+)", r"\bstruct\s+(\w+)", r"\benum\s+(\w+)"],
        "ruby": [r"\bdef\s+(\w+)", r"\bclass\s+(\w+)"],
        "php": [r"\bfunction\s+(\w+)", r"\bclass\s+(\w+)"],
    }
    _GENERIC_NAME_PATTERN = r"\b(?:def|function|func|fn|class|struct)\s+(\w+)"

    @staticmethod
    def _norm(name: str) -> str:
        return name.replace("_", "").lower()  # snake_case ~= camelCase

    @classmethod
    def _extract_names(cls, code: str, lang: str) -> set:
        pats = cls._NAME_PATTERNS.get((lang or "").lower(), [cls._GENERIC_NAME_PATTERN])
        names = set()
        for p in pats:
            for m in re.findall(p, code, re.MULTILINE):
                if m and m not in ("__init__", "constructor", "main"):
                    names.add(m)
        return names

    @classmethod
    def _surviving_fraction(cls, src: str, out: str, src_lang: str) -> float:
        """Fraction of source declaration names present as identifiers in output."""
        names = cls._extract_names(src, src_lang)
        if len(names) < 3:
            return 1.0  # too few to reliably detect a collapse
        out_ids = {cls._norm(t) for t in re.findall(r"[A-Za-z_]\w*", out)}
        present = sum(1 for n in names if cls._norm(n) in out_ids)
        return present / len(names)

    @staticmethod
    def _detect_unsupported(code: str) -> list:
        out = []
        for i, line in enumerate(code.splitlines(), 1):
            if "// TODO" in line and "verify" in line.lower():
                out.append({
                    "line": i,
                    "construct": line.strip(),
                    "type": "warning",
                    "description": "LLM flagged this spot for manual verification.",
                })
        return out

    def _response(self, code, confidence, warnings, unsupported, level, extra) -> ConvertResponse:
        return ConvertResponse(
            converted_code=code,
            source_language=self.source_lang,
            target_language=self.target_lang,
            conversion_confidence=confidence,
            warnings=warnings,
            unsupported_constructs=unsupported,
            unsupported_lines_count=len([u for u in unsupported if u.get("type") == "error"]),
            conversion_level=level,
            metadata={"method": "llm", "model": self.model, **extra},
        )

    def _fallback(self, code: str, error: str) -> ConvertResponse:
        return ConvertResponse(
            converted_code="",
            source_language=self.source_lang,
            target_language=self.target_lang,
            conversion_confidence=0.0,
            warnings=[f"LLM conversion unavailable: {error}"],
            unsupported_constructs=[],
            unsupported_lines_count=0,
            conversion_level=0,
            metadata={"method": "llm", "model": self.model, "error": error},
        )
