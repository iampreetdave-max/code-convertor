from typing import List


class ConfidenceCalculator:
    """Calculates conversion confidence scores using multiple factors."""

    def calculate(
        self,
        original_code: str,
        converted_code: str,
        lines_converted: int = 0,
        total_lines: int = 0,
        unsupported_count: int = 0,
    ) -> float:
        """
        Calculate overall conversion confidence (0.0 - 1.0).

        Factors:
        - Structure preservation (40%): Do line counts match reasonably?
        - Syntax validity (30%): Are braces balanced? Valid constructs?
        - Conversion completeness (30%): How many lines successfully converted?

        Args:
            original_code: Source code before conversion
            converted_code: Target code after conversion
            lines_converted: Number of successfully converted lines
            total_lines: Total number of lines to convert
            unsupported_count: Number of unsupported constructs found

        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        original_lines = [l for l in original_code.split("\n") if l.strip()]
        converted_lines = [l for l in converted_code.split("\n") if l.strip()]

        # Factor 1: Structure preservation (40%)
        structure_score = self._calculate_structure_score(original_lines, converted_lines)

        # Factor 2: Syntax validity (30%)
        syntax_score = self._calculate_syntax_score(converted_code)

        # Factor 3: Conversion completeness (30%)
        if total_lines > 0:
            completion_score = lines_converted / total_lines
        else:
            completion_score = 1.0 if unsupported_count == 0 else 0.5

        # Apply penalty for unsupported constructs
        unsupported_penalty = min(unsupported_count * 0.15, 0.5)

        confidence = (
            (structure_score * 0.4) + (syntax_score * 0.3) + (completion_score * 0.3)
        ) * (1.0 - unsupported_penalty)

        return max(0.0, min(confidence, 1.0))

    def _calculate_structure_score(self, original: List[str], converted: List[str]) -> float:
        """
        Score how well structure is preserved.
        - Similar line counts (good)
        - Similar nesting levels (good)
        """
        if not original:
            return 0.5

        line_ratio = len(converted) / len(original)
        line_penalty = abs(1.0 - line_ratio)

        # Allow some variance (JS often has more lines due to braces)
        # If ratio is between 0.7 and 1.5, score higher
        if 0.7 <= line_ratio <= 1.5:
            line_score = 0.95
        elif 0.5 <= line_ratio <= 2.0:
            line_score = 0.75
        else:
            line_score = 0.5

        return line_score

    def _calculate_syntax_score(self, code: str) -> float:
        """
        Score syntactic validity.
        - Balanced braces, brackets, parentheses
        - No obvious syntax errors
        """
        if not code.strip():
            return 0.0

        balanced = self._check_balanced_braces(code)
        semicolon_ratio = self._check_semicolon_consistency(code)

        return 0.7 if balanced else 0.5 + (semicolon_ratio * 0.2)

    def _check_balanced_braces(self, code: str) -> bool:
        """Check if braces, brackets, and parentheses are balanced."""
        stack = []
        pairs = {"(": ")", "[": "]", "{": "}"}

        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False

        return len(stack) == 0

    def _check_semicolon_consistency(self, code: str) -> float:
        """Check if semicolons are reasonably consistent (for JS)."""
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        if not lines:
            return 0.5

        with_semicolon = sum(1 for l in lines if l.endswith(";"))
        ratio = with_semicolon / len(lines)

        # JavaScript should mostly have semicolons (or be consistent)
        return 1.0 if 0.8 <= ratio <= 1.0 or ratio == 0.0 else 0.7
