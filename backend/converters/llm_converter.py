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

    BASE_MAX_TOKENS = 4096
    LARGE_FILE_MAX_TOKENS = 16384
    EXTRA_LARGE_FILE_MAX_TOKENS = 32768

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
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self._completion_fn = completion_fn
        self._client = None
        self._confidence = ConfidenceCalculator()

    # ------------------------------------------------------------------ public
    def convert(self, code: str) -> ConvertResponse:
        if not code.strip():
            return self._response("", 1.0, ["No code provided"], [], level=3, extra={})

        if self._completion_fn is None and not self.api_key:
            return self._fallback(
                code,
                "GROQ_API_KEY not set. Add a valid key to the environment "
                "(the one in .env is revoked), or pass api_key/completion_fn.",
            )

        system = self._prompt_for(self.source_lang, self.target_lang)
        user = f"Convert this {self.source_lang} to {self.target_lang}:\n\n{code}"
        max_tokens = self._calculate_max_tokens(code)

        try:
            raw = self._complete(system, user, max_tokens)
        except Exception as e:  # network / auth / rate-limit / bad model
            return self._fallback(code, f"{type(e).__name__}: {e}")

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
            },
        )

    # --------------------------------------------------------------- internals
    @staticmethod
    def _prompt_for(source: str, target: str) -> str:
        return PROMPTS.get((source, target)) or _generic_prompt(source, target)

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        """Isolated LLM call. Injected in tests; hits Groq in production."""
        if self._completion_fn is not None:
            return self._completion_fn(system, user, max_tokens)
        resp = self._get_client().chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.1,          # low for near-deterministic translation
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError("groq package required: pip install groq")
            self._client = Groq(api_key=self.api_key)
        return self._client

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
        return (m.group(1) if m else raw).strip()

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
