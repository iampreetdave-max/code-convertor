"""
Code Validator using Groq API.

Validates converted code and provides a quality score out of 10.
"""

import os
import re
import json
from typing import Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of code validation."""
    score: int  # 1-10
    is_valid: bool
    feedback: str
    issues: list[str]
    suggestions: list[str]
    compilation_check: str  # "PASS", "FAIL", or "UNKNOWN"


GROQ_VALIDATION_PROMPT = """You are a code quality validator. Analyze the following Java code that was converted from Python.

Rate the code quality from 1 to 10 based on:
1. **Correctness** (4 points): Would this code compile and run correctly?
2. **Idiomatic Java** (2 points): Does it follow Java conventions (camelCase, proper types, etc.)?
3. **Completeness** (2 points): Are all imports present? Is the class structure complete?
4. **Readability** (2 points): Is the code clean and well-structured?

Respond in this exact JSON format:
{{"score": <number 1-10>, "is_valid": <true/false>, "compilation_check": "<PASS/FAIL/UNKNOWN>", "feedback": "<2-3 sentence summary>", "issues": ["<issue 1>"], "suggestions": ["<suggestion 1>"]}}

JAVA CODE TO VALIDATE:
```java
{code}
```

ORIGINAL PYTHON CODE (for reference):
```python
{original_code}
```

Respond ONLY with the JSON, no other text."""


class CodeValidator:
    """Validates converted code using Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the validator.

        Args:
            api_key: Groq API key. If not provided, uses GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "groq package is required for validation. "
                    "Install it with: pip install groq"
                )
        return self._client

    def validate(
        self,
        converted_code: str,
        original_code: str,
        target_language: str = "java"
    ) -> ValidationResult:
        """
        Validate converted code using Groq API.

        Args:
            converted_code: The converted code to validate
            original_code: Original source code (for context)
            target_language: Target language (for validation rules)

        Returns:
            ValidationResult with score and feedback
        """
        if not self.api_key:
            return self._fallback_validation(converted_code, target_language)

        if not converted_code.strip():
            return ValidationResult(
                score=0,
                is_valid=False,
                feedback="No code provided for validation.",
                issues=["Empty code"],
                suggestions=["Provide valid code to validate"],
                compilation_check="FAIL"
            )

        try:
            prompt = GROQ_VALIDATION_PROMPT.format(
                code=converted_code,
                original_code=original_code
            )

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Fast and capable
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent scoring
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result_json = json.loads(result_text)

            return ValidationResult(
                score=min(10, max(1, int(result_json.get("score", 5)))),
                is_valid=result_json.get("is_valid", True),
                feedback=result_json.get("feedback", "Validation completed."),
                issues=result_json.get("issues", []),
                suggestions=result_json.get("suggestions", []),
                compilation_check=result_json.get("compilation_check", "UNKNOWN")
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                score=5,
                is_valid=True,
                feedback=f"Validation completed but response parsing failed: {str(e)}",
                issues=["Could not parse validation response"],
                suggestions=[],
                compilation_check="UNKNOWN"
            )
        except Exception as e:
            return self._fallback_validation(converted_code, target_language, error=str(e))

    def _fallback_validation(
        self,
        code: str,
        target_language: str,
        error: Optional[str] = None
    ) -> ValidationResult:
        """
        Basic validation without API (syntax checks only).
        """
        issues = []
        score = 10

        if target_language.lower() == "java":
            # Check for basic Java requirements
            if "class " not in code:
                issues.append("Missing class definition")
                score -= 2

            if "public static void main" not in code and "public class" in code:
                # It's okay if it's a utility class without main
                pass

            # Check balanced braces
            if code.count("{") != code.count("}"):
                issues.append("Unbalanced curly braces")
                score -= 3

            # Check for semicolons (basic check)
            lines = code.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("//") and not line.startswith("/*"):
                    if line.endswith(")") and not line.startswith("if") and not line.startswith("for") and not line.startswith("while"):
                        if "class " not in line and "interface " not in line:
                            issues.append(f"Line {i+1}: Possible missing semicolon")
                            score -= 0.5

            # Check for common Java imports
            if "ArrayList" in code and "import java.util" not in code:
                issues.append("Missing import for ArrayList")
                score -= 1

            if "HashMap" in code and "import java.util" not in code:
                issues.append("Missing import for HashMap")
                score -= 1

        score = max(1, min(10, int(score)))

        feedback = "Basic syntax validation completed."
        if error:
            feedback = f"API validation failed ({error}), performed basic syntax check."
        elif not self.api_key:
            feedback = "GROQ_API_KEY not set. Performed basic syntax validation only."

        return ValidationResult(
            score=score,
            is_valid=len(issues) == 0,
            feedback=feedback,
            issues=issues[:5],  # Limit to 5 issues
            suggestions=["Set GROQ_API_KEY for comprehensive AI-powered validation"],
            compilation_check="UNKNOWN"
        )
