"""
Tests for REAL (compile-checked) confidence scoring.

Confidence used to be cosmetic: broken output scored ~0.95 with zero warnings.
Now, when CODECONV_COMPILE_CHECK is on, the output is parsed in the target
language (ast/node/javac); a definitive parse failure caps confidence at LOW and
raises a warning. These tests re-enable checking (conftest.py disables it for the
rest of the suite) and verify the behaviour.

The Python-target cases use the stdlib `ast` parser and are fully deterministic
(no external tool). The JavaScript cases skip when `node` is not installed.
"""

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.confidence_calculator import ConfidenceCalculator
from converters.python_to_javascript import PythonToJavaScriptConverter
from converters.javascript_to_python import JavaScriptToPythonConverter


@pytest.fixture
def compile_check_on(monkeypatch):
    """Enable real compile-checking for a single test."""
    monkeypatch.setenv("CODECONV_COMPILE_CHECK", "1")


HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not installed")

try:
    import tree_sitter_language_pack  # noqa: F401
    HAS_TS = True
except Exception:
    HAS_TS = False
needs_ts = pytest.mark.skipif(not HAS_TS, reason="tree-sitter-language-pack not installed")


@needs_ts
class TestTreeSitterValidation:
    """tree-sitter parse-check lights up TS/go/rust/cpp/etc. output validation."""

    def test_valid_typescript(self):
        assert ConfidenceCalculator._validate_treesitter(
            "function f(x: number): number { return x + 1; }", "typescript") is True

    def test_broken_typescript(self):
        assert ConfidenceCalculator._validate_treesitter(
            "function f(x: number): number { return x + ; }", "typescript") is False

    def test_valid_go(self):
        assert ConfidenceCalculator._validate_treesitter(
            "package main\nfunc main() { println(\"hi\") }\n", "go") is True

    def test_broken_rust(self):
        assert ConfidenceCalculator._validate_treesitter(
            "fn main() { let x = ; }", "rust") is False

    def test_unknown_language_none(self):
        assert ConfidenceCalculator._validate_treesitter("whatever", "klingon") is None

    def test_via_validate_output_syntax(self, compile_check_on):
        calc = ConfidenceCalculator()
        assert calc.validate_output_syntax("package main\nfunc main() {}\n", "go") is True
        assert calc.validate_output_syntax("fn main() { let x = ; }", "rust") is False


# ---------------------------------------------------------------------------
# Core: validate_output_syntax (Python target = stdlib ast, deterministic)
# ---------------------------------------------------------------------------

