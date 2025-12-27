"""
Test cases for Python to JavaScript conversion.

These tests demonstrate the converter's capabilities and known limitations.
"""

import sys
sys.path.insert(0, '/home/user/code-convertor/backend')

from converters.python_to_javascript import PythonToJavaScriptConverter


def test_simple_variables():
    """Test variable declaration conversion."""
    converter = PythonToJavaScriptConverter()
    code = "x = 10\ny = 20"
    result = converter.convert(code)

    assert "let x = 10;" in result.converted_code
    assert "let y = 20;" in result.converted_code
    assert result.conversion_confidence > 0.8
    print("✓ test_simple_variables passed")


def test_print_to_console_log():
    """Test print() to console.log() conversion."""
    converter = PythonToJavaScriptConverter()
    code = 'print("Hello, World!")'
    result = converter.convert(code)

    assert "console.log" in result.converted_code
    assert result.conversion_confidence > 0.7
    print("✓ test_print_to_console_log passed")


def test_f_string_conversion():
    """Test f-string to template literal conversion."""
    converter = PythonToJavaScriptConverter()
    code = 'name = "Alice"\nprint(f"Hello, {name}!")'
    result = converter.convert(code)

    assert "`Hello, ${name}!`" in result.converted_code
    assert "console.log" in result.converted_code
    print("✓ test_f_string_conversion passed")


def test_if_condition():
    """Test if condition conversion."""
    converter = PythonToJavaScriptConverter()
    code = "if x > 5:\n    print(x)"
    result = converter.convert(code)

    assert "if (x > 5)" in result.converted_code
    assert result.conversion_confidence > 0.7
    print("✓ test_if_condition passed")


def test_for_loop_range():
    """Test for loop with range conversion."""
    converter = PythonToJavaScriptConverter()
    code = "for i in range(10):\n    print(i)"
    result = converter.convert(code)

    assert "for (let i = 0; i < 10; i++)" in result.converted_code
    assert result.conversion_confidence > 0.8
    print("✓ test_for_loop_range passed")


def test_function_definition():
    """Test function definition conversion."""
    converter = PythonToJavaScriptConverter()
    code = "def greet(name):\n    print(f\"Hi, {name}!\")"
    result = converter.convert(code)

    assert "function greet(name)" in result.converted_code
    assert result.conversion_confidence > 0.7
    print("✓ test_function_definition passed")


def test_while_loop():
    """Test while loop conversion."""
    converter = PythonToJavaScriptConverter()
    code = "while x > 0:\n    print(x)\n    x = x - 1"
    result = converter.convert(code)

    assert "while (x > 0)" in result.converted_code
    assert "console.log" in result.converted_code
    print("✓ test_while_loop passed")


def test_try_except():
    """Test try/except to try/catch conversion."""
    converter = PythonToJavaScriptConverter()
    code = "try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    print('Error')"
    result = converter.convert(code)

    assert "try {" in result.converted_code
    assert "catch" in result.converted_code
    print("✓ test_try_except passed")


def test_confidence_scoring():
    """Test that confidence scoring works."""
    converter = PythonToJavaScriptConverter()
    simple = "x = 5"
    complex_code = "for i in range(10):\n    if i > 5:\n        print(i)"

    simple_result = converter.convert(simple)
    complex_result = converter.convert(complex_code)

    # Both should have high confidence for correct conversions
    assert simple_result.conversion_confidence > 0.7
    assert complex_result.conversion_confidence > 0.7
    print("✓ test_confidence_scoring passed")


def test_constants_const_keyword():
    """Test that uppercase variables use const."""
    converter = PythonToJavaScriptConverter()
    code = "MAX_SIZE = 100\nmin_size = 10"
    result = converter.convert(code)

    assert "const MAX_SIZE" in result.converted_code
    assert "let min_size" in result.converted_code
    print("✓ test_constants_const_keyword passed")


if __name__ == "__main__":
    test_simple_variables()
    test_print_to_console_log()
    test_f_string_conversion()
    test_if_condition()
    test_for_loop_range()
    test_function_definition()
    test_while_loop()
    test_try_except()
    test_confidence_scoring()
    test_constants_const_keyword()
    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
