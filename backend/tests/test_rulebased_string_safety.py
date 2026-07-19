"""
Regression: the rule-based converter (used as the offline fallback) must not
rewrite operators/keywords INSIDE string literals. QA found
`"a == b and None"` becoming `"a === b && null"` — silent data corruption.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converters.python_to_javascript import PythonToJavaScriptConverter


def _convert(code):
    return PythonToJavaScriptConverter().convert(code).converted_code


def test_string_contents_preserved_in_return():
    out = _convert('def tricky():\n    return "a == b and None"')
    assert '"a == b and None"' in out          # literal untouched
    assert '===' not in out and '&&' not in out and 'null' not in out


def test_string_contents_preserved_in_assignment():
    out = _convert('x = "a == b and None"')
    assert '"a == b and None"' in out


def test_operator_outside_string_still_converts():
    out = _convert('if a == b:\n    pass')
    assert '===' in out                         # real operator converted


def test_mixed_real_and_string_operator():
    out = _convert('flag = a == b')
    assert 'a === b' in out                      # real == converted
    out2 = _convert('label = "x == y"')
    assert '"x == y"' in out2                     # string == preserved


def test_syntax_validated_in_metadata():
    # metadata now records the validator verdict (was missing on rule-based path)
    res = PythonToJavaScriptConverter().convert("x = 5\nprint(x)")
    assert "syntax_validated" in res.metadata
