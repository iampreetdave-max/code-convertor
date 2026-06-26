"""
Tests for the LLM-based Python to Java converter.

These tests verify:
1. Converter initialization and configuration
2. Response format compliance
3. Graceful error handling when API key is missing
4. Integration with the conversion engine
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from converters.python_to_java_llm import PythonToJavaLLMConverter, SYSTEM_PROMPT
from core.conversion_engine import ConversionEngine
from api.models import ConvertResponse


class TestPythonToJavaLLMConverter:
    """Test the PythonToJavaLLMConverter class."""

    def test_initialization_defaults(self):
        """Test converter initializes with correct defaults."""
        converter = PythonToJavaLLMConverter()
        assert converter.source_lang == "python"
        assert converter.target_lang == "java"
        assert converter.model == "claude-sonnet-4-5-20250929"

    def test_initialization_custom_model(self):
        """Test converter accepts custom model."""
        converter = PythonToJavaLLMConverter(model="claude-opus-4-5-20250929")
        assert converter.model == "claude-opus-4-5-20250929"

    def test_empty_code_returns_empty_response(self):
        """Test that empty code returns appropriate response."""
        converter = PythonToJavaLLMConverter()
        result = converter.convert("")

        assert result.converted_code == ""
        assert result.conversion_confidence == 1.0
        assert "No code provided" in result.warnings
        assert result.metadata["method"] == "llm"

    def test_whitespace_only_code_returns_empty_response(self):
        """Test that whitespace-only code returns appropriate response."""
        converter = PythonToJavaLLMConverter()
        result = converter.convert("   \n\t\n  ")

        assert result.converted_code == ""
        assert "No code provided" in result.warnings

    def test_missing_api_key_returns_error(self):
        """Test graceful handling when API key is missing."""
        # Ensure no API key in environment
        with patch.dict(os.environ, {}, clear=True):
            # Remove ANTHROPIC_API_KEY if it exists
            if "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]

            converter = PythonToJavaLLMConverter(api_key=None)
            # Manually clear api_key to simulate missing key
            converter.api_key = None
            result = converter.convert("x = 5")

            assert result.conversion_confidence == 0.0
            assert any("ANTHROPIC_API_KEY" in w for w in result.warnings)
            assert result.metadata.get("error") is not None

    def test_confidence_extraction_high(self):
        """Test confidence extraction for HIGH confidence."""
        converter = PythonToJavaLLMConverter()
        code = """public class Main {
    public static void main(String[] args) {
        int x = 5;
    }
}
// Conversion confidence: HIGH"""
        confidence, reason = converter._extract_confidence(code)
        assert confidence == 0.95
        assert reason == ""

    def test_confidence_extraction_medium(self):
        """Test confidence extraction for MEDIUM confidence."""
        converter = PythonToJavaLLMConverter()
        code = """// Some code
// Conversion confidence: MEDIUM - duck typing approximated"""
        confidence, reason = converter._extract_confidence(code)
        assert confidence == 0.75
        assert "duck typing" in reason.lower()

    def test_confidence_extraction_low(self):
        """Test confidence extraction for LOW confidence."""
        converter = PythonToJavaLLMConverter()
        code = """// Some code
// Conversion confidence: LOW - metaclasses not supported"""
        confidence, reason = converter._extract_confidence(code)
        assert confidence == 0.50
        assert "metaclasses" in reason.lower()

    def test_confidence_extraction_default(self):
        """Test default confidence when not specified."""
        converter = PythonToJavaLLMConverter()
        code = """public class Main {}"""
        confidence, reason = converter._extract_confidence(code)
        assert confidence == 0.80
        assert reason == ""

    def test_warning_extraction(self):
        """Test warning extraction from code comments."""
        converter = PythonToJavaLLMConverter()
        code = """// WARNING: Type inference uncertain
// Note: Consider using generics
int x = 5;"""
        warnings = converter._extract_warnings(code)
        assert len(warnings) == 2
        assert any("Type inference" in w for w in warnings)
        assert any("generics" in w for w in warnings)

    def test_unsupported_construct_detection(self):
        """Test detection of TODO comments indicating uncertainty."""
        converter = PythonToJavaLLMConverter()
        code = """int x = 5; // TODO: verify type
String y = "hello";
Object z = null; // TODO: verify type inference"""
        unsupported = converter._detect_unsupported(code)
        assert len(unsupported) == 2
        assert all(u["type"] == "warning" for u in unsupported)

    def test_response_format_compliance(self):
        """Test that response matches ConvertResponse schema."""
        converter = PythonToJavaLLMConverter()
        # Test with empty code to avoid API call
        result = converter.convert("")

        assert isinstance(result, ConvertResponse)
        assert hasattr(result, "converted_code")
        assert hasattr(result, "source_language")
        assert hasattr(result, "target_language")
        assert hasattr(result, "conversion_confidence")
        assert hasattr(result, "warnings")
        assert hasattr(result, "unsupported_constructs")
        assert hasattr(result, "unsupported_lines_count")
        assert hasattr(result, "conversion_level")
        assert hasattr(result, "metadata")

    def test_system_prompt_completeness(self):
        """Test that system prompt contains key conversion rules."""
        # Type inference rules
        assert "int x = 5" in SYSTEM_PROMPT
        assert "ArrayList" in SYSTEM_PROMPT
        assert "HashMap" in SYSTEM_PROMPT

        # Method mappings
        assert "list.add" in SYSTEM_PROMPT
        assert "System.out.println" in SYSTEM_PROMPT

        # Control flow
        assert "else if" in SYSTEM_PROMPT
        assert "for (int i = 0" in SYSTEM_PROMPT

        # Exception handling
        assert "IllegalArgumentException" in SYSTEM_PROMPT
        assert "catch (Exception" in SYSTEM_PROMPT


