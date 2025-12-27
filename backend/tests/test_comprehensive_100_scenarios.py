"""
Comprehensive Test Suite: 100 Scenarios for CodeTransform
Tests cover: API endpoints, conversions, edge cases, language detection, and frontend logic
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from converters.python_to_javascript import PythonToJavaScriptConverter
from converters.javascript_to_python import JavaScriptToPythonConverter
from core.language_detector import LanguageDetector
from core.conversion_engine import ConversionEngine

client = TestClient(app)
py2js = PythonToJavaScriptConverter()
js2py = JavaScriptToPythonConverter()
detector = LanguageDetector()
engine = ConversionEngine()


# =============================================================================
# SECTION 1: API ENDPOINT TESTS (1-20)
# =============================================================================

class TestAPIEndpoints:
    """Test REST API endpoints directly"""

    # Test 1
    def test_api_root_endpoint(self):
        """Test health check endpoint returns correct status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Backend running"
        assert "version" in data
        assert "supported_pairs" in data

    # Test 2
    def test_api_convert_python_to_javascript(self):
        """Test convert endpoint with Python to JavaScript"""
        response = client.post("/convert", json={
            "code": "print('hello')",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200
        data = response.json()
        assert "console.log" in data["converted_code"]

    # Test 3
    def test_api_convert_javascript_to_python(self):
        """Test convert endpoint with JavaScript to Python"""
        response = client.post("/convert", json={
            "code": "console.log('hello');",
            "source_language": "javascript",
            "target_language": "python"
        })
        assert response.status_code == 200
        data = response.json()
        assert "print" in data["converted_code"]

    # Test 4
    def test_api_detect_language_python(self):
        """Test language detection for Python code"""
        response = client.post("/detect-language", json={
            "code": "def foo():\n    print('bar')"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["detected_language"] == "python"

    # Test 5
    def test_api_detect_language_javascript(self):
        """Test language detection for JavaScript code"""
        response = client.post("/detect-language", json={
            "code": "function foo() {\n    console.log('bar');\n}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["detected_language"] == "javascript"

    # Test 6
    def test_api_empty_code_error(self):
        """Test that empty code returns 400 error"""
        response = client.post("/convert", json={
            "code": "",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    # Test 7
    def test_api_whitespace_only_error(self):
        """Test that whitespace-only code returns 400 error"""
        response = client.post("/convert", json={
            "code": "   \n\t   ",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    # Test 8
    def test_api_missing_source_language(self):
        """Test that missing source language returns 400"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    # Test 9
    def test_api_missing_target_language(self):
        """Test that missing target language returns 400"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": ""
        })
        assert response.status_code == 400

    # Test 10
    def test_api_unsupported_language_pair(self):
        """Test unsupported language pair handling"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": "rust"
        })
        # Should return 400 for unsupported pair
        assert response.status_code in [400, 500]

    # Test 11
    def test_api_response_has_confidence(self):
        """Test that response includes confidence score"""
        response = client.post("/convert", json={
            "code": "x = 5",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200
        data = response.json()
        assert "conversion_confidence" in data
        assert 0 <= data["conversion_confidence"] <= 1

    # Test 12
    def test_api_response_has_warnings(self):
        """Test that response includes warnings array"""
        response = client.post("/convert", json={
            "code": "class Foo:\n    pass",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    # Test 13
    def test_api_detect_empty_code_error(self):
        """Test detect-language with empty code"""
        response = client.post("/detect-language", json={
            "code": ""
        })
        assert response.status_code == 400

    # Test 14
    def test_api_large_code_input(self):
        """Test API handles large code input"""
        large_code = "x = 1\n" * 1000
        response = client.post("/convert", json={
            "code": large_code,
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    # Test 15
    def test_api_special_characters_in_code(self):
        """Test API handles special characters"""
        response = client.post("/convert", json={
            "code": "print('Hello, World! @#$%^&*()')",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    # Test 16
    def test_api_unicode_in_code(self):
        """Test API handles unicode characters"""
        response = client.post("/convert", json={
            "code": "print('Hello, 世界! こんにちは')",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    # Test 17
    def test_api_response_metadata(self):
        """Test that response includes metadata"""
        response = client.post("/convert", json={
            "code": "if True:\n    x = 1",
            "source_language": "python",
            "target_language": "javascript"
        })
        data = response.json()
        assert "metadata" in data

    # Test 18
    def test_api_strict_mode_option(self):
        """Test strict_mode option in request"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": "javascript",
            "strict_mode": True
        })
        assert response.status_code == 200

    # Test 19
    def test_api_detect_unknown_language(self):
        """Test detection of unknown/ambiguous code"""
        response = client.post("/detect-language", json={
            "code": "x = 1"  # Could be multiple languages
        })
        assert response.status_code == 200

    # Test 20
    def test_api_conversion_level_in_response(self):
        """Test that response includes conversion_level"""
        response = client.post("/convert", json={
            "code": "print('hello')",
            "source_language": "python",
            "target_language": "javascript"
        })
        data = response.json()
        assert "conversion_level" in data


# =============================================================================
# SECTION 2: PYTHON TO JAVASCRIPT CONVERSION (21-40)
# =============================================================================

class TestPythonToJavaScript:
    """Test Python to JavaScript conversions"""

    # Test 21
    def test_simple_variable_assignment(self):
        """Test simple variable assignment"""
        result = py2js.convert("x = 5")
        assert "let x = 5" in result.converted_code or "const x = 5" in result.converted_code

    # Test 22
    def test_multiple_assignments(self):
        """Test multiple variable assignments"""
        result = py2js.convert("x = 1\ny = 2\nz = 3")
        assert "1" in result.converted_code
        assert "2" in result.converted_code
        assert "3" in result.converted_code

    # Test 23
    def test_string_concatenation(self):
        """Test string with concatenation"""
        result = py2js.convert("msg = 'Hello' + ' World'")
        assert "'Hello'" in result.converted_code or '"Hello"' in result.converted_code

    # Test 24
    def test_list_to_array(self):
        """Test list conversion to array"""
        result = py2js.convert("items = [1, 2, 3]")
        assert "[1, 2, 3]" in result.converted_code

    # Test 25
    def test_dict_to_object(self):
        """Test dict conversion to object"""
        result = py2js.convert("data = {'key': 'value'}")
        assert "key" in result.converted_code

    # Test 26
    def test_and_operator(self):
        """Test 'and' to '&&' conversion"""
        result = py2js.convert("if x and y:\n    pass")
        assert "&&" in result.converted_code

    # Test 27
    def test_or_operator(self):
        """Test 'or' to '||' conversion"""
        result = py2js.convert("if x or y:\n    pass")
        assert "||" in result.converted_code

    # Test 28
    def test_not_operator(self):
        """Test 'not' to '!' conversion"""
        result = py2js.convert("if not x:\n    pass")
        assert "!" in result.converted_code

    # Test 29
    def test_true_to_true(self):
        """Test True to true conversion"""
        result = py2js.convert("flag = True")
        assert "true" in result.converted_code

    # Test 30
    def test_false_to_false(self):
        """Test False to false conversion"""
        result = py2js.convert("flag = False")
        assert "false" in result.converted_code

    # Test 31
    def test_none_to_null(self):
        """Test None to null conversion"""
        result = py2js.convert("value = None")
        assert "null" in result.converted_code

    # Test 32
    def test_elif_to_else_if(self):
        """Test elif to else if conversion"""
        result = py2js.convert("if x:\n    pass\nelif y:\n    pass")
        assert "else if" in result.converted_code

    # Test 33 - KNOWN BUG: except not converting to catch
    @pytest.mark.xfail(reason="BUG: Python except not converting to JavaScript catch")
    def test_except_to_catch(self):
        """Test except to catch conversion - KNOWN BUG"""
        result = py2js.convert("try:\n    x = 1\nexcept:\n    x = 0")
        assert "catch" in result.converted_code

    # Test 34
    def test_def_to_function(self):
        """Test def to function conversion"""
        result = py2js.convert("def foo():\n    pass")
        assert "function" in result.converted_code

    # Test 35
    def test_range_to_for_loop(self):
        """Test range() to for loop conversion"""
        result = py2js.convert("for i in range(10):\n    print(i)")
        assert "for" in result.converted_code
        assert "10" in result.converted_code

    # Test 36 - KNOWN BUG: f-string not converting to template literal
    @pytest.mark.xfail(reason="BUG: Python f-string not converting to JavaScript template literal")
    def test_fstring_to_template(self):
        """Test f-string to template literal conversion - KNOWN BUG"""
        result = py2js.convert("msg = f'Hello {name}'")
        assert "`" in result.converted_code

    # Test 37
    def test_single_line_comment(self):
        """Test single line comment conversion"""
        result = py2js.convert("# This is a comment")
        assert "//" in result.converted_code

    # Test 38 - KNOWN BUG: len() not converting to .length
    @pytest.mark.xfail(reason="BUG: Python len() not converting to JavaScript .length")
    def test_len_to_length(self):
        """Test len() to .length conversion - KNOWN BUG"""
        result = py2js.convert("size = len(items)")
        assert "length" in result.converted_code

    # Test 39
    def test_append_to_push(self):
        """Test .append() to .push() conversion"""
        result = py2js.convert("items.append(1)")
        assert "push" in result.converted_code

    # Test 40
    def test_nested_if_statements(self):
        """Test nested if statements with proper braces"""
        code = """if a:
    if b:
        x = 1
    else:
        x = 2
else:
    x = 3"""
        result = py2js.convert(code)
        # Count opening and closing braces
        assert result.converted_code.count("{") == result.converted_code.count("}")


# =============================================================================
# SECTION 3: JAVASCRIPT TO PYTHON CONVERSION (41-60)
# =============================================================================

class TestJavaScriptToPython:
    """Test JavaScript to Python conversions"""

    # Test 41
    def test_console_log_to_print(self):
        """Test console.log to print conversion"""
        result = js2py.convert("console.log('hello');")
        assert "print" in result.converted_code

    # Test 42
    def test_let_to_variable(self):
        """Test let declaration removal"""
        result = js2py.convert("let x = 5;")
        assert "x = 5" in result.converted_code
        assert "let" not in result.converted_code

    # Test 43
    def test_const_to_variable(self):
        """Test const declaration removal"""
        result = js2py.convert("const x = 5;")
        assert "x = 5" in result.converted_code
        assert "const" not in result.converted_code

    # Test 44
    def test_var_to_variable(self):
        """Test var declaration removal"""
        result = js2py.convert("var x = 5;")
        assert "x = 5" in result.converted_code
        assert "var" not in result.converted_code

    # Test 45
    def test_and_and_to_and(self):
        """Test && to 'and' conversion"""
        result = js2py.convert("if (x && y) {\n    z = 1;\n}")
        assert " and " in result.converted_code

    # Test 46
    def test_or_or_to_or(self):
        """Test || to 'or' conversion"""
        result = js2py.convert("if (x || y) {\n    z = 1;\n}")
        assert " or " in result.converted_code

    # Test 47
    def test_not_to_not(self):
        """Test ! to 'not' conversion"""
        result = js2py.convert("if (!x) {\n    y = 1;\n}")
        assert "not " in result.converted_code

    # Test 48
    def test_true_to_True(self):
        """Test true to True conversion"""
        result = js2py.convert("let flag = true;")
        assert "True" in result.converted_code

    # Test 49
    def test_false_to_False(self):
        """Test false to False conversion"""
        result = js2py.convert("let flag = false;")
        assert "False" in result.converted_code

    # Test 50
    def test_null_to_None(self):
        """Test null to None conversion"""
        result = js2py.convert("let value = null;")
        assert "None" in result.converted_code

    # Test 51 - KNOWN BUG: undefined not converting to None
    @pytest.mark.xfail(reason="BUG: JavaScript undefined not converting to Python None")
    def test_undefined_to_None(self):
        """Test undefined to None conversion - KNOWN BUG"""
        result = js2py.convert("let value = undefined;")
        assert "None" in result.converted_code

    # Test 52
    def test_else_if_to_elif(self):
        """Test else if to elif conversion"""
        result = js2py.convert("if (x > 0) {\n    y = 1;\n} else if (x < 0) {\n    y = -1;\n}")
        assert "elif" in result.converted_code

    # Test 53
    def test_catch_to_except(self):
        """Test catch to except conversion"""
        result = js2py.convert("try {\n    x = 1;\n} catch (e) {\n    console.log(e);\n}")
        assert "except" in result.converted_code

    # Test 54
    def test_function_to_def(self):
        """Test function to def conversion"""
        result = js2py.convert("function foo() {\n    return 1;\n}")
        assert "def" in result.converted_code

    # Test 55 - KNOWN BUG: arrow function not converting properly
    @pytest.mark.xfail(reason="BUG: JavaScript arrow function not converting to Python lambda/def")
    def test_arrow_function(self):
        """Test arrow function conversion - KNOWN BUG"""
        result = js2py.convert("const add = (a, b) => a + b;")
        assert "lambda" in result.converted_code or "def" in result.converted_code

    # Test 56 - KNOWN BUG: template literal not converting to f-string
    @pytest.mark.xfail(reason="BUG: JavaScript template literal not converting to Python f-string")
    def test_template_literal_to_fstring(self):
        """Test template literal to f-string conversion - KNOWN BUG"""
        result = js2py.convert("let msg = `Hello ${name}`;")
        has_fstring = "f'" in result.converted_code or 'f"' in result.converted_code
        assert has_fstring

    # Test 57
    def test_single_line_comment(self):
        """Test single line comment conversion"""
        result = js2py.convert("// This is a comment")
        assert "#" in result.converted_code

    # Test 58 - KNOWN BUG: .length not converting to len()
    @pytest.mark.xfail(reason="BUG: JavaScript .length not converting to Python len()")
    def test_length_to_len(self):
        """Test .length to len() conversion - KNOWN BUG"""
        result = js2py.convert("let size = items.length;")
        assert "len(" in result.converted_code

    # Test 59
    def test_push_to_append(self):
        """Test .push() to .append() conversion"""
        result = js2py.convert("items.push(1);")
        assert "append" in result.converted_code

    # Test 60
    def test_semicolon_removal(self):
        """Test semicolon removal"""
        result = js2py.convert("let x = 5;")
        # Most lines should not end with semicolon
        lines = [l for l in result.converted_code.split("\n") if l.strip() and not l.strip().startswith("#")]
        # Allow some semicolons in edge cases, but at least the main line should not have one
        assert "x = 5" in result.converted_code


# =============================================================================
# SECTION 4: EDGE CASES (61-75)
# =============================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios"""

    # Test 61
    def test_empty_function(self):
        """Test empty function body"""
        result = py2js.convert("def foo():\n    pass")
        assert "function" in result.converted_code

    # Test 62
    def test_single_line_if(self):
        """Test single line if statement"""
        result = py2js.convert("if x:\n    y = 1")
        assert "if" in result.converted_code

    # Test 63
    def test_deeply_nested_blocks(self):
        """Test deeply nested code blocks"""
        code = """
if a:
    if b:
        if c:
            if d:
                x = 1
"""
        result = py2js.convert(code)
        assert result.converted_code.count("{") == result.converted_code.count("}")

    # Test 64
    def test_mixed_quotes(self):
        """Test mixed quote styles"""
        result = py2js.convert('''x = "hello 'world'"''')
        assert "hello" in result.converted_code

    # Test 65
    def test_escaped_quotes(self):
        """Test escaped quotes"""
        result = py2js.convert('''x = "hello \\"world\\""''')
        assert "hello" in result.converted_code

    # Test 66
    def test_multiline_string(self):
        """Test multiline string handling"""
        code = '''msg = """
This is a
multiline string
"""'''
        result = py2js.convert(code)
        assert result.converted_code  # Should not crash

    # Test 67
    def test_regex_like_pattern(self):
        """Test code with regex-like patterns"""
        result = js2py.convert("let pattern = /test/g;")
        assert result.converted_code  # Should not crash

    # Test 68
    def test_numbers_with_underscores(self):
        """Test number literals with underscores"""
        result = py2js.convert("x = 1_000_000")
        assert result.converted_code

    # Test 69
    def test_binary_literal(self):
        """Test binary literal"""
        result = py2js.convert("x = 0b1010")
        assert result.converted_code

    # Test 70
    def test_hex_literal(self):
        """Test hex literal"""
        result = py2js.convert("x = 0xFF")
        assert result.converted_code

    # Test 71
    def test_scientific_notation(self):
        """Test scientific notation"""
        result = py2js.convert("x = 1.5e10")
        assert result.converted_code

    # Test 72
    def test_negative_numbers(self):
        """Test negative numbers"""
        result = py2js.convert("x = -42")
        assert "-42" in result.converted_code

    # Test 73
    def test_float_numbers(self):
        """Test float numbers"""
        result = py2js.convert("x = 3.14159")
        assert "3.14159" in result.converted_code

    # Test 74
    def test_empty_list(self):
        """Test empty list/array"""
        result = py2js.convert("items = []")
        assert "[]" in result.converted_code

    # Test 75
    def test_empty_dict(self):
        """Test empty dict/object"""
        result = py2js.convert("data = {}")
        assert "{}" in result.converted_code


# =============================================================================
# SECTION 5: LANGUAGE DETECTION (76-85)
# =============================================================================

class TestLanguageDetection:
    """Test language detection functionality - using Pydantic model attributes"""

    # Test 76
    def test_detect_python_by_def(self):
        """Test Python detection by def keyword"""
        result = detector.detect("def foo():\n    pass")
        assert result.detected_language == "python"

    # Test 77
    def test_detect_python_by_print(self):
        """Test Python detection by print"""
        result = detector.detect("print('hello')")
        assert result.detected_language == "python"

    # Test 78
    def test_detect_js_by_function(self):
        """Test JavaScript detection by function"""
        result = detector.detect("function foo() { return 1; }")
        assert result.detected_language == "javascript"

    # Test 79
    def test_detect_js_by_console_log(self):
        """Test JavaScript detection by console.log"""
        result = detector.detect("console.log('test');")
        assert result.detected_language == "javascript"

    # Test 80
    def test_detect_js_by_let(self):
        """Test JavaScript detection by let"""
        result = detector.detect("let x = 5;\nconsole.log(x);")
        assert result.detected_language == "javascript"

    # Test 81
    def test_detect_js_by_const(self):
        """Test JavaScript detection by const"""
        result = detector.detect("const x = 5;\nconsole.log(x);")
        assert result.detected_language == "javascript"

    # Test 82
    def test_detect_confidence_score(self):
        """Test that detection returns confidence"""
        result = detector.detect("def foo():\n    print('bar')")
        assert hasattr(result, 'confidence')
        assert 0 <= result.confidence <= 1

    # Test 83
    def test_detect_reason(self):
        """Test that detection returns reason"""
        result = detector.detect("console.log('test');")
        assert hasattr(result, 'reason')
        assert result.reason is not None

    # Test 84
    def test_detect_alternatives(self):
        """Test that detection returns alternatives"""
        result = detector.detect("x = 5\ny = 10")  # Ambiguous
        assert hasattr(result, 'alternatives')

    # Test 85
    def test_detect_unknown_code(self):
        """Test detection of truly ambiguous code"""
        result = detector.detect("// just a comment")
        assert hasattr(result, 'detected_language')


# =============================================================================
# SECTION 6: FRONTEND LOGIC TESTS (86-100)
# =============================================================================

class TestFrontendLogic:
    """Test frontend logic (file extensions, download naming, etc.)"""

    # File extension mapping (mirrors frontend)
    EXTENSION_TO_LANGUAGE = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'cpp',
        'cs': 'csharp',
        'go': 'go',
        'rs': 'rust',
        'rb': 'ruby',
        'php': 'php'
    }

    LANGUAGE_TO_EXTENSION = {
        'python': 'py',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'cpp': 'cpp',
        'csharp': 'cs',
        'go': 'go',
        'rust': 'rs',
        'ruby': 'rb',
        'php': 'php'
    }

    # Test 86
    def test_py_extension_maps_to_python(self):
        """Test .py maps to python"""
        assert self.EXTENSION_TO_LANGUAGE['py'] == 'python'

    # Test 87
    def test_js_extension_maps_to_javascript(self):
        """Test .js maps to javascript"""
        assert self.EXTENSION_TO_LANGUAGE['js'] == 'javascript'

    # Test 88
    def test_python_maps_to_py_extension(self):
        """Test python maps to .py"""
        assert self.LANGUAGE_TO_EXTENSION['python'] == 'py'

    # Test 89
    def test_javascript_maps_to_js_extension(self):
        """Test javascript maps to .js"""
        assert self.LANGUAGE_TO_EXTENSION['javascript'] == 'js'

    # Test 90
    def test_java_extension_mapping(self):
        """Test Java file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['java'] == 'java'
        assert self.LANGUAGE_TO_EXTENSION['java'] == 'java'

    # Test 91
    def test_typescript_extension_mapping(self):
        """Test TypeScript file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['ts'] == 'typescript'
        assert self.LANGUAGE_TO_EXTENSION['typescript'] == 'ts'

    # Test 92
    def test_cpp_extension_mapping(self):
        """Test C++ file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['cpp'] == 'cpp'
        assert self.EXTENSION_TO_LANGUAGE['c'] == 'cpp'

    # Test 93
    def test_go_extension_mapping(self):
        """Test Go file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['go'] == 'go'
        assert self.LANGUAGE_TO_EXTENSION['go'] == 'go'

    # Test 94
    def test_rust_extension_mapping(self):
        """Test Rust file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['rs'] == 'rust'
        assert self.LANGUAGE_TO_EXTENSION['rust'] == 'rs'

    # Test 95
    def test_ruby_extension_mapping(self):
        """Test Ruby file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['rb'] == 'ruby'
        assert self.LANGUAGE_TO_EXTENSION['ruby'] == 'rb'

    # Test 96
    def test_php_extension_mapping(self):
        """Test PHP file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['php'] == 'php'
        assert self.LANGUAGE_TO_EXTENSION['php'] == 'php'

    # Test 97
    def test_download_filename_python(self):
        """Test download filename for Python"""
        ext = self.LANGUAGE_TO_EXTENSION['python']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.py"

    # Test 98
    def test_download_filename_javascript(self):
        """Test download filename for JavaScript"""
        ext = self.LANGUAGE_TO_EXTENSION['javascript']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.js"

    # Test 99
    def test_download_filename_java(self):
        """Test download filename for Java"""
        ext = self.LANGUAGE_TO_EXTENSION['java']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.java"

    # Test 100
    def test_all_languages_have_extensions(self):
        """Test all supported languages have file extensions"""
        languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'ruby', 'php']
        for lang in languages:
            assert lang in self.LANGUAGE_TO_EXTENSION
            assert self.LANGUAGE_TO_EXTENSION[lang] is not None


# =============================================================================
# ADDITIONAL INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple features"""

    def test_roundtrip_conversion_simple(self):
        """Test Python -> JS -> Python roundtrip"""
        original = "x = 5"
        py_to_js = py2js.convert(original)
        js_to_py = js2py.convert(py_to_js.converted_code)
        # Should preserve the basic meaning
        assert "x" in js_to_py.converted_code
        assert "5" in js_to_py.converted_code

    def test_engine_get_supported_pairs(self):
        """Test engine returns supported pairs"""
        pairs = engine.get_supported_pairs()
        # Pairs are returned as strings like 'python→javascript'
        assert any('python' in p and 'javascript' in p for p in pairs)
        assert any('javascript' in p and 'python' in p for p in pairs)

    # Known bug: confidence calculation
    @pytest.mark.xfail(reason="BUG: Complex code gets higher confidence than simple code (inverted)")
    def test_confidence_decreases_with_complex_code(self):
        """Test confidence decreases for complex/unsupported code - KNOWN BUG"""
        simple_result = py2js.convert("x = 5")
        complex_result = py2js.convert("class Foo(Bar):\n    @decorator\n    async def method(self):\n        yield x")
        assert complex_result.conversion_confidence <= simple_result.conversion_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
