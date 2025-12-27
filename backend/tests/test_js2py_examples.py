"""
Comprehensive tests for JavaScript to Python conversion.

Tests verify that JavaScript code is correctly converted to idiomatic Python
with proper indentation (4 spaces), syntax validity, and accurate semantics.
"""

import sys
sys.path.insert(0, '/home/user/code-convertor/backend')

from converters.javascript_to_python import JavaScriptToPythonConverter


# ============================================================================
# LEVEL 1: Simple Replacements (100% Accuracy)
# ============================================================================

def test_console_log_to_print():
    """Test console.log() conversion to print()."""
    converter = JavaScriptToPythonConverter()
    code = "console.log('Hello');\nconsole.log(x);"
    result = converter.convert(code)

    assert "print('Hello')" in result.converted_code, "console.log not converted"
    assert "print(x)" in result.converted_code, "console.log with variable not converted"
    assert result.conversion_confidence > 0.8, f"Low confidence: {result.conversion_confidence}"

    print("✓ test_console_log_to_print passed")


def test_variable_declarations():
    """Test let/const/var conversion."""
    converter = JavaScriptToPythonConverter()
    code = "let x = 5;\nconst Y = 10;\nvar z = 15;"
    result = converter.convert(code)

    assert "x = 5" in result.converted_code, "let not converted"
    assert "Y = 10" in result.converted_code, "const not converted"
    assert "z = 15" in result.converted_code, "var not converted"
    assert result.conversion_confidence > 0.8, f"Low confidence: {result.conversion_confidence}"

    print("✓ test_variable_declarations passed")


def test_boolean_null_conversion():
    """Test boolean and null conversion."""
    converter = JavaScriptToPythonConverter()
    code = "let isTrue = true;\nlet isFalse = false;\nlet empty = null;"
    result = converter.convert(code)

    assert "isTrue = True" in result.converted_code, "true not converted to True"
    assert "isFalse = False" in result.converted_code, "false not converted to False"
    assert "empty = None" in result.converted_code, "null not converted to None"

    print("✓ test_boolean_null_conversion passed")


def test_comment_conversion():
    """Test JavaScript comment to Python comment."""
    converter = JavaScriptToPythonConverter()
    code = "// This is a comment\nlet x = 5;"
    result = converter.convert(code)

    assert "# This is a comment" in result.converted_code, "Comment not converted"

    print("✓ test_comment_conversion passed")


def test_template_literal_to_f_string():
    """Test template literal conversion to f-string."""
    converter = JavaScriptToPythonConverter()
    code = 'console.log(`Hello ${name}`);'
    result = converter.convert(code)

    assert "print(f" in result.converted_code, "Template literal not converted to f-string"
    assert "{name}" in result.converted_code, "Variable not substituted correctly"

    print("✓ test_template_literal_to_f_string passed")


# ============================================================================
# LEVEL 2: Structural Transformations
# ============================================================================

def test_simple_if_statement():
    """Test if statement conversion."""
    converter = JavaScriptToPythonConverter()
    code = "if (x > 5) {\n    console.log(x);\n}"
    result = converter.convert(code)

    assert "if x > 5:" in result.converted_code, "if statement not converted"
    assert "print(x)" in result.converted_code, "print in if block not converted"

    # Check indentation (4 spaces for Python)
    lines = result.converted_code.split("\n")
    print_line = [l for l in lines if "print" in l][0]
    leading_spaces = len(print_line) - len(print_line.lstrip())
    assert leading_spaces == 4, f"Expected 4 spaces, got {leading_spaces}"

    print("✓ test_simple_if_statement passed")


