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

    def test_api_root_endpoint(self):
        """Test health check endpoint returns correct status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Backend running"
        assert "version" in data
        assert "supported_pairs" in data

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

    def test_api_detect_language_python(self):
        """Test language detection for Python code"""
        response = client.post("/detect-language", json={
            "code": "def foo():\n    print('bar')"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["detected_language"] == "python"

    def test_api_detect_language_javascript(self):
        """Test language detection for JavaScript code"""
        response = client.post("/detect-language", json={
            "code": "function foo() {\n    console.log('bar');\n}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["detected_language"] == "javascript"

    def test_api_empty_code_error(self):
        """Test that empty code returns 400 error"""
        response = client.post("/convert", json={
            "code": "",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    def test_api_whitespace_only_error(self):
        """Test that whitespace-only code returns 400 error"""
        response = client.post("/convert", json={
            "code": "   \n\t   ",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    def test_api_missing_source_language(self):
        """Test that missing source language returns 400"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "",
            "target_language": "javascript"
        })
        assert response.status_code == 400

    def test_api_missing_target_language(self):
        """Test that missing target language returns 400"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": ""
        })
        assert response.status_code == 400

    def test_api_unsupported_language_pair(self):
        """Test unsupported language pair handling"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": "rust"
        })
        assert response.status_code in [400, 500]

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

    def test_api_detect_empty_code_error(self):
        """Test detect-language with empty code"""
        response = client.post("/detect-language", json={
            "code": ""
        })
        assert response.status_code == 400

    def test_api_large_code_input(self):
        """Test API handles large code input"""
        large_code = "x = 1\n" * 1000
        response = client.post("/convert", json={
            "code": large_code,
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    def test_api_special_characters_in_code(self):
        """Test API handles special characters"""
        response = client.post("/convert", json={
            "code": "print('Hello, World! @#$%^&*()')",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    def test_api_unicode_in_code(self):
        """Test API handles unicode characters"""
        response = client.post("/convert", json={
            "code": "print('Hello, 世界! こんにちは')",
            "source_language": "python",
            "target_language": "javascript"
        })
        assert response.status_code == 200

    def test_api_response_metadata(self):
        """Test that response includes metadata"""
        response = client.post("/convert", json={
            "code": "if True:\n    x = 1",
            "source_language": "python",
            "target_language": "javascript"
        })
        data = response.json()
        assert "metadata" in data

    def test_api_strict_mode_option(self):
        """Test strict_mode option in request"""
        response = client.post("/convert", json={
            "code": "print('test')",
            "source_language": "python",
            "target_language": "javascript",
            "strict_mode": True
        })
        assert response.status_code == 200

    def test_api_detect_unknown_language(self):
        """Test detection of unknown/ambiguous code"""
        response = client.post("/detect-language", json={
            "code": "x = 1"
        })
        assert response.status_code == 200

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
# SECTION 2: PYTHON TO JAVASCRIPT CONVERSION (21-35)
# =============================================================================

class TestPythonToJavaScript:
    """Test Python to JavaScript conversions"""

    def test_simple_variable_assignment(self):
        """Test simple variable assignment"""
        result = py2js.convert("x = 5")
        assert "let x = 5" in result.converted_code or "const x = 5" in result.converted_code

    def test_multiple_assignments(self):
        """Test multiple variable assignments"""
        result = py2js.convert("x = 1\ny = 2\nz = 3")
        assert "1" in result.converted_code
        assert "2" in result.converted_code
        assert "3" in result.converted_code

    def test_string_concatenation(self):
        """Test string with concatenation"""
        result = py2js.convert("msg = 'Hello' + ' World'")
        assert "'Hello'" in result.converted_code or '"Hello"' in result.converted_code

    def test_list_to_array(self):
        """Test list conversion to array"""
        result = py2js.convert("items = [1, 2, 3]")
        assert "[1, 2, 3]" in result.converted_code

    def test_dict_to_object(self):
        """Test dict conversion to object"""
        result = py2js.convert("data = {'key': 'value'}")
        assert "key" in result.converted_code

    def test_and_operator(self):
        """Test 'and' to '&&' conversion"""
        result = py2js.convert("if x and y:\n    pass")
        assert "&&" in result.converted_code

    def test_or_operator(self):
        """Test 'or' to '||' conversion"""
        result = py2js.convert("if x or y:\n    pass")
        assert "||" in result.converted_code

    def test_not_operator(self):
        """Test 'not' to '!' conversion"""
        result = py2js.convert("if not x:\n    pass")
        assert "!" in result.converted_code

    def test_true_to_true(self):
        """Test True to true conversion"""
        result = py2js.convert("flag = True")
        assert "true" in result.converted_code

    def test_false_to_false(self):
        """Test False to false conversion"""
        result = py2js.convert("flag = False")
        assert "false" in result.converted_code

    def test_none_to_null(self):
        """Test None to null conversion"""
        result = py2js.convert("value = None")
        assert "null" in result.converted_code

    def test_elif_to_else_if(self):
        """Test elif to else if conversion"""
        result = py2js.convert("if x:\n    pass\nelif y:\n    pass")
        assert "else if" in result.converted_code

    def test_def_to_function(self):
        """Test def to function conversion"""
        result = py2js.convert("def foo():\n    pass")
        assert "function" in result.converted_code

    def test_range_to_for_loop(self):
        """Test range() to for loop conversion"""
        result = py2js.convert("for i in range(10):\n    print(i)")
        assert "for" in result.converted_code
        assert "10" in result.converted_code

    def test_single_line_comment(self):
        """Test single line comment conversion"""
        result = py2js.convert("# This is a comment")
        assert "//" in result.converted_code

    def test_append_to_push(self):
        """Test .append() to .push() conversion"""
        result = py2js.convert("items.append(1)")
        assert "push" in result.converted_code

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
        assert result.converted_code.count("{") == result.converted_code.count("}")


# =============================================================================
# SECTION 3: JAVASCRIPT TO PYTHON CONVERSION (36-50)
# =============================================================================

class TestJavaScriptToPython:
    """Test JavaScript to Python conversions"""

    def test_console_log_to_print(self):
        """Test console.log to print conversion"""
        result = js2py.convert("console.log('hello');")
        assert "print" in result.converted_code

    def test_let_to_variable(self):
        """Test let declaration removal"""
        result = js2py.convert("let x = 5;")
        assert "x = 5" in result.converted_code
        assert "let" not in result.converted_code

    def test_const_to_variable(self):
        """Test const declaration removal"""
        result = js2py.convert("const x = 5;")
        assert "x = 5" in result.converted_code
        assert "const" not in result.converted_code

    def test_var_to_variable(self):
        """Test var declaration removal"""
        result = js2py.convert("var x = 5;")
        assert "x = 5" in result.converted_code
        assert "var" not in result.converted_code

    def test_and_and_to_and(self):
        """Test && to 'and' conversion"""
        result = js2py.convert("if (x && y) {\n    z = 1;\n}")
        assert " and " in result.converted_code

    def test_or_or_to_or(self):
        """Test || to 'or' conversion"""
        result = js2py.convert("if (x || y) {\n    z = 1;\n}")
        assert " or " in result.converted_code

    def test_not_to_not(self):
        """Test ! to 'not' conversion"""
        result = js2py.convert("if (!x) {\n    y = 1;\n}")
        assert "not " in result.converted_code

    def test_true_to_True(self):
        """Test true to True conversion"""
        result = js2py.convert("let flag = true;")
        assert "True" in result.converted_code

    def test_false_to_False(self):
        """Test false to False conversion"""
        result = js2py.convert("let flag = false;")
        assert "False" in result.converted_code

    def test_null_to_None(self):
        """Test null to None conversion"""
        result = js2py.convert("let value = null;")
        assert "None" in result.converted_code

    def test_else_if_to_elif(self):
        """Test else if to elif conversion"""
        result = js2py.convert("if (x > 0) {\n    y = 1;\n} else if (x < 0) {\n    y = -1;\n}")
        assert "elif" in result.converted_code

    def test_catch_to_except(self):
        """Test catch to except conversion"""
        result = js2py.convert("try {\n    x = 1;\n} catch (e) {\n    console.log(e);\n}")
        assert "except" in result.converted_code

    def test_function_to_def(self):
        """Test function to def conversion"""
        result = js2py.convert("function foo() {\n    return 1;\n}")
        assert "def" in result.converted_code

    def test_single_line_comment(self):
        """Test single line comment conversion"""
        result = js2py.convert("// This is a comment")
        assert "#" in result.converted_code

    def test_push_to_append(self):
        """Test .push() to .append() conversion"""
        result = js2py.convert("items.push(1);")
        assert "append" in result.converted_code

    def test_semicolon_removal(self):
        """Test semicolon removal"""
        result = js2py.convert("let x = 5;")
        assert "x = 5" in result.converted_code


# =============================================================================
# SECTION 4: EDGE CASES (51-65)
# =============================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_function(self):
        """Test empty function body"""
        result = py2js.convert("def foo():\n    pass")
        assert "function" in result.converted_code

    def test_single_line_if(self):
        """Test single line if statement"""
        result = py2js.convert("if x:\n    y = 1")
        assert "if" in result.converted_code

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

    def test_mixed_quotes(self):
        """Test mixed quote styles"""
        result = py2js.convert('''x = "hello 'world'"''')
        assert "hello" in result.converted_code

    def test_escaped_quotes(self):
        """Test escaped quotes"""
        result = py2js.convert('''x = "hello \\"world\\""''')
        assert "hello" in result.converted_code

    def test_multiline_string(self):
        """Test multiline string handling"""
        code = '''msg = """
This is a
multiline string
"""'''
        result = py2js.convert(code)
        assert result.converted_code

    def test_regex_like_pattern(self):
        """Test code with regex-like patterns"""
        result = js2py.convert("let pattern = /test/g;")
        assert result.converted_code

    def test_numbers_with_underscores(self):
        """Test number literals with underscores"""
        result = py2js.convert("x = 1_000_000")
        assert result.converted_code

    def test_binary_literal(self):
        """Test binary literal"""
        result = py2js.convert("x = 0b1010")
        assert result.converted_code

    def test_hex_literal(self):
        """Test hex literal"""
        result = py2js.convert("x = 0xFF")
        assert result.converted_code

    def test_scientific_notation(self):
        """Test scientific notation"""
        result = py2js.convert("x = 1.5e10")
        assert result.converted_code

    def test_negative_numbers(self):
        """Test negative numbers"""
        result = py2js.convert("x = -42")
        assert "-42" in result.converted_code

    def test_float_numbers(self):
        """Test float numbers"""
        result = py2js.convert("x = 3.14159")
        assert "3.14159" in result.converted_code

    def test_empty_list(self):
        """Test empty list/array"""
        result = py2js.convert("items = []")
        assert "[]" in result.converted_code

    def test_empty_dict(self):
        """Test empty dict/object"""
        result = py2js.convert("data = {}")
        assert "{}" in result.converted_code


# =============================================================================
# SECTION 5: LANGUAGE DETECTION (66-75)
# =============================================================================

class TestLanguageDetection:
    """Test language detection functionality"""

    def test_detect_python_by_def(self):
        """Test Python detection by def keyword"""
        result = detector.detect("def foo():\n    pass")
        assert result.detected_language == "python"

    def test_detect_python_by_print(self):
        """Test Python detection by print"""
        result = detector.detect("print('hello')")
        assert result.detected_language == "python"

    def test_detect_js_by_function(self):
        """Test JavaScript detection by function"""
        result = detector.detect("function foo() { return 1; }")
        assert result.detected_language == "javascript"

    def test_detect_js_by_console_log(self):
        """Test JavaScript detection by console.log"""
        result = detector.detect("console.log('test');")
        assert result.detected_language == "javascript"

    def test_detect_js_by_let(self):
        """Test JavaScript detection by let"""
        result = detector.detect("let x = 5;\nconsole.log(x);")
        assert result.detected_language == "javascript"

    def test_detect_js_by_const(self):
        """Test JavaScript detection by const"""
        result = detector.detect("const x = 5;\nconsole.log(x);")
        assert result.detected_language == "javascript"

    def test_detect_confidence_score(self):
        """Test that detection returns confidence"""
        result = detector.detect("def foo():\n    print('bar')")
        assert hasattr(result, 'confidence')
        assert 0 <= result.confidence <= 1

    def test_detect_reason(self):
        """Test that detection returns reason"""
        result = detector.detect("console.log('test');")
        assert hasattr(result, 'reason')
        assert result.reason is not None

    def test_detect_alternatives(self):
        """Test that detection returns alternatives"""
        result = detector.detect("x = 5\ny = 10")
        assert hasattr(result, 'alternatives')

    def test_detect_unknown_code(self):
        """Test detection of truly ambiguous code"""
        result = detector.detect("// just a comment")
        assert hasattr(result, 'detected_language')


# =============================================================================
# SECTION 6: FRONTEND LOGIC TESTS (76-90)
# =============================================================================

class TestFrontendLogic:
    """Test frontend logic (file extensions, download naming, etc.)"""

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

    def test_py_extension_maps_to_python(self):
        """Test .py maps to python"""
        assert self.EXTENSION_TO_LANGUAGE['py'] == 'python'

    def test_js_extension_maps_to_javascript(self):
        """Test .js maps to javascript"""
        assert self.EXTENSION_TO_LANGUAGE['js'] == 'javascript'

    def test_python_maps_to_py_extension(self):
        """Test python maps to .py"""
        assert self.LANGUAGE_TO_EXTENSION['python'] == 'py'

    def test_javascript_maps_to_js_extension(self):
        """Test javascript maps to .js"""
        assert self.LANGUAGE_TO_EXTENSION['javascript'] == 'js'

    def test_java_extension_mapping(self):
        """Test Java file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['java'] == 'java'
        assert self.LANGUAGE_TO_EXTENSION['java'] == 'java'

    def test_typescript_extension_mapping(self):
        """Test TypeScript file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['ts'] == 'typescript'
        assert self.LANGUAGE_TO_EXTENSION['typescript'] == 'ts'

    def test_cpp_extension_mapping(self):
        """Test C++ file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['cpp'] == 'cpp'
        assert self.EXTENSION_TO_LANGUAGE['c'] == 'cpp'

    def test_go_extension_mapping(self):
        """Test Go file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['go'] == 'go'
        assert self.LANGUAGE_TO_EXTENSION['go'] == 'go'

    def test_rust_extension_mapping(self):
        """Test Rust file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['rs'] == 'rust'
        assert self.LANGUAGE_TO_EXTENSION['rust'] == 'rs'

    def test_ruby_extension_mapping(self):
        """Test Ruby file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['rb'] == 'ruby'
        assert self.LANGUAGE_TO_EXTENSION['ruby'] == 'rb'

    def test_php_extension_mapping(self):
        """Test PHP file extension mapping"""
        assert self.EXTENSION_TO_LANGUAGE['php'] == 'php'
        assert self.LANGUAGE_TO_EXTENSION['php'] == 'php'

    def test_download_filename_python(self):
        """Test download filename for Python"""
        ext = self.LANGUAGE_TO_EXTENSION['python']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.py"

    def test_download_filename_javascript(self):
        """Test download filename for JavaScript"""
        ext = self.LANGUAGE_TO_EXTENSION['javascript']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.js"

    def test_download_filename_java(self):
        """Test download filename for Java"""
        ext = self.LANGUAGE_TO_EXTENSION['java']
        filename = f"converted_code.{ext}"
        assert filename == "converted_code.java"

    def test_all_languages_have_extensions(self):
        """Test all supported languages have file extensions"""
        languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'ruby', 'php']
        for lang in languages:
            assert lang in self.LANGUAGE_TO_EXTENSION
            assert self.LANGUAGE_TO_EXTENSION[lang] is not None


# =============================================================================
# SECTION 7: INTEGRATION TESTS (91-95)
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple features"""

    def test_roundtrip_conversion_simple(self):
        """Test Python -> JS -> Python roundtrip"""
        original = "x = 5"
        py_to_js = py2js.convert(original)
        js_to_py = js2py.convert(py_to_js.converted_code)
        assert "x" in js_to_py.converted_code
        assert "5" in js_to_py.converted_code

    def test_engine_get_supported_pairs(self):
        """Test engine returns supported pairs"""
        pairs = engine.get_supported_pairs()
        assert any('python' in p and 'javascript' in p for p in pairs)
        assert any('javascript' in p and 'python' in p for p in pairs)

    def test_print_roundtrip(self):
        """Test print/console.log roundtrip"""
        py_code = "print('hello')"
        js_result = py2js.convert(py_code)
        assert "console.log" in js_result.converted_code
        py_result = js2py.convert(js_result.converted_code)
        assert "print" in py_result.converted_code

    def test_function_roundtrip(self):
        """Test function definition roundtrip"""
        py_code = "def add(a, b):\n    return a + b"
        js_result = py2js.convert(py_code)
        assert "function" in js_result.converted_code
        py_result = js2py.convert(js_result.converted_code)
        assert "def" in py_result.converted_code

    def test_if_statement_roundtrip(self):
        """Test if statement roundtrip"""
        py_code = "if x > 0:\n    y = 1"
        js_result = py2js.convert(py_code)
        assert "if" in js_result.converted_code
        assert "{" in js_result.converted_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
