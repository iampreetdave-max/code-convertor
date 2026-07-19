import os
from typing import Dict, List
from api.models import ConvertResponse
from core.language_detector import LanguageDetector
from converters.python_to_javascript import PythonToJavaScriptConverter
from converters.javascript_to_python import JavaScriptToPythonConverter
from converters.python_to_java import PythonToJavaConverter
from converters.llm_converter import LLMConverter


class ConversionEngine:
    """
    Orchestrates code conversion between supported languages.

    Strategy: prefer the LLM converter (idiomatic, correct output for ANY pair),
    and fall back to the fast rule-based converters when the LLM is unavailable
    (no API key / network error) for the three pairs that have one. This gives
    good output by default and still works offline for the core pairs.
    """

    # Languages offered as a source / target. HTML is source-only.
    SOURCE_LANGUAGES = ["python", "javascript", "typescript", "java", "html",
                        "cpp", "csharp", "go", "rust", "ruby", "php"]
    TARGET_LANGUAGES = ["python", "javascript", "typescript", "java",
                        "cpp", "csharp", "go", "rust", "ruby", "php"]

    def __init__(self):
        self.detector = LanguageDetector()
        # Offline fallbacks for the pairs that have a rule-based converter.
        self.rule_based: Dict[tuple, type] = {
            ("python", "javascript"): PythonToJavaScriptConverter,
            ("javascript", "python"): JavaScriptToPythonConverter,
            ("python", "java"): PythonToJavaConverter,
        }

    def _is_supported(self, source: str, target: str) -> bool:
        return (source in self.SOURCE_LANGUAGES
                and target in self.TARGET_LANGUAGES
                and source != target)

    def convert(
        self,
        code: str,
        source_language: str,
        target_language: str,
        strict_mode: bool = False,
    ) -> ConvertResponse:
        source = (source_language or "").lower()
        target = (target_language or "").lower()

        if not code.strip():
            return self._basic(code="", source=source, target=target,
                               confidence=1.0, warnings=["No code provided"])

        if source == target:
            return self._basic(code=code, source=source, target=target,
                               confidence=1.0,
                               warnings=["Source and target languages are the same"],
                               level=0)

        if not self._is_supported(source, target):
            raise ValueError(
                f"Conversion from {source_language} to {target_language} is not supported. "
                f"Sources: {', '.join(self.SOURCE_LANGUAGES)}. "
                f"Targets: {', '.join(self.TARGET_LANGUAGES)}."
            )

        # Was the LLM actually configured? (If no key, rule-based is the normal
        # path and shouldn't be flagged as a degraded fallback.)
        llm_attempted = bool(os.environ.get("GROQ_API_KEY"))

        # 1) Try the LLM (idiomatic output for any pair).
        llm_result = None
        try:
            llm_result = LLMConverter(source, target).convert(code)
        except Exception:
            llm_result = None  # network/import error -> try fallback below

        rule_cls = self.rule_based.get((source, target))
        llm_ok = (llm_result is not None
                  and llm_result.conversion_confidence > 0
                  and llm_result.converted_code.strip())

        if llm_ok:
            result = llm_result
        elif rule_cls is not None:
            result = rule_cls().convert(code)
            result.metadata["method"] = "rule-based"
            if llm_attempted:
                # LLM was configured but failed (rate-limit / error): downgrade
                # honestly and explain why (carry the sanitized reason).
                result.conversion_confidence = min(result.conversion_confidence, 0.5)
                reason = (" (" + llm_result.warnings[0] + ")") if (llm_result and llm_result.warnings) else ""
                result.warnings.insert(
                    0, "AI conversion unavailable - used the fast rule-based "
                       "converter; review the output." + reason)
        elif llm_result is not None:
            # No rule-based fallback: surface the LLM's fallback (carries the error).
            result = llm_result
        else:
            return self._basic(
                code=code, source=source, target=target, confidence=0.0, level=0,
                warnings=["Conversion failed and no fallback is available."])

        if strict_mode and result.unsupported_lines_count > 0:
            result.warnings.insert(
                0, f"STRICT MODE: Found {result.unsupported_lines_count} unsupported "
                   f"constructs. Review unsupported_constructs for details.")
        return result

    def get_supported_pairs(self) -> List[str]:
        """All offered pairs, as 'source -> target' strings (HTML is source-only)."""
        return [f"{s} -> {t}"
                for s in self.SOURCE_LANGUAGES
                for t in self.TARGET_LANGUAGES
                if s != t]

    def get_supported_languages(self) -> Dict[str, List[str]]:
        return {"sources": self.SOURCE_LANGUAGES, "targets": self.TARGET_LANGUAGES}

    def detect_and_convert(self, code: str, target_language: str,
                           strict_mode: bool = False) -> Dict:
        detection = self.detector.detect(code)
        if detection.detected_language == "unknown":
            return {
                "detection": detection,
                "conversion": self._basic(
                    code="", source="unknown", target=target_language,
                    confidence=0.0, level=0,
                    warnings=["Could not detect source language"]),
            }
        conversion = self.convert(code, detection.detected_language,
                                  target_language, strict_mode=strict_mode)
        return {"detection": detection, "conversion": conversion}

    # ----------------------------------------------------------------- helpers
    def _basic(self, code, source, target, confidence, warnings=None, level=1) -> ConvertResponse:
        return ConvertResponse(
            converted_code=code,
            source_language=source,
            target_language=target,
            conversion_confidence=confidence,
            warnings=warnings or [],
            unsupported_constructs=[],
            unsupported_lines_count=0,
            conversion_level=level,
            metadata={"lines_processed": len(code.split("\n")) if code else 0},
        )