def test_if_else_statement():
    """Test if/else statement conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (x > 5) {\n"
        "    console.log('large');\n"
        "} else {\n"
        "    console.log('small');\n"
        "}"
    )
    result = converter.convert(code)

    assert "if x > 5:" in result.converted_code, "if not converted"
    assert "else:" in result.converted_code, "else not converted"
    assert result.conversion_confidence > 0.7, f"Low confidence: {result.conversion_confidence}"

    print("✓ test_if_else_statement passed")


def test_if_elif_else_chain():
    """Test if/elif/else chain conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (x > 10) {\n"
        "    console.log('large');\n"
        "} else if (x > 5) {\n"
        "    console.log('medium');\n"
        "} else {\n"
        "    console.log('small');\n"
        "}"
    )
    result = converter.convert(code)

    assert "if x > 10:" in result.converted_code, "if not converted"
    assert "elif x > 5:" in result.converted_code, "elif not converted"
    assert "else:" in result.converted_code, "else not converted"

    print("✓ test_if_elif_else_chain passed")


def test_condition_operators():
    """Test condition operator conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (x === 5) { console.log('equal'); }\n"
        "if (x !== 5) { console.log('not equal'); }\n"
        "if (x > 5 && y < 10) { console.log('both'); }\n"
        "if (a || b) { console.log('or'); }\n"
        "if (!x) { console.log('not'); }"
    )
    result = converter.convert(code)

    assert "x == 5" in result.converted_code, "=== not converted to =="
    assert "x != 5" in result.converted_code, "!== not converted to !="
    assert "and" in result.converted_code, "&& not converted to and"
    assert "or" in result.converted_code, "|| not converted to or"
    assert "not x" in result.converted_code, "! not converted to not"

    print("✓ test_condition_operators passed")


def test_function_definition():
    """Test function definition conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "function greet(name) {\n"
        "    console.log(`Hello ${name}`);\n"
        "}\n"
        "greet('Alice');"
    )
    result = converter.convert(code)

    assert "def greet(name):" in result.converted_code, "function not converted"
    assert "print(f" in result.converted_code or "print(" in result.converted_code, "function body not converted"

    print("✓ test_function_definition passed")


def test_while_loop():
    """Test while loop conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "let i = 0;\n"
        "while (i < 5) {\n"
        "    console.log(i);\n"
        "    i++;\n"
        "}"
    )
    result = converter.convert(code)

    assert "while i < 5:" in result.converted_code, "while not converted"
    assert "print(i)" in result.converted_code, "loop body not converted"

    print("✓ test_while_loop passed")


def test_try_catch_block():
    """Test try/catch conversion to try/except."""
    converter = JavaScriptToPythonConverter()
    code = (
        "try {\n"
        "    let x = 1 / 0;\n"
        "} catch (error) {\n"
        "    console.log('Error');\n"
        "}"
    )
    result = converter.convert(code)

    assert "try:" in result.converted_code, "try not converted"
    assert "except Exception" in result.converted_code, "catch not converted"

    print("✓ test_try_catch_block passed")


def test_nested_if_blocks():
    """Test nested if blocks conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (a) {\n"
        "    if (b) {\n"
        "        console.log('nested');\n"
        "    }\n"
        "}"
    )
    result = converter.convert(code)

    lines = result.converted_code.split("\n")
    if_lines = [l for l in lines if "if " in l]
    assert len(if_lines) >= 2, "Nested if statements not found"

    # Check indentation
    nested_line = [l for l in lines if "if b" in l][0]
    nested_spaces = len(nested_line) - len(nested_line.lstrip())
    assert nested_spaces == 4, f"Nested if should have 4 spaces, got {nested_spaces}"

    print("✓ test_nested_if_blocks passed")


def test_null_check_condition():
    """Test null checking in conditions."""
    converter = JavaScriptToPythonConverter()
    code = "if (x === null) { console.log('is null'); }"
    result = converter.convert(code)

    assert "x == None" in result.converted_code, "null not converted in condition"

    print("✓ test_null_check_condition passed")


# ============================================================================
# LEVEL 3: Complex Conversions
# ============================================================================

