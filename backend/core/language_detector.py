import re
import os
import json
from typing import Dict, Tuple, List
from api.models import DetectResponse


class LanguageDetector:
    """Enhanced language detection with confidence scoring. Uses Groq API when available."""

    def __init__(self):
        """Initialize detector with language-specific patterns and weights."""
        self._groq_client = None
        self._groq_available = False
        self._init_groq()
        self.patterns = {
            "python": {
                r"\bdef\s+\w+\s*\(": 1.0,  # def function_name(
                r"\bimport\s+": 0.8,
                r"\bfrom\s+.*\s+import\s+": 0.9,
                r"@\w+": 0.7,  # Decorators
                r"\bprint\s*\(": 0.6,
                r"\belif\s+": 0.95,  # Unique to Python
                r"__name__\s*==\s*['\"]__main__['\"]": 1.0,
                r":\s*$": 0.4,  # Lines ending with colon
                r"^\s{4,}": 0.3,  # Indentation (4+ spaces)
                r"\bclass\s+": 0.7,
                r"\blambda\s+": 0.8,
                r"\btry\s*:": 0.6,
                r"\bexcept\s+": 0.85,
                r"\bfinally\s*:": 0.7,
                r"\bwith\s+": 0.7,
                r"\bas\s+\w+:": 0.6,
                r"\bfor\s+\w+\s+in\s+": 0.9,
                r"\bwhile\s+": 0.6,
                r"\bpass\b": 0.9,
                r"\bNone\b": 0.4,
                r"\bTrue\b|\bFalse\b": 0.3,
            },
            "javascript": {
                r"console\.log\s*\(": 1.0,
                r"\bconst\s+": 0.95,
                r"\blet\s+": 0.95,
                r"\bvar\s+": 0.7,
                r"\bfunction\s+\w+\s*\(": 0.9,
                r"=>": 0.95,  # Arrow functions
                r"\basync\s+": 0.8,
                r"\bawait\s+": 0.8,
                r"\bimport\s+": 0.6,
                r"\bexport\s+": 0.8,
                r"\{.*\}": 0.2,  # Braces (low weight, too common)
                r"this\.": 0.7,
                r"\bnew\s+": 0.6,
                r"\bfunction\s*\*": 0.8,  # Generator
                r"\bclass\s+": 0.7,
                r"\bthrow\s+": 0.7,
                r"\bcatch\s*\(": 0.85,
                r"\bfinally\s*\{": 0.7,
                r"\btry\s*\{": 0.7,
                r"\.map\s*\(": 0.7,
                r"\.filter\s*\(": 0.7,
            },
            "java": {
                r"System\.out\.println\s*\(": 1.0,
                r"\bpublic\s+static\s+void\s+main": 1.0,
                r"\bpublic\s+class\s+": 0.95,
                r"\bprivate\s+": 0.8,
                r"\bprotected\s+": 0.8,
                r"\bnew\s+\w+\s*\(": 0.7,
                r"\bimport\s+java": 0.95,
                r"\bint\s+": 0.6,
                r"\bString\s+": 0.6,
                r"\btry\s*\{": 0.7,
                r"\bcatch\s*\(": 0.85,
                r"\bthrows\s+": 0.85,
                r"\bboolean\s+": 0.7,
                r"\bvoid\s+": 0.7,
                r"\bfor\s*\(": 0.5,
                r"\bwhile\s*\(": 0.3,
                r"@Override": 0.9,
                r"\binterface\s+": 0.8,
                r"\benum\s+": 0.8,
            }
        }

    def _init_groq(self):
        """Try to initialize Groq client for AI-powered detection."""
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=api_key)
                self._groq_available = True
            except ImportError:
                pass

    @staticmethod
    def _looks_like_html(code: str) -> bool:
        """Strong, low-false-positive HTML signals."""
        s = code.strip()
        if re.search(r"<!doctype\s+html|<html[\s>]|</html>|</body>|</head>", s, re.I):
            return True
        # Several distinct closing tags = markup, not a string containing '<'.
        tags = re.findall(
            r"</\s*(div|span|p|a|h[1-6]|section|header|footer|nav|ul|ol|li|table|tr|td|"
            r"form|button|label|style|script|title|main|article|aside)\s*>", s, re.I)
        return len(tags) >= 3

    def detect(self, code: str) -> DetectResponse:
        """
        Detect language using Groq API (preferred) or regex fallback.

        Args:
            code: Source code to analyze

        Returns:
            DetectResponse with language, confidence, reason, and alternatives
        """
        if not code.strip():
            return DetectResponse(
                detected_language="unknown",
                confidence=0.0,
                reason="No code provided",
                alternatives=[]
            )

        # HTML has no entry in the pattern table, so it used to be force-fit to
        # whatever scored least-badly (usually Java). Markup is unmistakable —
        # short-circuit on strong signals before any scoring or API call.
        if self._looks_like_html(code):
            return DetectResponse(
                detected_language="html",
                confidence=0.95,
                reason="HTML markup detected (doctype/tags)",
                alternatives=[]
            )

        # Try Groq AI detection first
        if self._groq_available:
            try:
                result = self._detect_with_groq(code)
                if result and result.detected_language != "unknown":
                    return result
            except Exception:
                pass

        # Fallback to regex-based detection
        return self._detect_with_regex(code)

    def _detect_with_groq(self, code: str) -> DetectResponse:
        """Detect language using Groq LLM API."""
        prompt = (
            "Detect the programming language of this code. "
            "Respond ONLY with JSON, no other text.\n"
            '{{"language": "<language_name>", "confidence": <0.0-1.0>, "reason": "<brief explanation>"}}\n\n'
            "Supported languages: python, javascript, java, typescript, cpp, csharp, go, rust, ruby, php\n"
            "Use lowercase for the language name.\n\n"
            f"Code:\n```\n{code[:2000]}\n```"
        )

        response = self._groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )

        result_text = response.choices[0].message.content.strip()

        # Handle potential markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        result_json = json.loads(result_text)
        lang = result_json.get("language", "unknown").lower().strip()
        conf = float(result_json.get("confidence", 0.5))
        reason = result_json.get("reason", "Detected by AI")

        # Validate the language is one we support
        supported = {"python", "javascript", "java", "typescript", "cpp", "csharp", "go", "rust", "ruby", "php"}
        if lang not in supported:
            return None

        # Get regex-based alternatives
        regex_result = self._detect_with_regex(code)
        alternatives = regex_result.alternatives

        return DetectResponse(
            detected_language=lang,
            confidence=min(max(conf, 0.0), 1.0),
            reason=f"[AI] {reason}",
            alternatives=alternatives
        )

    def _detect_with_regex(self, code: str) -> DetectResponse:
        """Detect language using regex pattern matching (fallback)."""
        scores = {}
        for lang, patterns in self.patterns.items():
            score = self._calculate_language_score(code, lang, patterns)
            scores[lang] = score

        # Sort by score
        sorted_langs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_lang, top_score = sorted_langs[0]

        # Normalize confidence (max possible score is roughly 15-20)
        confidence = min(top_score / 10.0, 1.0)

        # Return unknown only if no language has any matches
        if top_score == 0:
            top_lang = "unknown"
            confidence = 0.0
            reason = "Could not detect language - no matching patterns found"
        else:
            reason = self._generate_detection_reason(code, top_lang)

        # Build alternatives list
        alternatives = []
        for lang, score in sorted_langs[1:]:
            alt_confidence = min(score / 10.0, 1.0)
            if score > 0:
                alternatives.append((lang, alt_confidence))

        return DetectResponse(
            detected_language=top_lang,
            confidence=confidence,
            reason=reason,
            alternatives=alternatives
        )

    def _calculate_language_score(self, code: str, lang: str, patterns: Dict[str, float]) -> float:
        """
        Calculate language detection score based on pattern matches.

        Args:
            code: Source code
            lang: Language to score
            patterns: Pattern-weight pairs

        Returns:
            float: Total score for this language
        """
        score = 0.0
        for pattern, weight in patterns.items():
            # Use MULTILINE and IGNORECASE flags for better matching
            matches = len(re.findall(pattern, code, re.MULTILINE | re.IGNORECASE))
            if matches > 0:
                # Score increases with match count, but with diminishing returns
                score += weight * min(matches, 3)  # Cap at 3 matches per pattern

        return score

    def _generate_detection_reason(self, code: str, lang: str) -> str:
        """
        Generate human-readable explanation of detection.

        Args:
            code: Source code
            lang: Detected language

        Returns:
            str: Explanation string
        """
        patterns = self.patterns[lang]
        found_patterns = []

        for pattern, weight in patterns.items():
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                # Convert pattern to readable form
                readable = self._pattern_to_readable(pattern, lang)
                found_patterns.append(readable)

        if not found_patterns:
            return f"Detected as {lang} (low confidence)"

        # Show top patterns
        top_patterns = found_patterns[:4]
        return f"Found {lang} patterns: {', '.join(top_patterns)}"

    @staticmethod
    def _pattern_to_readable(pattern: str, lang: str) -> str:
        """Convert regex pattern to readable form."""
        # Simple conversions for common patterns
        conversions = {
            r"\bdef\s+\w+\s*\(": "function definition (def)",
            r"console\.log\s*\(": "console.log",
            r"\bconst\s+": "const declaration",
            r"=>": "arrow function",
            r"\bclass\s+": "class definition",
            r"\bimport\s+": "import statement",
            r"\bpublic\s+static\s+void\s+main": "main method",
            r"System\.out\.println\s*\(": "println statement",
        }

        if pattern in conversions:
            return conversions[pattern]

        # Generic fallback
        simplified = pattern.replace(r"\b", "").replace("\\s+", " ").replace("\\s*", "")
        return simplified[:30]  # Limit length
