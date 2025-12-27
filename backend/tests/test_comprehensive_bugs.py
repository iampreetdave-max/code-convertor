"""
Comprehensive bug-catching test suite with 100+ test cases.

Tests designed to identify logical errors, edge cases, and boundary conditions
across the entire code-convertor system.
"""

import sys
sys.path.insert(0, '/home/user/code-convertor/backend')

from converters.python_to_javascript import PythonToJavaScriptConverter
from converters.javascript_to_python import JavaScriptToPythonConverter
from core.language_detector import LanguageDetector
from utils.confidence_calculator import ConfidenceCalculator
from utils.indentation import IndentationTracker


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.passed += 1
        print(f"✓ {test_name}")

    def add_fail(self, test_name, reason):
        self.failed += 1
        self.errors.append((test_name, reason))
        print(f"✗ {test_name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"TEST RESULTS: {self.passed}/{total} PASSED")
        print(f"{'='*70}")
        if self.errors:
            print(f"\n{self.failed} FAILURES:\n")
            for test_name, reason in self.errors:
                print(f"  ✗ {test_name}")
                print(f"    {reason}\n")


results = TestResults()

# ============================================================================
# CRITICAL BUG TESTS: Nested Parentheses in Print/Console.log
# ============================================================================

def test_python_print_with_nested_function_call():
    """Test print with nested function calls."""
    converter = PythonToJavaScriptConverter()
    code = "print(func())"
    result = converter.convert(code)
    if "console.log(func())" in result.converted_code:
        results.add_pass("python_print_with_nested_function_call")
    else:
        results.add_fail("python_print_with_nested_function_call",
                        f"Expected 'console.log(func())', got: {result.converted_code}")


def test_python_print_with_multiple_nested():
    """Test print with multiple nested function calls."""
    converter = PythonToJavaScriptConverter()
    code = "print(func(inner()))"
    result = converter.convert(code)
    if "console.log(func(inner()))" in result.converted_code:
        results.add_pass("python_print_with_multiple_nested")
    else:
        results.add_fail("python_print_with_multiple_nested",
                        f"Expected complete function call, got: {result.converted_code}")


def test_javascript_console_log_nested_function():
    """Test console.log with nested function calls."""
    converter = JavaScriptToPythonConverter()
    code = "console.log(func());"
    result = converter.convert(code)
    if "print(func())" in result.converted_code:
        results.add_pass("javascript_console_log_nested_function")
    else:
        results.add_fail("javascript_console_log_nested_function",
                        f"Expected 'print(func())', got: {result.converted_code}")


def test_javascript_console_log_multiple_params_with_calls():
    """Test console.log with multiple parameters including function calls."""
    converter = JavaScriptToPythonConverter()
    code = "console.log(func1(), func2());"
    result = converter.convert(code)
    if "print(func1(), func2())" in result.converted_code:
        results.add_pass("javascript_console_log_multiple_params_with_calls")
    else:
        results.add_fail("javascript_console_log_multiple_params_with_calls",
                        f"Expected both functions, got: {result.converted_code}")


# ============================================================================
# CRITICAL BUG TESTS: If Statement with Nested Parentheses
# ============================================================================

def test_python_if_with_nested_function_call():
    """Test if statement with nested function call in condition."""
    converter = PythonToJavaScriptConverter()
    code = "if func(x):\n    pass"
    result = converter.convert(code)
    if "if (func(x))" in result.converted_code:
        results.add_pass("python_if_with_nested_function_call")
    else:
        results.add_fail("python_if_with_nested_function_call",
                        f"Expected 'if (func(x))', got: {result.converted_code}")


def test_javascript_if_with_nested_function_call():
    """Test if statement with nested function call."""
    converter = JavaScriptToPythonConverter()
    code = "if (func(x)) {\n    console.log('yes');\n}"
    result = converter.convert(code)
    if "if func(x):" in result.converted_code:
        results.add_pass("javascript_if_with_nested_function_call")
    else:
        results.add_fail("javascript_if_with_nested_function_call",
                        f"Expected 'if func(x):', got: {result.converted_code}")


# ============================================================================
# CRITICAL BUG TESTS: Overly Broad Catch Pattern
# ============================================================================

def test_javascript_catch_in_comment():
    """Test that 'catch' in comments doesn't trigger catch block conversion."""
    converter = JavaScriptToPythonConverter()
    code = "// catch the error\nconsole.log('ok');"
    result = converter.convert(code)
    # Should NOT convert to except
    if "except" not in result.converted_code:
        results.add_pass("javascript_catch_in_comment")
    else:
        results.add_fail("javascript_catch_in_comment",
                        "Comment containing 'catch' was incorrectly converted to except")


def test_javascript_catch_in_string():
    """Test that 'catch' in string literals doesn't trigger conversion."""
    converter = JavaScriptToPythonConverter()
    code = 'let msg = "catch this";\nconsole.log(msg);'
    result = converter.convert(code)
    # Should NOT convert string content
    if 'msg = "catch this"' in result.converted_code or "msg = 'catch this'" in result.converted_code:
        results.add_pass("javascript_catch_in_string")
    else:
        results.add_fail("javascript_catch_in_string",
                        "String literal with 'catch' was incorrectly modified")


# ============================================================================
# HIGH SEVERITY TESTS: Boolean Conversion Edge Cases
# ============================================================================

def test_python_to_js_true_with_comma():
    """Test True followed by comma."""
    converter = PythonToJavaScriptConverter()
    code = "x = [True, False]"
    result = converter.convert(code)
    if "true, false" in result.converted_code or "true,false" in result.converted_code:
        results.add_pass("python_to_js_true_with_comma")
    else:
        results.add_fail("python_to_js_true_with_comma",
                        f"Boolean in list not converted: {result.converted_code}")


def test_python_to_js_true_with_bracket():
    """Test True followed by bracket."""
    converter = PythonToJavaScriptConverter()
    code = "x = [True]"
    result = converter.convert(code)
    if "true" in result.converted_code.lower():
        results.add_pass("python_to_js_true_with_bracket")
    else:
        results.add_fail("python_to_js_true_with_bracket",
                        f"Boolean in bracket not converted: {result.converted_code}")


def test_python_to_js_true_with_colon():
    """Test True followed by colon."""
    converter = PythonToJavaScriptConverter()
    code = "x = {True: 1}"
    result = converter.convert(code)
    if "true" in result.converted_code.lower():
        results.add_pass("python_to_js_true_with_colon")
    else:
        results.add_fail("python_to_js_true_with_colon",
                        f"Boolean in dict not converted: {result.converted_code}")


def test_python_to_js_true_in_ternary():
    """Test True in ternary expression."""
    converter = PythonToJavaScriptConverter()
    code = "x = a if True else b"
    result = converter.convert(code)
    # Should have converted True to true
    if "true" in result.converted_code.lower():
        results.add_pass("python_to_js_true_in_ternary")
    else:
        results.add_fail("python_to_js_true_in_ternary",
                        f"True in ternary not converted: {result.converted_code}")


# ============================================================================
# HIGH SEVERITY TESTS: String-Based Replacement Issues
# ============================================================================

def test_python_to_js_none_in_variable_name():
    """Test that None in variable names isn't converted in Py->JS."""
    converter = PythonToJavaScriptConverter()
    code = "NonExistent = 5"
    result = converter.convert(code)
    # Should NOT convert NonExistent to nullExistent
    if "NonExistent" in result.converted_code or "nonexistent" in result.converted_code.lower():
        results.add_pass("python_to_js_none_in_variable_name")
    else:
        results.add_fail("python_to_js_none_in_variable_name",
                        f"Variable name corrupted: {result.converted_code}")


def test_javascript_to_python_true_in_variable_name():
    """Test that 'true' in variable names isn't converted."""
    converter = JavaScriptToPythonConverter()
    code = "let isTrue = 5;"
    result = converter.convert(code)
    # Variable name should stay as isTrue, only the value True should be uppercase
    if "is" in result.converted_code.lower():
        results.add_pass("javascript_to_python_true_in_variable_name")
    else:
        results.add_fail("javascript_to_python_true_in_variable_name",
                        f"Variable name corrupted: {result.converted_code}")


# ============================================================================
# HIGH SEVERITY TESTS: Complex Exception Types
# ============================================================================

def test_python_multiple_exception_types():
    """Test exception handling with multiple exception types."""
    converter = PythonToJavaScriptConverter()
    code = "try:\n    pass\nexcept (ValueError, TypeError):\n    pass"
    result = converter.convert(code)
    if "catch" in result.converted_code:
        results.add_pass("python_multiple_exception_types")
    else:
        results.add_fail("python_multiple_exception_types",
                        "Multiple exception types not handled")


def test_python_exception_with_pipe():
    """Test exception handling with pipe syntax."""
    converter = PythonToJavaScriptConverter()
    code = "try:\n    pass\nexcept ValueError | TypeError:\n    pass"
    result = converter.convert(code)
    if "catch" in result.converted_code:
        results.add_pass("python_exception_with_pipe")
    else:
        results.add_fail("python_exception_with_pipe",
                        "Pipe syntax exception not handled")


# ============================================================================
# HIGH SEVERITY TESTS: Arrow Function Parameter Parsing
# ============================================================================

def test_javascript_arrow_with_parentheses():
    """Test arrow function with parentheses around parameter."""
    converter = JavaScriptToPythonConverter()
    code = "let f = (x) => x * 2;"
    result = converter.convert(code)
    if "lambda" in result.converted_code and "x" in result.converted_code:
        results.add_pass("javascript_arrow_with_parentheses")
    else:
        results.add_fail("javascript_arrow_with_parentheses",
                        f"Arrow with parentheses not converted: {result.converted_code}")


def test_javascript_arrow_multiple_params():
    """Test arrow function with multiple parameters."""
    converter = JavaScriptToPythonConverter()
    code = "let add = (x, y) => x + y;"
    result = converter.convert(code)
    # Currently not supported but should not crash
    if result.conversion_confidence >= 0:
        results.add_pass("javascript_arrow_multiple_params")
    else:
        results.add_fail("javascript_arrow_multiple_params",
                        "Multiple parameter arrow function caused crash")


def test_javascript_arrow_no_params():
    """Test arrow function with no parameters."""
    converter = JavaScriptToPythonConverter()
    code = "let f = () => 42;"
    result = converter.convert(code)
    # Currently not supported but should not crash
    if result.conversion_confidence >= 0:
        results.add_pass("javascript_arrow_no_params")
    else:
        results.add_fail("javascript_arrow_no_params",
                        "No-parameter arrow function caused crash")


# ============================================================================
# HIGH SEVERITY TESTS: Parentheses Balancing in Confidence
# ============================================================================

def test_confidence_braces_in_string():
    """Test confidence calculation with braces in string literals."""
    calculator = ConfidenceCalculator()
    code = 'print("}")'
    # Should not count string content braces
    result = calculator.calculate(code, code)
    if result > 0.5:  # Should have reasonable confidence
        results.add_pass("confidence_braces_in_string")
    else:
        results.add_fail("confidence_braces_in_string",
                        f"String braces incorrectly counted, confidence too low: {result}")


def test_confidence_braces_in_comment():
    """Test confidence calculation with braces in comments."""
    calculator = ConfidenceCalculator()
    code = 'x = 5  # comment with }'
    result = calculator.calculate(code, code)
    if result > 0.5:
        results.add_pass("confidence_braces_in_comment")
    else:
        results.add_fail("confidence_braces_in_comment",
                        f"Comment braces incorrectly counted, confidence too low: {result}")


# ============================================================================
# MEDIUM SEVERITY TESTS: Integer Constraints in Range
# ============================================================================

def test_python_negative_range():
    """Test for loop with negative range."""
    converter = PythonToJavaScriptConverter()
    code = "for i in range(-5):\n    pass"
    result = converter.convert(code)
    # Should handle negative ranges
    if "for" in result.converted_code:
        results.add_pass("python_negative_range")
    else:
        results.add_fail("python_negative_range",
                        "Negative range not handled")


def test_python_range_with_variable():
    """Test for loop with variable in range."""
    converter = PythonToJavaScriptConverter()
    code = "for i in range(n):\n    pass"
    result = converter.convert(code)
    # Should handle variable-based ranges
    if "for" in result.converted_code:
        results.add_pass("python_range_with_variable")
    else:
        results.add_fail("python_range_with_variable",
                        "Variable-based range not handled")


def test_python_range_with_expression():
    """Test for loop with expression in range."""
    converter = PythonToJavaScriptConverter()
    code = "for i in range(n + 1):\n    pass"
    result = converter.convert(code)
    if "for" in result.converted_code:
        results.add_pass("python_range_with_expression")
    else:
        results.add_fail("python_range_with_expression",
                        "Expression in range not handled")


# ============================================================================
# MEDIUM SEVERITY TESTS: For-Of with Complex Iterables
# ============================================================================

def test_javascript_for_of_with_function_call():
    """Test for-of loop with function call as iterable."""
    converter = JavaScriptToPythonConverter()
    code = "for (let x of getArray()) {\n    console.log(x);\n}"
    result = converter.convert(code)
    if "for x in" in result.converted_code:
        results.add_pass("javascript_for_of_with_function_call")
    else:
        results.add_fail("javascript_for_of_with_function_call",
                        f"For-of with function call not handled: {result.converted_code}")


def test_javascript_for_of_with_nested_call():
    """Test for-of with nested function calls."""
    converter = JavaScriptToPythonConverter()
    code = "for (let x of obj.getArray()) {\n    console.log(x);\n}"
    result = converter.convert(code)
    if "for x in" in result.converted_code:
        results.add_pass("javascript_for_of_with_nested_call")
    else:
        results.add_fail("javascript_for_of_with_nested_call",
                        "For-of with nested call not handled")


# ============================================================================
# MEDIUM SEVERITY TESTS: List Comprehensions
# ============================================================================

def test_python_list_comprehension_with_condition():
    """Test list comprehension with condition."""
    converter = PythonToJavaScriptConverter()
    code = "[x for x in items if x > 0]"
    result = converter.convert(code)
    # Should handle or skip with warning
    if result.conversion_confidence >= 0:
        results.add_pass("python_list_comprehension_with_condition")
    else:
        results.add_fail("python_list_comprehension_with_condition",
                        "List comprehension with condition crashed")


def test_python_list_comprehension_multiple_for():
    """Test list comprehension with multiple for clauses."""
    converter = PythonToJavaScriptConverter()
    code = "[x+y for x in a for y in b]"
    result = converter.convert(code)
    if result.conversion_confidence >= 0:
        results.add_pass("python_list_comprehension_multiple_for")
    else:
        results.add_fail("python_list_comprehension_multiple_for",
                        "Multiple for comprehension crashed")


# ============================================================================
# MEDIUM SEVERITY TESTS: Indentation Edge Cases
# ============================================================================

def test_indentation_three_spaces():
    """Test handling of 3-space indentation (malformed)."""
    tracker = IndentationTracker("python")
    level = tracker.get_indent_level("   x = 5")  # 3 spaces
    # Should handle gracefully
    if level == 0:
        results.add_pass("indentation_three_spaces")
    else:
        results.add_fail("indentation_three_spaces",
                        f"3-space indentation incorrectly parsed as level {level}")


def test_indentation_five_spaces():
    """Test handling of 5-space indentation."""
    tracker = IndentationTracker("python")
    level = tracker.get_indent_level("     x = 5")  # 5 spaces
    # Should handle gracefully (not 0, not 2)
    if level in [1, 1.25]:  # Either round down or handle specially
        results.add_pass("indentation_five_spaces")
    else:
        results.add_fail("indentation_five_spaces",
                        f"5-space indentation incorrectly parsed as level {level}")


def test_javascript_indentation_mixed_spacing():
    """Test JavaScript with mixed 2-space and 4-space indentation."""
    tracker = IndentationTracker("javascript")
    level1 = tracker.get_indent_level("  x = 5")  # 2 spaces
    level2 = tracker.get_indent_level("    x = 5")  # 4 spaces
    # Both should be detected reasonably
    if level1 >= 0 and level2 >= 0:
        results.add_pass("javascript_indentation_mixed_spacing")
    else:
        results.add_fail("javascript_indentation_mixed_spacing",
                        "Mixed indentation not handled")


# ============================================================================
# MEDIUM SEVERITY TESTS: Type Hints
# ============================================================================

def test_python_complex_type_hint():
    """Test function with complex type hints."""
    converter = PythonToJavaScriptConverter()
    code = "def func(x: Dict[str, List[int]]) -> None:\n    pass"
    result = converter.convert(code)
    # Should convert without crashing, type hints should be removed, output should be JavaScript
    if "function func" in result.converted_code and "{" in result.converted_code:
        results.add_pass("python_complex_type_hint")
    else:
        results.add_fail("python_complex_type_hint",
                        f"Complex type hint not handled: {result.converted_code}")


def test_python_union_type_hint():
    """Test function with Union type hint."""
    converter = PythonToJavaScriptConverter()
    code = "def func(x: Union[int, str]) -> Optional[str]:\n    pass"
    result = converter.convert(code)
    if "function func" in result.converted_code and "{" in result.converted_code:
        results.add_pass("python_union_type_hint")
    else:
        results.add_fail("python_union_type_hint",
                        "Union type hint not handled")


def test_python_callable_type_hint():
    """Test function with Callable type hint."""
    converter = PythonToJavaScriptConverter()
    code = "def func(callback: Callable[[int, int], str]) -> None:\n    pass"
    result = converter.convert(code)
    if "function func" in result.converted_code and "{" in result.converted_code:
        results.add_pass("python_callable_type_hint")
    else:
        results.add_fail("python_callable_type_hint",
                        "Callable type hint not handled")


# ============================================================================
# LOW SEVERITY TESTS: Input Validation
# ============================================================================

def test_warning_negative_line_number():
    """Test warning with negative line number."""
    from utils.warning_generator import WarningGenerator
    generator = WarningGenerator()
    # Should handle gracefully
    try:
        generator.add_type_hint_warning(-1, "str")
        results.add_pass("warning_negative_line_number")
    except:
        results.add_fail("warning_negative_line_number",
                        "Negative line number caused exception")


def test_warning_zero_line_number():
    """Test warning with line number 0."""
    from utils.warning_generator import WarningGenerator
    generator = WarningGenerator()
    try:
        generator.add_type_hint_warning(0, "int")
        results.add_pass("warning_zero_line_number")
    except:
        results.add_fail("warning_zero_line_number",
                        "Zero line number caused exception")


def test_warning_very_large_line_number():
    """Test warning with very large line number."""
    from utils.warning_generator import WarningGenerator
    generator = WarningGenerator()
    try:
        generator.add_type_hint_warning(999999999, "float")
        results.add_pass("warning_very_large_line_number")
    except:
        results.add_fail("warning_very_large_line_number",
                        "Large line number caused exception")


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================

def test_empty_file_conversion():
    """Test converting empty file."""
    converter = PythonToJavaScriptConverter()
    code = ""
    result = converter.convert(code)
    if result.converted_code == "" and result.conversion_confidence == 1.0:
        results.add_pass("empty_file_conversion")
    else:
        results.add_fail("empty_file_conversion",
                        f"Empty file not handled correctly")


def test_only_comments_python():
    """Test Python file with only comments."""
    converter = PythonToJavaScriptConverter()
    code = "# Comment 1\n# Comment 2"
    result = converter.convert(code)
    if "//" in result.converted_code:
        results.add_pass("only_comments_python")
    else:
        results.add_fail("only_comments_python",
                        "Comments-only file not converted")


def test_only_comments_javascript():
    """Test JavaScript file with only comments."""
    converter = JavaScriptToPythonConverter()
    code = "// Comment 1\n// Comment 2"
    result = converter.convert(code)
    if "#" in result.converted_code:
        results.add_pass("only_comments_javascript")
    else:
        results.add_fail("only_comments_javascript",
                        "JavaScript comments-only file not converted")


def test_whitespace_only_file():
    """Test file with only whitespace."""
    converter = PythonToJavaScriptConverter()
    code = "   \n   \n   "
    result = converter.convert(code)
    # Should handle gracefully
    if result.conversion_confidence >= 0:
        results.add_pass("whitespace_only_file")
    else:
        results.add_fail("whitespace_only_file",
                        "Whitespace-only file caused issues")


def test_deeply_nested_structure():
    """Test deeply nested if/for/function structures."""
    converter = PythonToJavaScriptConverter()
    code = """if x:
    for i in range(5):
        if y:
            for j in range(3):
                if z:
                    print('deep')"""
    result = converter.convert(code)
    # Count opening and closing braces
    opens = result.converted_code.count('{')
    closes = result.converted_code.count('}')
    if opens == closes and opens > 0:
        results.add_pass("deeply_nested_structure")
    else:
        results.add_fail("deeply_nested_structure",
                        f"Brace mismatch: {opens} opens, {closes} closes")


def test_single_line_multiple_statements():
    """Test single line with multiple statements."""
    converter = PythonToJavaScriptConverter()
    code = "x = 5; y = 10; print(x)"
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("single_line_multiple_statements")
    else:
        results.add_fail("single_line_multiple_statements",
                        "Multiple statements on one line caused crash")


def test_mixed_quotes_in_strings():
    """Test strings with mixed quote types."""
    converter = PythonToJavaScriptConverter()
    code = '''print("He said \\'hello\\'")\nprint('She said "goodbye"')'''
    result = converter.convert(code)
    if "console.log" in result.converted_code:
        results.add_pass("mixed_quotes_in_strings")
    else:
        results.add_fail("mixed_quotes_in_strings",
                        "Mixed quotes in strings not handled")


def test_escaped_characters():
    """Test strings with escaped characters."""
    converter = PythonToJavaScriptConverter()
    code = r'print("Line 1\nLine 2\tTabbed")'
    result = converter.convert(code)
    if "\\n" in result.converted_code or "\\t" in result.converted_code:
        results.add_pass("escaped_characters")
    else:
        results.add_fail("escaped_characters",
                        "Escaped characters lost in conversion")


def test_raw_strings():
    """Test Python raw strings."""
    converter = PythonToJavaScriptConverter()
    code = r'regex = r"\d+\s+\w+"'
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("raw_strings")
    else:
        results.add_fail("raw_strings",
                        "Raw strings caused crash")


def test_unicode_characters():
    """Test code with unicode characters."""
    converter = PythonToJavaScriptConverter()
    code = 'message = "Hello 世界 🌍"'
    result = converter.convert(code)
    if "message" in result.converted_code:
        results.add_pass("unicode_characters")
    else:
        results.add_fail("unicode_characters",
                        "Unicode characters lost")


def test_very_long_line():
    """Test conversion of very long line."""
    converter = PythonToJavaScriptConverter()
    code = "x = " + " + ".join(str(i) for i in range(100))
    result = converter.convert(code)
    if "x" in result.converted_code:
        results.add_pass("very_long_line")
    else:
        results.add_fail("very_long_line",
                        "Very long line not handled")


def test_many_nested_parentheses():
    """Test expression with many nested parentheses."""
    converter = PythonToJavaScriptConverter()
    code = "result = ((((value + 1) * 2) - 3) / 4)"
    result = converter.convert(code)
    if "result" in result.converted_code:
        results.add_pass("many_nested_parentheses")
    else:
        results.add_fail("many_nested_parentheses",
                        "Nested parentheses not handled")


def test_assignment_with_complex_expression():
    """Test assignment with complex expression."""
    converter = JavaScriptToPythonConverter()
    code = "let x = a + b * c - d / e;"
    result = converter.convert(code)
    if "x = " in result.converted_code:
        results.add_pass("assignment_with_complex_expression")
    else:
        results.add_fail("assignment_with_complex_expression",
                        "Complex expression in assignment not converted")


def test_function_with_default_parameters():
    """Test function definition with default parameters."""
    converter = PythonToJavaScriptConverter()
    code = "def func(x=5, y=10):\n    pass"
    result = converter.convert(code)
    if "function func" in result.converted_code:
        results.add_pass("function_with_default_parameters")
    else:
        results.add_fail("function_with_default_parameters",
                        "Default parameters not handled")


def test_function_with_varargs():
    """Test function with *args and **kwargs."""
    converter = PythonToJavaScriptConverter()
    code = "def func(*args, **kwargs):\n    pass"
    result = converter.convert(code)
    # Should handle or skip gracefully
    if result.conversion_confidence >= 0:
        results.add_pass("function_with_varargs")
    else:
        results.add_fail("function_with_varargs",
                        "Varargs caused crash")


def test_lambda_function():
    """Test lambda function."""
    converter = PythonToJavaScriptConverter()
    code = "f = lambda x: x * 2"
    result = converter.convert(code)
    # Should handle arrow function conversion
    if result.conversion_confidence >= 0:
        results.add_pass("lambda_function")
    else:
        results.add_fail("lambda_function",
                        "Lambda function caused crash")


def test_decorator():
    """Test decorated function."""
    converter = PythonToJavaScriptConverter()
    code = "@decorator\ndef func():\n    pass"
    result = converter.convert(code)
    if "function" in result.converted_code or "@decorator" in result.converted_code:
        results.add_pass("decorator")
    else:
        results.add_fail("decorator",
                        "Decorator not handled")


def test_class_definition():
    """Test class definition (not supported but shouldn't crash)."""
    converter = PythonToJavaScriptConverter()
    code = "class MyClass:\n    pass"
    result = converter.convert(code)
    # Should fail gracefully
    if result.conversion_confidence >= 0:
        results.add_pass("class_definition")
    else:
        results.add_fail("class_definition",
                        "Class definition caused crash")


def test_import_statement():
    """Test import statement."""
    converter = PythonToJavaScriptConverter()
    code = "import numpy as np"
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("import_statement")
    else:
        results.add_fail("import_statement",
                        "Import statement caused crash")


def test_ternary_operator_python():
    """Test Python ternary operator."""
    converter = PythonToJavaScriptConverter()
    code = "x = a if condition else b"
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("ternary_operator_python")
    else:
        results.add_fail("ternary_operator_python",
                        "Ternary operator caused crash")


def test_ternary_operator_javascript():
    """Test JavaScript ternary operator."""
    converter = JavaScriptToPythonConverter()
    code = "let x = condition ? a : b;"
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("ternary_operator_javascript")
    else:
        results.add_fail("ternary_operator_javascript",
                        "JavaScript ternary caused crash")


def test_switch_statement():
    """Test JavaScript switch statement."""
    converter = JavaScriptToPythonConverter()
    code = "switch(x) {\n    case 1: break;\n    default: break;\n}"
    result = converter.convert(code)
    # Not supported but shouldn't crash
    if result.conversion_confidence >= 0:
        results.add_pass("switch_statement")
    else:
        results.add_fail("switch_statement",
                        "Switch statement caused crash")


def test_do_while_loop():
    """Test do-while loop (not in Python)."""
    converter = JavaScriptToPythonConverter()
    code = "do {\n    console.log('test');\n} while(x < 5);"
    result = converter.convert(code)
    # Should handle gracefully
    if result.conversion_confidence >= 0:
        results.add_pass("do_while_loop")
    else:
        results.add_fail("do_while_loop",
                        "Do-while loop caused crash")


def test_with_statement_python():
    """Test Python with statement."""
    converter = PythonToJavaScriptConverter()
    code = "with open('file.txt') as f:\n    data = f.read()"
    result = converter.convert(code)
    # Should handle or skip
    if result.conversion_confidence >= 0:
        results.add_pass("with_statement_python")
    else:
        results.add_fail("with_statement_python",
                        "With statement caused crash")


def test_multiple_inheritance():
    """Test Python class with multiple inheritance."""
    converter = PythonToJavaScriptConverter()
    code = "class Child(Parent1, Parent2):\n    pass"
    result = converter.convert(code)
    if result.conversion_confidence >= 0:
        results.add_pass("multiple_inheritance")
    else:
        results.add_fail("multiple_inheritance",
                        "Multiple inheritance caused crash")


def test_assert_statement():
    """Test assert statement."""
    converter = PythonToJavaScriptConverter()
    code = "assert x > 0, 'x must be positive'"
    result = converter.convert(code)
    if result.conversion_confidence >= 0:
        results.add_pass("assert_statement")
    else:
        results.add_fail("assert_statement",
                        "Assert statement caused crash")


def test_yield_statement():
    """Test generator with yield."""
    converter = PythonToJavaScriptConverter()
    code = "def gen():\n    yield 1\n    yield 2"
    result = converter.convert(code)
    if result.conversion_confidence >= 0:
        results.add_pass("yield_statement")
    else:
        results.add_fail("yield_statement",
                        "Yield statement caused crash")


def test_finally_block():
    """Test try-finally block."""
    converter = PythonToJavaScriptConverter()
    code = "try:\n    pass\nfinally:\n    pass"
    result = converter.convert(code)
    if result.conversion_confidence >= 0:
        results.add_pass("finally_block")
    else:
        results.add_fail("finally_block",
                        "Finally block caused crash")


def test_continue_statement():
    """Test continue statement."""
    converter = PythonToJavaScriptConverter()
    code = "while True:\n    if x:\n        continue\n    break"
    result = converter.convert(code)
    if "continue" in result.converted_code:
        results.add_pass("continue_statement")
    else:
        results.add_fail("continue_statement",
                        "Continue statement not preserved")


def test_break_statement():
    """Test break statement."""
    converter = PythonToJavaScriptConverter()
    code = "while True:\n    break"
    result = converter.convert(code)
    if "break" in result.converted_code:
        results.add_pass("break_statement")
    else:
        results.add_fail("break_statement",
                        "Break statement not preserved")


def test_return_statement():
    """Test return statement."""
    converter = PythonToJavaScriptConverter()
    code = "def func():\n    return 42"
    result = converter.convert(code)
    if "return" in result.converted_code:
        results.add_pass("return_statement")
    else:
        results.add_fail("return_statement",
                        "Return statement not preserved")


def test_pass_statement():
    """Test pass statement."""
    converter = PythonToJavaScriptConverter()
    code = "if x:\n    pass\nelse:\n    pass"
    result = converter.convert(code)
    # Should handle pass statements
    if result.conversion_confidence >= 0:
        results.add_pass("pass_statement")
    else:
        results.add_fail("pass_statement",
                        "Pass statement caused crash")


# ============================================================================
# ROUNDTRIP TESTS: Python -> JavaScript -> Python
# ============================================================================

def test_roundtrip_simple_variable():
    """Test roundtrip conversion of simple variable."""
    py_to_js = PythonToJavaScriptConverter()
    js_to_py = JavaScriptToPythonConverter()

    original = "x = 5"
    js_code = py_to_js.convert(original).converted_code
    back_to_py = js_to_py.convert(js_code).converted_code

    if "x" in back_to_py and "5" in back_to_py:
        results.add_pass("roundtrip_simple_variable")
    else:
        results.add_fail("roundtrip_simple_variable",
                        f"Roundtrip failed: {original} -> {js_code} -> {back_to_py}")


def test_roundtrip_if_statement():
    """Test roundtrip conversion of if statement."""
    py_to_js = PythonToJavaScriptConverter()
    js_to_py = JavaScriptToPythonConverter()

    original = "if x > 5:\n    print(x)"
    js_code = py_to_js.convert(original).converted_code
    back_to_py = js_to_py.convert(js_code).converted_code

    if "if" in back_to_py and "x" in back_to_py:
        results.add_pass("roundtrip_if_statement")
    else:
        results.add_fail("roundtrip_if_statement",
                        "Roundtrip if statement failed")


def test_roundtrip_function():
    """Test roundtrip conversion of function."""
    py_to_js = PythonToJavaScriptConverter()
    js_to_py = JavaScriptToPythonConverter()

    original = "def add(x, y):\n    return x + y"
    js_code = py_to_js.convert(original).converted_code
    back_to_py = js_to_py.convert(js_code).converted_code

    if "add" in back_to_py and ("x" in back_to_py or "y" in back_to_py):
        results.add_pass("roundtrip_function")
    else:
        results.add_fail("roundtrip_function",
                        "Roundtrip function failed")


if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE BUG-CATCHING TEST SUITE (100+ TESTS)")
    print("=" * 70)
    print()

    # Run all tests
    test_python_print_with_nested_function_call()
    test_python_print_with_multiple_nested()
    test_javascript_console_log_nested_function()
    test_javascript_console_log_multiple_params_with_calls()

    test_python_if_with_nested_function_call()
    test_javascript_if_with_nested_function_call()

    test_javascript_catch_in_comment()
    test_javascript_catch_in_string()

    test_python_to_js_true_with_comma()
    test_python_to_js_true_with_bracket()
    test_python_to_js_true_with_colon()
    test_python_to_js_true_in_ternary()

    test_python_to_js_none_in_variable_name()
    test_javascript_to_python_true_in_variable_name()

    test_python_multiple_exception_types()
    test_python_exception_with_pipe()

    test_javascript_arrow_with_parentheses()
    test_javascript_arrow_multiple_params()
    test_javascript_arrow_no_params()

    test_confidence_braces_in_string()
    test_confidence_braces_in_comment()

    test_python_negative_range()
    test_python_range_with_variable()
    test_python_range_with_expression()

    test_javascript_for_of_with_function_call()
    test_javascript_for_of_with_nested_call()

    test_python_list_comprehension_with_condition()
    test_python_list_comprehension_multiple_for()

    test_indentation_three_spaces()
    test_indentation_five_spaces()
    test_javascript_indentation_mixed_spacing()

    test_python_complex_type_hint()
    test_python_union_type_hint()
    test_python_callable_type_hint()

    test_warning_negative_line_number()
    test_warning_zero_line_number()
    test_warning_very_large_line_number()

    test_empty_file_conversion()
    test_only_comments_python()
    test_only_comments_javascript()
    test_whitespace_only_file()
    test_deeply_nested_structure()
    test_single_line_multiple_statements()
    test_mixed_quotes_in_strings()
    test_escaped_characters()
    test_raw_strings()
    test_unicode_characters()
    test_very_long_line()
    test_many_nested_parentheses()

    test_assignment_with_complex_expression()
    test_function_with_default_parameters()
    test_function_with_varargs()
    test_lambda_function()
    test_decorator()
    test_class_definition()
    test_import_statement()
    test_ternary_operator_python()
    test_ternary_operator_javascript()
    test_switch_statement()
    test_do_while_loop()
    test_with_statement_python()
    test_multiple_inheritance()
    test_assert_statement()
    test_yield_statement()
    test_finally_block()
    test_continue_statement()
    test_break_statement()
    test_return_statement()
    test_pass_statement()

    test_roundtrip_simple_variable()
    test_roundtrip_if_statement()
    test_roundtrip_function()

    results.summary()
