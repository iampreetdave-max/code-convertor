"""
Comprehensive tests for closing brace handling in Python to JavaScript conversion.

These tests verify that closing braces are properly inserted when indentation decreases.
"""

import sys
sys.path.insert(0, '/home/user/code-convertor/backend')

from converters.python_to_javascript import PythonToJavaScriptConverter


def test_simple_if_closing_brace():
    """Test closing brace for simple if statement."""
    converter = PythonToJavaScriptConverter()
    code = "if x > 5:\n    print(x)\nprint('done')"
    result = converter.convert(code)

    # Must have both opening and closing braces
    assert "{" in result.converted_code, "Missing opening brace"
    assert "}" in result.converted_code, "Missing closing brace"

    # Braces must be balanced
    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, \
        f"Unbalanced braces: {opening_count} opening, {closing_count} closing"

    assert result.conversion_confidence > 0.7, \
        f"Low confidence: {result.conversion_confidence}"

    print("✓ test_simple_if_closing_brace passed")


def test_nested_blocks_closing_braces():
    """Test multiple nested blocks close properly."""
    converter = PythonToJavaScriptConverter()
    code = ("if x > 0:\n"
            "    if y > 0:\n"
            "        print('both')\n"
            "    print('x')\n"
            "print('done')")
    result = converter.convert(code)

    # Check brace matching
    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, \
        f"Nested blocks unbalanced: {opening_count} opening, {closing_count} closing"

    # Verify structure
    lines = result.converted_code.split("\n")
    assert any("if (x > 0)" in line for line in lines), "Outer if statement not converted"
    assert any("if (y > 0)" in line for line in lines), "Inner if statement not converted"

    print("✓ test_nested_blocks_closing_braces passed")


def test_function_closing_brace():
    """Test function definition has closing brace."""
    converter = PythonToJavaScriptConverter()
    code = ("def greet(name):\n"
            "    print(f'Hello {name}')\n"
            "    return name")
    result = converter.convert(code)

    assert "function greet" in result.converted_code, "Function not converted"
    assert "}" in result.converted_code, "Missing closing brace for function"

    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "Function braces not balanced"

    print("✓ test_function_closing_brace passed")


def test_for_loop_closing_brace():
    """Test for loop has closing brace."""
    converter = PythonToJavaScriptConverter()
    code = ("for i in range(5):\n"
            "    print(i)\n"
            "print('done')")
    result = converter.convert(code)

    assert "for (let i = 0" in result.converted_code, "For loop not converted"
    assert "}" in result.converted_code, "Missing closing brace for loop"

    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "Loop braces not balanced"

    print("✓ test_for_loop_closing_brace passed")


def test_if_elif_else_closing_braces():
    """Test if/elif/else chain closes properly."""
    converter = PythonToJavaScriptConverter()
    code = ("if x > 10:\n"
            "    print('large')\n"
            "elif x > 5:\n"
            "    print('medium')\n"
            "else:\n"
            "    print('small')\n"
            "print('done')")
    result = converter.convert(code)

    # Should have balanced braces
    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "If/elif/else braces not balanced"

    # Check for proper else if syntax
    # Note: closing brace is on separate line due to indentation decrease
    assert "else if" in result.converted_code, "Missing else if"
    assert "else {" in result.converted_code, "Missing else {"

    print("✓ test_if_elif_else_closing_braces passed")


def test_while_loop_closing_brace():
    """Test while loop closing brace."""
    converter = PythonToJavaScriptConverter()
    code = ("while x > 0:\n"
            "    print(x)\n"
            "    x = x - 1\n"
            "print('done')")
    result = converter.convert(code)

    assert "while" in result.converted_code, "While loop not converted"

    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "While loop braces not balanced"

    print("✓ test_while_loop_closing_brace passed")


def test_try_catch_closing_braces():
    """Test try/catch blocks close properly."""
    converter = PythonToJavaScriptConverter()
    code = ("try:\n"
            "    x = 1 / 0\n"
            "except ZeroDivisionError:\n"
            "    print('Error')\n"
            "print('done')")
    result = converter.convert(code)

    assert "try {" in result.converted_code, "Try block not converted"
    assert "catch" in result.converted_code, "Catch block not converted"

    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "Try/catch braces not balanced"

    print("✓ test_try_catch_closing_braces passed")


def test_multiple_unindent_levels():
    """Test multiple indentation level decreases."""
    converter = PythonToJavaScriptConverter()
    code = ("if a:\n"
            "    if b:\n"
            "        if c:\n"
            "            print('c')\n"
            "print('done')")
    result = converter.convert(code)

    # Should have 3 closing braces
    closing_count = result.converted_code.count("}")
    assert closing_count >= 3, f"Expected at least 3 closing braces, got {closing_count}"

    # Braces should be balanced
    opening_count = result.converted_code.count("{")
    assert opening_count == closing_count, "Multiple unindent braces not balanced"

    print("✓ test_multiple_unindent_levels passed")


def test_empty_block_handling():
    """Test handling of blocks with minimal content."""
    converter = PythonToJavaScriptConverter()
    code = "if x:\n    pass\nprint('ok')"
    result = converter.convert(code)

    # Should still close the block properly
    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "Empty block braces not balanced"

    print("✓ test_empty_block_handling passed")


def test_complex_nested_structure():
    """Test complex nested structure with multiple block types."""
    converter = PythonToJavaScriptConverter()
    code = ("def process(items):\n"
            "    for item in items:\n"
            "        if item > 0:\n"
            "            print(item)\n"
            "        else:\n"
            "            print('negative')\n"
            "    return items\n"
            "result = process([1, 2, 3])")
    result = converter.convert(code)

    # Verify all braces are balanced
    opening_count = result.converted_code.count("{")
    closing_count = result.converted_code.count("}")
    assert opening_count == closing_count, "Complex structure braces not balanced"

    # Verify function was converted
    assert "function process" in result.converted_code, "Function definition not converted"

    # Verify loop was converted
    assert "for (let item of items)" in result.converted_code, "For loop not converted"

    print("✓ test_complex_nested_structure passed")


def test_indentation_consistency():
    """Test that closing braces have consistent indentation."""
    converter = PythonToJavaScriptConverter()
    code = ("if x:\n"
            "    if y:\n"
            "        print('y')\n"
            "    print('x')\n"
            "print('done')")
    result = converter.convert(code)

    lines = result.converted_code.split("\n")
    closing_braces = [line for line in lines if line.strip() == "}"]

    # Verify closing braces exist
    assert len(closing_braces) > 0, "No closing braces found"

    # Verify they have proper indentation (2 spaces per level)
    for brace_line in closing_braces:
        leading_spaces = len(brace_line) - len(brace_line.lstrip())
        # Should be multiple of 2 (2 spaces per indentation level)
        assert leading_spaces % 2 == 0, \
            f"Closing brace has improper indentation: {leading_spaces} spaces"

    print("✓ test_indentation_consistency passed")


if __name__ == "__main__":
    test_simple_if_closing_brace()
    test_nested_blocks_closing_braces()
    test_function_closing_brace()
    test_for_loop_closing_brace()
    test_if_elif_else_closing_braces()
    test_while_loop_closing_brace()
    test_try_catch_closing_braces()
    test_multiple_unindent_levels()
    test_empty_block_handling()
    test_complex_nested_structure()
    test_indentation_consistency()

    print("\n" + "=" * 60)
    print("All closing brace tests passed! ✓")
    print("=" * 60)