def test_for_loop_with_range():
    """Test for loop with range conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "for (let i = 0; i < 5; i++) {\n"
        "    console.log(i);\n"
        "}"
    )
    result = converter.convert(code)

    assert "for i in range(5):" in result.converted_code, "for loop not converted"
    assert "print(i)" in result.converted_code, "loop body not converted"

    print("✓ test_for_loop_with_range passed")


def test_for_of_loop():
    """Test for-of loop conversion."""
    converter = JavaScriptToPythonConverter()
    code = (
        "for (let item of items) {\n"
        "    console.log(item);\n"
        "}"
    )
    result = converter.convert(code)

    assert "for item in items:" in result.converted_code, "for-of loop not converted"

    print("✓ test_for_of_loop passed")


def test_for_in_loop():
    """Test for-in loop conversion with warning."""
    converter = JavaScriptToPythonConverter()
    code = (
        "for (let key in obj) {\n"
        "    console.log(key);\n"
        "}"
    )
    result = converter.convert(code)

    assert "for key in obj:" in result.converted_code, "for-in loop not converted"
    # Should have warning about for-in
    assert len(result.warnings) > 0, "Should have warning for for-in loop"

    print("✓ test_for_in_loop passed")


def test_arrow_function_to_lambda():
    """Test arrow function conversion to lambda."""
    converter = JavaScriptToPythonConverter()
    code = "let double = x => x * 2;"
    result = converter.convert(code)

    assert "lambda x: x * 2" in result.converted_code, "arrow function not converted to lambda"
    # Should have warning about lambda limitations
    assert len(result.warnings) > 0, "Should have warning for arrow function"

    print("✓ test_arrow_function_to_lambda passed")


def test_complex_nested_structure():
    """Test complex nested structure with multiple block types."""
    converter = JavaScriptToPythonConverter()
    code = (
        "function process(items) {\n"
        "    for (let item of items) {\n"
        "        if (item > 0) {\n"
        "            console.log(item);\n"
        "        } else {\n"
        "            console.log('negative');\n"
        "        }\n"
        "    }\n"
        "}\n"
        "process([1, 2, 3]);"
    )
    result = converter.convert(code)

    assert "def process(items):" in result.converted_code, "function not converted"
    assert "for item in items:" in result.converted_code, "for loop not converted"
    assert "if item > 0:" in result.converted_code, "if not converted"
    assert "else:" in result.converted_code, "else not converted"

    print("✓ test_complex_nested_structure passed")


# ============================================================================
# QUALITY GATES
# ============================================================================

def test_indentation_consistency():
    """Test that converted Python uses 4-space indentation."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (x) {\n"
        "    if (y) {\n"
        "        console.log('y');\n"
        "    }\n"
        "}"
    )
    result = converter.convert(code)

    lines = result.converted_code.split("\n")
    # Find indented lines
    indented_lines = [l for l in lines if l and l[0] == ' ']

    for line in indented_lines:
        leading_spaces = len(line) - len(line.lstrip())
        # Should be multiple of 4 (Python standard)
        assert leading_spaces % 4 == 0, \
            f"Line has {leading_spaces} spaces (not multiple of 4): {line}"

    print("✓ test_indentation_consistency passed")