class TestConversionEngineIntegration:
    """Test integration with ConversionEngine."""

    def test_python_java_pair_registered(self):
        """Test that Python→Java converter is registered."""
        engine = ConversionEngine()
        assert ("python", "java") in engine.converters

    def test_python_java_in_supported_pairs(self):
        """Test that Python→Java appears in supported pairs."""
        engine = ConversionEngine()
        pairs = engine.get_supported_pairs()
        assert "python→java" in pairs

    def test_converter_instantiation(self):
        """Test that engine can instantiate the converter."""
        engine = ConversionEngine()
        converter_class = engine.converters[("python", "java")]
        converter = converter_class()
        assert isinstance(converter, PythonToJavaLLMConverter)


class TestMockedAPIConversion:
    """Test conversion with mocked API calls."""

    def test_successful_conversion_mock(self):
        """Test successful conversion with mocked API response."""
        converter = PythonToJavaLLMConverter(api_key="test-key")

        # Mock the API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="""// Converted from Python by CodeConvertor
// Source language: Python
// Target language: Java

import java.util.*;

public class Main {
    public static void main(String[] args) {
        int x = 5;
        System.out.println(x);
    }
}
// Conversion confidence: HIGH""")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 150

        # Create a mock client and inject it
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        converter._client = mock_client

        result = converter.convert("x = 5\nprint(x)")

        assert "public class Main" in result.converted_code
        assert "int x = 5" in result.converted_code
        assert result.conversion_confidence == 0.95
        assert result.conversion_level == 3
        assert result.metadata["method"] == "llm"

    def test_api_error_handling(self):
        """Test graceful handling of API errors."""
        converter = PythonToJavaLLMConverter(api_key="test-key")

        # Create a mock client that raises an error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")
        converter._client = mock_client

        result = converter.convert("x = 5")

        assert result.conversion_confidence == 0.0
        assert "rate limit" in result.warnings[0].lower()
        assert "error" in result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
