"""
Live integration test for the LLM converter (hits the real Groq API).

Skipped unless GROQ_API_KEY is set in the environment, so the default test run
never makes a paid API call. Run explicitly with:

    set GROQ_API_KEY=...   (Windows)   /   export GROQ_API_KEY=...  (Unix)
    python -m pytest tests/test_llm_converter_live.py -v -s
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converters.llm_converter import LLMConverter

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set; skipping live Groq API test",
)


def test_java_to_typescript_live():
    java = (
        "public class Calc {\n"
        "    public int add(int a, int b) { return a + b; }\n"
        "    public String greet(String n) { return \"Hi \" + n; }\n"
        "}"
    )
    res = LLMConverter("java", "typescript").convert(java)
    assert res.target_language == "typescript"
    assert res.metadata.get("method") == "llm"
    assert res.conversion_confidence > 0.5
    # idiomatic TS markers we asked for
    assert ": number" in res.converted_code
    assert ": string" in res.converted_code
    assert "```" not in res.converted_code


def test_html_to_typescript_live():
    html = '<div class="card"><h2>Hi</h2><button>Go</button></div>'
    res = LLMConverter("html", "typescript").convert(html)
    assert res.target_language == "typescript"
    assert res.conversion_confidence > 0.4
    assert "createElement" in res.converted_code
