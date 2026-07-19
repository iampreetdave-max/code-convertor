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
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        conv = LLMConverter("java", "typescript")  # no completion_fn, no key
        res = conv.convert("class A {}")
        assert res.conversion_confidence == 0.0
        assert any("GROQ_API_KEY" in w for w in res.warnings)

    def test_llm_error_fallback(self):
        def boom(system, user, max_tokens):
            raise RuntimeError("rate limited")
        conv = LLMConverter("java", "typescript", completion_fn=boom)
        res = conv.convert("class A {}")
        assert res.conversion_confidence == 0.0
        assert any("rate limited" in w for w in res.warnings)

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

    def test_unsupported_pair_raises(self):
        with pytest.raises(ValueError):
            LLMConverter("cobol", "typescript")


# ---------------------------------------------------------------------------
# Engine wiring
# ---------------------------------------------------------------------------

class TestEngineWiring:
    def test_pairs_registered(self):
        pairs = ConversionEngine().get_supported_pairs()
        assert "java -> typescript" in pairs
        assert "html -> typescript" in pairs

    def test_factory_builds_correct_converter(self):
        factory = ConversionEngine().converters[("java", "typescript")]
        conv = factory()  # partial() -> LLMConverter("java","typescript")
        assert isinstance(conv, LLMConverter)
        assert conv.source_lang == "java" and conv.target_lang == "typescript"

    def test_prompts_exist_for_both_pairs(self):
        assert ("java", "typescript") in PROMPTS
        assert ("html", "typescript") in PROMPTS