class TestValidateOutputSyntax:

    def test_valid_python_true(self, compile_check_on):
        calc = ConfidenceCalculator()
        assert calc.validate_output_syntax("def f(x):\n    return x + 1\n", "python") is True

    def test_invalid_python_false(self, compile_check_on):
        calc = ConfidenceCalculator()
        # stray closing brace -> not valid Python
        assert calc.validate_output_syntax("def f(x):\n    return x\n}\n", "python") is False

    def test_disabled_returns_none(self, monkeypatch):
        monkeypatch.setenv("CODECONV_COMPILE_CHECK", "0")
        calc = ConfidenceCalculator()
        # Even blatantly invalid code returns None when checking is disabled.
        assert calc.validate_output_syntax("def f(:\n}", "python") is None

    def test_empty_returns_none(self, compile_check_on):
        calc = ConfidenceCalculator()
        assert calc.validate_output_syntax("   ", "python") is None

    def test_oversize_skipped(self, compile_check_on):
        calc = ConfidenceCalculator()
        big = "x = 1\n" * (ConfidenceCalculator.MAX_VALIDATION_BYTES // 2)  # > cap
        assert calc.validate_output_syntax(big, "python") is None

    def test_unknown_language_none(self, compile_check_on):
        calc = ConfidenceCalculator()
        # cobol has no validator (not python/js/ts/java and not a tree-sitter grammar)
        assert calc.validate_output_syntax("anything", "cobol") is None

    @needs_node
    def test_valid_javascript_true(self, compile_check_on):
        calc = ConfidenceCalculator()
        assert calc.validate_output_syntax("function f(x) {\n  return x + 1;\n}\n", "javascript") is True

    @needs_node
    def test_invalid_javascript_false(self, compile_check_on):
        calc = ConfidenceCalculator()
        assert calc.validate_output_syntax("function f(x) {\n  return x +;\n}\n", "javascript") is False


# ---------------------------------------------------------------------------
# calculate(): a definitive parse failure caps confidence at LOW
# ---------------------------------------------------------------------------

class TestCalculatePenalty:

    def test_invalid_capped_low(self):
        calc = ConfidenceCalculator()
        conf = calc.calculate("x = 1", "let x = 1;", syntax_valid=False)
        assert conf <= 0.25

    def test_valid_not_penalized(self):
        calc = ConfidenceCalculator()
        conf = calc.calculate("x = 1", "let x = 1;", syntax_valid=True)
        assert conf > 0.25

    def test_none_is_legacy_behaviour(self):
        calc = ConfidenceCalculator()
        # No target, no verdict -> identical to the old heuristic (no penalty).
        conf = calc.calculate("x = 1", "let x = 1;")
        assert conf > 0.25


# ---------------------------------------------------------------------------
# End-to-end through the converters
# ---------------------------------------------------------------------------

class TestConverterIntegration:

    def test_invalid_js_to_python_low_confidence_and_warning(self, compile_check_on):
        # JS block close leaves a stray '}' -> invalid Python (audit defect C3).
        js = "function add(a, b) {\n  return a + b;\n}\n"
        res = JavaScriptToPythonConverter().convert(js)
        # Only meaningful if the converter really produced invalid Python.
        calc = ConfidenceCalculator()
        if calc.validate_output_syntax(res.converted_code, "python") is False:
            assert res.conversion_confidence <= 0.25
            assert any("syntax validation" in w.lower() for w in res.warnings), \
                "expected a syntax-validation warning on broken output"

    def test_valid_js_to_python_no_syntax_warning(self, compile_check_on):
        js = "x = 5;\n"
        res = JavaScriptToPythonConverter().convert(js)
        # This trivially-valid conversion must not be flagged as a syntax failure.
        assert not any("failed syntax validation" in w.lower() for w in res.warnings)

    @needs_node
    def test_blank_line_bug_flagged(self, compile_check_on):
        # Blank line inside a function breaks brace placement (audit defect C1).
        py = "def f():\n    x = 1\n\n    return x\n"
        res = PythonToJavaScriptConverter().convert(py)
        calc = ConfidenceCalculator()
        if calc.validate_output_syntax(res.converted_code, "javascript") is False:
            assert res.conversion_confidence <= 0.25
            assert any("syntax validation" in w.lower() for w in res.warnings)

    @needs_node
    def test_clean_py_to_js_high_confidence(self, compile_check_on):
        py = "def add(a, b):\n    return a + b\n"
        res = PythonToJavaScriptConverter().convert(py)
        # Clean conversion should parse and keep a healthy confidence.
        assert res.conversion_confidence > 0.5
        assert not any("failed syntax validation" in w.lower() for w in res.warnings)

    @needs_node
    def test_reused_instance_does_not_leak_warnings(self, compile_check_on):
        # Converting broken code then clean code on the SAME instance must not
        # leave the broken code's syntax-validation warning on the clean result.
        conv = PythonToJavaScriptConverter()
        conv.convert("def f():\n    x = 1\n\n    return x\n")  # broken (blank line)
        clean = conv.convert("def add(a, b):\n    return a + b\n")  # clean
        assert not any("failed syntax validation" in w.lower() for w in clean.warnings)
        assert clean.conversion_confidence > 0.5
