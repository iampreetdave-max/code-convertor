from typing import Dict
from api.models import ConvertResponse
from core.language_detector import LanguageDetector
from converters.python_to_javascript import PythonToJavaScriptConverter
from converters.javascript_to_python import JavaScriptToPythonConverter


class ConversionEngine:
    """Orchestrates code conversion between supported language pairs."""

    def __init__(self):
        """Initialize the conversion engine with available converters."""
        self.detector = LanguageDetector()
        self.converters: Dict[tuple, type] = {
            ("python", "javascript"): PythonToJavaScriptConverter,
            ("javascript", "python"): JavaScriptToPythonConverter,
            # Future pairs can be added here
            # ("python", "java"): PythonToJavaConverter,
            # etc.
        }

    def convert(
        self,
        code: str,
        source_language: str,
        target_language: str,
        strict_mode: bool = False
    ) -> ConvertResponse:
        """
        Convert code from source language to target language.

        Args:
            code: Source code to convert
            source_language: Source language (e.g., "python")
            target_language: Target language (e.g., "javascript")
            strict_mode: If True, fail on unsupported constructs; if False, best-effort

        Returns:
            ConvertResponse with converted code and metadata

        Raises:
            ValueError: If language pair is not supported or invalid
        """
        # Validate inputs
        if not code.strip():
            return ConvertResponse(
                converted_code="",
                source_language=source_language,
                target_language=target_language,
                conversion_confidence=1.0,
                warnings=["No code provided"],
                unsupported_constructs=[],
                unsupported_lines_count=0,
                conversion_level=1,
                metadata={}
            )

        if source_language == target_language:
            return ConvertResponse(
                converted_code=code,
                source_language=source_language,
                target_language=target_language,
                conversion_confidence=1.0,
                warnings=["Source and target languages are the same"],
                unsupported_constructs=[],
                unsupported_lines_count=0,
                conversion_level=0,
                metadata={"lines_processed": len(code.split("\n"))}
            )

        # Check if conversion is supported
        key = (source_language.lower(), target_language.lower())
        if key not in self.converters:
            supported_pairs = ", ".join([f"{s}→{t}" for s, t in self.converters.keys()])
            raise ValueError(
                f"Conversion from {source_language} to {target_language} is not yet supported. "
                f"Supported pairs: {supported_pairs}"
            )

        # Get appropriate converter
        converter_class = self.converters[key]
        converter = converter_class()

        # Perform conversion
        try:
            result = converter.convert(code)

            # In strict mode, fail if unsupported constructs found
            if strict_mode and result.unsupported_lines_count > 0:
                result.warnings.insert(
                    0,
                    f"STRICT MODE: Found {result.unsupported_lines_count} unsupported constructs. "
                    f"Conversion aborted. Review unsupported_constructs for details."
                )

            return result

        except Exception as e:
            # Return best-effort response with error
            return ConvertResponse(
                converted_code=code,  # Return original as fallback
                source_language=source_language,
                target_language=target_language,
                conversion_confidence=0.0,
                warnings=[f"Conversion error: {str(e)}", "Returned original code"],
                unsupported_constructs=[],
                unsupported_lines_count=0,
                conversion_level=0,
                metadata={
                    "error": str(e),
                    "lines_processed": len(code.split("\n"))
                }
            )

    def get_supported_pairs(self) -> list:
        """Get list of supported language pairs."""
        return [f"{s}→{t}" for s, t in self.converters.keys()]

    def detect_and_convert(
        self,
        code: str,
        target_language: str,
        strict_mode: bool = False
    ) -> Dict:
        """
        Detect source language and convert to target in one call.

        Args:
            code: Source code
            target_language: Target language
            strict_mode: If True, fail on unsupported constructs

        Returns:
            Dict with detection_result and conversion_result
        """
        detection = self.detector.detect(code)

        if detection.detected_language == "unknown":
            return {
                "detection": detection,
                "conversion": ConvertResponse(
                    converted_code="",
                    source_language="unknown",
                    target_language=target_language,
                    conversion_confidence=0.0,
                    warnings=["Could not detect source language"],
                    unsupported_constructs=[],
                    unsupported_lines_count=0,
                    conversion_level=0,
                    metadata={}
                )
            }

        conversion = self.convert(
            code,
            detection.detected_language,
            target_language,
            strict_mode=strict_mode
        )

        return {
            "detection": detection,
            "conversion": conversion
        }