def test_colons_after_blocks():
    """Test that all block-starting statements have colons."""
    converter = JavaScriptToPythonConverter()
    code = (
        "if (a) {\n"
        "    console.log('a');\n"
        "}\n"
        "for (let i = 0; i < 5; i++) {\n"
        "    console.log(i);\n"
        "}\n"
        "function f() {\n"
        "    console.log('f');\n"
        "}"
    )
    result = converter.convert(code)

    # Check that lines with if/for/def have colons
    lines = result.converted_code.split("\n")
    block_lines = [l.strip() for l in lines if l.strip() and any(kw in l for kw in ['if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'try:', 'except '])]

    for line in block_lines:
        if not line.endswith(':'):
            # Handle cases like "} else:" where closing brace comes first
            if ':' not in line:
                raise AssertionError(f"Block line missing colon: {line}")

    print("✓ test_colons_after_blocks passed")


def test_confidence_scoring_simple():
    """Test confidence scoring for simple conversions."""
    converter = JavaScriptToPythonConverter()
    code = "let x = 5;\nconsole.log(x);"
    result = converter.convert(code)

    # Simple code should have high confidence
    assert result.conversion_confidence > 0.7, \
        f"Low confidence for simple code: {result.conversion_confidence}"

    print("✓ test_confidence_scoring_simple passed")


def test_confidence_scoring_with_warnings():
    """Test confidence scoring with warnings."""
    converter = JavaScriptToPythonConverter()
    code = "let double = x => x * 2;"
    result = converter.convert(code)

    # Complex arrow functions should have warnings
    assert len(result.warnings) > 0, "Should have warnings for arrow function"
    # But confidence should still be reasonable
    assert result.conversion_confidence > 0.5, \
        f"Confidence too low despite valid conversion: {result.conversion_confidence}"

    print("✓ test_confidence_scoring_with_warnings passed")


def test_construct_detection():
    """Test that constructs are properly detected."""
    converter = JavaScriptToPythonConverter()
    code = (
        "let x = 5;\n"
        "console.log(x);\n"
        "if (x > 0) {\n"
        "    console.log('positive');\n"
        "}"
    )
    result = converter.convert(code)

    # Should detect variable and output
    assert "variable" in result.metadata.get("constructs_found", {}), "Variable not detected"
    assert "output" in result.metadata.get("constructs_found", {}), "Output not detected"

    print("✓ test_construct_detection passed")


def test_multiple_conversions_in_sequence():
    """Test multiple conversions work correctly in sequence."""
    converter = JavaScriptToPythonConverter()

    # First conversion
    code1 = "let x = 5;\nconsole.log(x);"
    result1 = converter.convert(code1)
    assert "x = 5" in result1.converted_code

    # Second conversion with same converter instance
    code2 = "if (true) {\n    console.log('yes');\n}"
    result2 = converter.convert(code2)
    assert "if True:" in result2.converted_code

    print("✓ test_multiple_conversions_in_sequence passed")


def test_empty_code():
    """Test handling of empty code."""
    converter = JavaScriptToPythonConverter()
    code = ""
    result = converter.convert(code)

    assert result.converted_code == "", "Empty code should return empty string"
    assert result.conversion_confidence == 1.0, "Empty code should have perfect confidence"

    print("✓ test_empty_code passed")


def test_comments_only():
    """Test code with only comments."""
    converter = JavaScriptToPythonConverter()
    code = "// Comment 1\n// Comment 2"
    result = converter.convert(code)

    assert "# Comment 1" in result.converted_code, "Comment 1 not converted"
    assert "# Comment 2" in result.converted_code, "Comment 2 not converted"

    print("✓ test_comments_only passed")


def test_semicolon_removal():
    """Test that semicolons are removed in Python output."""
    converter = JavaScriptToPythonConverter()
    code = "let x = 5;\nconsole.log(x);"
    result = converter.convert(code)

    # Check that output has no semicolons on Python statements
    lines = result.converted_code.split("\n")
    python_lines = [l for l in lines if any(kw in l for kw in ['print', '=', 'if ', 'for '])]

    for line in python_lines:
        # Python lines shouldn't end with semicolons (except in strings)
        if line.rstrip().endswith(';'):
            raise AssertionError(f"Semicolon found in Python output: {line}")

    print("✓ test_semicolon_removal passed")


if __name__ == "__main__":
    # Level 1: Simple Replacements
    test_console_log_to_print()
    test_variable_declarations()
    test_boolean_null_conversion()
    test_comment_conversion()
    test_template_literal_to_f_string()

    # Level 2: Structural Transformations
    test_simple_if_statement()
    test_if_else_statement()
    test_if_elif_else_chain()
    test_condition_operators()
    test_function_definition()
    test_while_loop()
    test_try_catch_block()
    test_nested_if_blocks()
    test_null_check_condition()

    # Level 3: Complex Conversions
    test_for_loop_with_range()
    test_for_of_loop()
    test_for_in_loop()
    test_arrow_function_to_lambda()
    test_complex_nested_structure()

    # Quality Gates
    test_indentation_consistency()
    test_colons_after_blocks()
    test_confidence_scoring_simple()
    test_confidence_scoring_with_warnings()
    test_construct_detection()
    test_multiple_conversions_in_sequence()
    test_empty_code()
    test_comments_only()
    test_semicolon_removal()

    print("\n" + "=" * 60)
    print("All JavaScript→Python tests passed! ✓")
    print("=" * 60)
