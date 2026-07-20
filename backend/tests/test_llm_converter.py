"""
Deterministic tests for the LLM converter (Java->TS, HTML->TS).

All LLM calls are dependency-injected via `completion_fn`, so this suite runs
with NO network and NO API key. A separate, skipped-by-default integration test
(test_llm_converter_live.py) exercises the real Groq API.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converters.llm_converter import LLMConverter, PROMPTS
from core.conversion_engine import ConversionEngine


def fake_completion(return_text):
    """Build a completion_fn that ignores inputs and returns canned text."""
    def _fn(system, user, max_tokens):
        return return_text
    return _fn


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

class TestExtractCode:
    def test_typescript_fence(self):
        raw = "Here you go:\n```typescript\nconst x: number = 1;\n```\nDone."
        assert LLMConverter._extract_code(raw) == "const x: number = 1;"

    def test_bare_fence(self):
        assert LLMConverter._extract_code("```\nlet y = 2;\n```") == "let y = 2;"

    def test_no_fence_returns_stripped(self):
        assert LLMConverter._extract_code("  const z = 3;  ") == "const z = 3;"

    def test_empty(self):
        assert LLMConverter._extract_code("") == ""


# ---------------------------------------------------------------------------
# Confidence parsing
# ---------------------------------------------------------------------------

class TestExtractConfidence:
    def test_high(self):
        assert LLMConverter._extract_confidence("code\n// Conversion confidence: HIGH")[0] == 0.95

    def test_medium_with_reason(self):
        conf, reason = LLMConverter._extract_confidence(
            "code\n// Conversion confidence: MEDIUM - streams approximated")
        assert conf == 0.75 and "streams" in reason

    def test_low(self):
        assert LLMConverter._extract_confidence("code\n// Conversion confidence: LOW - threads")[0] == 0.50

    def test_unspecified_default(self):
        assert LLMConverter._extract_confidence("just code, no marker")[0] == 0.80


# ---------------------------------------------------------------------------
# convert()
# ---------------------------------------------------------------------------

class TestConvert:
    def test_java_to_ts_happy_path(self):
        ts = "```typescript\nexport function add(a: number, b: number): number {\n  return a + b;\n}\n// Conversion confidence: HIGH\n```"
        conv = LLMConverter("java", "typescript", completion_fn=fake_completion(ts))
        res = conv.convert("int add(int a, int b){ return a+b; }")
        assert res.target_language == "typescript"
        assert "export function add" in res.converted_code
        assert "```" not in res.converted_code          # fence stripped
        assert "confidence: HIGH" not in res.converted_code.lower()  # marker line not shown as code? (kept inside)
        assert res.conversion_confidence == 0.95
        assert res.metadata["method"] == "llm"

    def test_html_to_ts_pair_supported(self):
        ts = "```typescript\nexport function render(): HTMLDivElement { return document.createElement('div'); }\n// Conversion confidence: HIGH\n```"
        conv = LLMConverter("html", "typescript", completion_fn=fake_completion(ts))
        res = conv.convert("<div></div>")
        assert "render()" in res.converted_code
        assert res.conversion_confidence == 0.95

    def test_empty_input(self):
        conv = LLMConverter("java", "typescript", completion_fn=fake_completion("should not be called"))
        res = conv.convert("   ")
        assert res.converted_code == ""
        assert res.conversion_confidence == 1.0
        assert "No code provided" in res.warnings

    def test_no_key_no_fn_fallback(self, monkeypatch):
        for k in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEYS"):
            monkeypatch.delenv(k, raising=False)
        conv = LLMConverter("java", "typescript")  # no completion_fn, no key
        res = conv.convert("class A {}")
        assert res.conversion_confidence == 0.0
        assert any("GROQ" in w for w in res.warnings)

    def test_llm_error_fallback(self):
        def boom(system, user, max_tokens):
            raise RuntimeError("some raw internal vendor detail")
        conv = LLMConverter("java", "typescript", completion_fn=boom)
        res = conv.convert("class A {}")
        assert res.conversion_confidence == 0.0
        joined = " ".join(res.warnings).lower()
        assert "unavailable" in joined or "try again" in joined   # friendly message
        assert "some raw internal vendor detail" not in joined     # sanitized, no leak

    def test_empty_llm_output_fallback(self):
        conv = LLMConverter("java", "typescript", completion_fn=fake_completion("```\n\n```"))
        res = conv.convert("class A {}")
        assert res.conversion_confidence == 0.0

    def test_todo_verify_becomes_unsupported(self):
        ts = "```typescript\nconst x = 1n; // TODO: verify long fits\n// Conversion confidence: MEDIUM - long\n```"
        conv = LLMConverter("java", "typescript", completion_fn=fake_completion(ts))
        res = conv.convert("long x = 1;")
        assert len(res.unsupported_constructs) == 1
        assert "verify" in res.unsupported_constructs[0]["construct"].lower()

    def test_invalid_verdict_caps_confidence(self, monkeypatch):
        # Force the validator to report a definitive syntax failure.
        ts = "```typescript\nexport const broken = ;\n// Conversion confidence: HIGH\n```"
        conv = LLMConverter("java", "typescript", completion_fn=fake_completion(ts))
        monkeypatch.setattr(conv._confidence, "validate_output_syntax", lambda code, lang: False)
        res = conv.convert("class A {}")
        assert res.conversion_confidence <= 0.25
        assert any("failed syntax validation" in w.lower() for w in res.warnings)

    def test_any_pair_allowed_generic_prompt(self):
        # Any pair is allowed now; unknown ones use a generic translator prompt.
        ts = "```rust\nfn main() {}\n// Conversion confidence: MEDIUM - approximated\n```"
        conv = LLMConverter("cobol", "rust", completion_fn=fake_completion(ts))
        res = conv.convert("DISPLAY 'HI'.")
        assert res.target_language == "rust"
        assert "fn main" in res.converted_code


# ---------------------------------------------------------------------------
# Resilience: rate-limit handling + error sanitization (no vendor leak)
# ---------------------------------------------------------------------------

class TestResilience:
    def test_is_transient(self):
        class RateLimitError(Exception):
            pass
        assert LLMConverter._is_transient(RateLimitError("x"))
        assert LLMConverter._is_transient(Exception("got 503 from upstream"))
        assert not LLMConverter._is_transient(ValueError("bad prompt"))

    def test_friendly_error_no_vendor_leak(self):
        class RateLimitError(Exception):
            pass
        e = RateLimitError("Error code: 429 - organization org_01kfxxx ... "
                           "Upgrade at https://console.groq.com/settings/billing")
        msg = LLMConverter._friendly_error(e)
        assert "org_" not in msg and "http" not in msg and "groq.com" not in msg
        assert "rate-limited" in msg.lower()

    def test_convert_rate_limit_falls_back_sanitized(self):
        class RateLimitError(Exception):
            pass

        def boom(system, user, mt):
            raise RateLimitError("429 organization org_01kfxxx "
                                 "https://console.groq.com/settings/billing")
        res = LLMConverter("java", "python", completion_fn=boom).convert("x();")
        assert res.conversion_confidence == 0.0          # graceful, not a crash
        joined = " ".join(res.warnings)
        assert "org_" not in joined and "groq.com" not in joined and "http" not in joined
        assert "rate-limited" in joined.lower()


# ---------------------------------------------------------------------------
# Completeness guardrail: truncation + collapse detection
# ---------------------------------------------------------------------------

class TestCompleteness:
    def test_surviving_fraction(self):
        src = "def alpha(x):\n    pass\ndef beta(x):\n    pass\ndef gamma(x):\n    pass\ndef delta(x):\n    pass"
        assert LLMConverter._surviving_fraction(src, "alpha beta gamma delta", "python") == 1.0
        assert LLMConverter._surviving_fraction(src, "alpha", "python") == 0.25

    def test_collapse_detected_and_capped(self):
        src = ("def alpha(x):\n    return x\n\ndef beta(x):\n    return x\n\n"
               "def gamma(x):\n    return x\n\ndef delta(x):\n    return x")
        out = "```javascript\nfunction alpha(x){return x;}\n// Conversion confidence: HIGH\n```"
        res = LLMConverter("python", "javascript", completion_fn=fake_completion(out)).convert(src)
        assert any("incomplete" in w.lower() for w in res.warnings)
        assert res.conversion_confidence <= 0.4

    def test_faithful_not_flagged(self):
        src = "def alpha(x):\n    return x\n\ndef beta(x):\n    return x\n\ndef gamma(x):\n    return x"
        out = ("```javascript\nfunction alpha(x){return x;}\nfunction beta(x){return x;}\n"
               "function gamma(x){return x;}\n```")
        res = LLMConverter("python", "javascript", completion_fn=fake_completion(out)).convert(src)
        assert not any("incomplete" in w.lower() for w in res.warnings)

    def test_truncation_flagged_and_capped(self):
        out = "```javascript\nfunction alpha(x){return x;}\n```"
        conv = LLMConverter("python", "javascript", completion_fn=fake_completion(out))
        conv._last_finish_reason = "length"      # simulate hitting the token cap
        res = conv.convert("def alpha(x): return x")
        assert any("truncat" in w.lower() for w in res.warnings)
        assert res.conversion_confidence <= 0.4


# ---------------------------------------------------------------------------
# Multi-key rotation + failover (3-key safety net)
# ---------------------------------------------------------------------------

class TestMultiKey:
    @pytest.fixture(autouse=True)
    def _clear_keys(self, monkeypatch):
        for k in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3",
                  "GROQ_API_KEY_4", "GROQ_API_KEYS"):
            monkeypatch.delenv(k, raising=False)

    def test_collect_keys_dedupe_and_order(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "a")
        monkeypatch.setenv("GROQ_API_KEY_2", "b")
        monkeypatch.setenv("GROQ_API_KEYS", "c, a")  # 'a' duplicates the primary
        assert LLMConverter._collect_keys() == ["a", "b", "c"]
        assert LLMConverter._collect_keys("z")[0] == "z"  # explicit arg wins first slot

    def test_rotation_spreads_start(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "k1")
        monkeypatch.setenv("GROQ_API_KEY_2", "k2")
        monkeypatch.setenv("GROQ_API_KEY_3", "k3")
        conv = LLMConverter("python", "javascript")
        LLMConverter._key_cursor = 0
        starts = [conv._rotated_keys()[0] for _ in range(3)]
        assert set(starts) == {"k1", "k2", "k3"}  # each key leads once

    def test_failover_to_next_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "k1")
        monkeypatch.setenv("GROQ_API_KEY_2", "k2")
        LLMConverter._key_cursor = 0
        conv = LLMConverter("python", "javascript")
        tried = []

        class RateLimitError(Exception):
            pass

        def fake(key, system, user, mt):
            tried.append(key)
            if key == "k1":
                raise RateLimitError("429 rate limit")
            return "```javascript\nlet x = 1;\n```"
        monkeypatch.setattr(conv, "_call_key", fake)
        out = conv._complete("sys", "usr", 100)
        assert "let x = 1" in out
        assert tried == ["k1", "k2"]  # transparently failed over

    def test_all_keys_rate_limited_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "k1")
        monkeypatch.setenv("GROQ_API_KEY_2", "k2")
        LLMConverter._key_cursor = 0
        conv = LLMConverter("python", "javascript")

        class RateLimitError(Exception):
            pass

        def boom(*a, **kw):   # **kw: _call_key now takes an optional model=
            raise RateLimitError("429")
        monkeypatch.setattr(conv, "_call_key", boom)
        monkeypatch.setattr(conv, "_retry_wait", lambda e, a: 0)  # no real sleep
        with pytest.raises(RateLimitError):
            conv._complete("s", "u", 10)  # exhausts pool -> engine falls back


# ---------------------------------------------------------------------------
# Engine wiring
# ---------------------------------------------------------------------------

class TestEngineWiring:
    def test_pairs_registered(self):
        pairs = ConversionEngine().get_supported_pairs()
        assert "java -> typescript" in pairs
        assert "html -> typescript" in pairs

    def test_engine_supports_pairs_and_has_fallbacks(self):
        eng = ConversionEngine()
        # LLM pairs are supported...
        assert eng._is_supported("java", "typescript")
        assert eng._is_supported("html", "typescript")
        assert eng._is_supported("java", "python")   # was "undefined" before
        # ...rule-based fallbacks still exist for the core pairs...
        assert ("python", "javascript") in eng.rule_based
        # ...and a language we don't offer is rejected.
        assert not eng._is_supported("python", "cobol")

    def test_prompts_exist_for_both_pairs(self):
        assert ("java", "typescript") in PROMPTS
        assert ("html", "typescript") in PROMPTS
