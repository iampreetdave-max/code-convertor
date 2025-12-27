import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
from api.models import ConvertResponse
from utils.indentation import ParsedLine, IndentationTracker
from utils.confidence_calculator import ConfidenceCalculator
from utils.warning_generator import WarningGenerator


class ConversionLevel(Enum):
    """Conversion complexity levels."""
    LEVEL_1 = 1  # Simple string replacements
    LEVEL_2 = 2  # Structural (conditions, functions with blocks)
    LEVEL_3 = 3  # Complex (loops, comprehensions, transformations)


class BaseConverter(ABC):
    """Abstract base class for all language converters."""

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.current_level = ConversionLevel.LEVEL_1
        self.warnings = WarningGenerator()
        self.indentation_tracker = IndentationTracker(source_lang)
        self.confidence_calculator = ConfidenceCalculator()

        # Initialize rules (to be implemented by subclasses)
        self.rules: Dict[str, List] = {}

    @abstractmethod
    def _initialize_rules(self):
        """Initialize conversion rules for this language pair."""
        pass

    def convert(self, code: str) -> ConvertResponse:
        """
        Main conversion pipeline.

        Steps:
        1. Parse code into structured format
        2. Apply conversion rules
        3. Calculate confidence
        4. Generate warnings
        5. Return response

        Args:
            code: Source code to convert

        Returns:
            ConvertResponse with converted code and metadata
        """
        if not code.strip():
            return ConvertResponse(
                converted_code="",
                source_language=self.source_lang,
                target_language=self.target_lang,
                conversion_confidence=1.0,
                warnings=[],
                unsupported_constructs=[],
                unsupported_lines_count=0,
                conversion_level=1,
                metadata={"lines_processed": 0}
            )

        # Initialize rules
        self._initialize_rules()

        # Parse code
        lines = code.split("\n")
        parsed_lines = self._parse_code(lines)

        # Apply conversions
        converted_lines = self._apply_conversions(parsed_lines)

        # Generate output
        converted_code = "\n".join(converted_lines)

        # Calculate confidence
        conversion_confidence = self.confidence_calculator.calculate(
            original_code=code,
            converted_code=converted_code,
            lines_converted=len([l for l in converted_lines if l.strip()]),
            total_lines=len(parsed_lines),
            unsupported_count=len(self.warnings.unsupported_constructs)
        )

        # Get warnings
        warnings, unsupported_constructs = self.warnings.get_all()

        # Build metadata
        metadata = {
            "lines_processed": len(lines),
            "blocks_detected": self.indentation_tracker.block_count,
            "indentation_levels": self.indentation_tracker.max_indent_level,
            "constructs_found": self._count_constructs(parsed_lines)
        }

        return ConvertResponse(
            converted_code=converted_code,
            source_language=self.source_lang,
            target_language=self.target_lang,
            conversion_confidence=conversion_confidence,
            warnings=warnings,
            unsupported_constructs=unsupported_constructs,
            unsupported_lines_count=len([u for u in unsupported_constructs if u["type"] == "error"]),
            conversion_level=self.current_level.value,
            metadata=metadata
        )

    def _parse_code(self, lines: List[str]) -> List[ParsedLine]:
        """
        Parse code into structured format with metadata.

        Args:
            lines: List of code lines

        Returns:
            List of ParsedLine objects with metadata
        """
        parsed = []
        self.indentation_tracker.reset()

        for i, line in enumerate(lines, 1):
            # Get indentation level
            indent = self.indentation_tracker.get_indent_level(line)

            # Identify construct type
            construct = self._identify_construct(line)

            # Create parsed line object
            parsed_line = ParsedLine(
                original=line,
                line_num=i,
                indent_level=indent,
                construct_type=construct["type"],
                content=construct["content"],
                block_start=construct.get("block_start", False),
                block_level=self.indentation_tracker.current_block_level
            )

            parsed.append(parsed_line)

            # Track block changes
            if construct.get("block_start"):
                self.indentation_tracker.enter_block()
            elif construct.get("block_end"):
                self.indentation_tracker.exit_block()

        return parsed

    def _identify_construct(self, line: str) -> Dict:
        """
        Identify what construct this line contains.

        Args:
            line: Code line to analyze

        Returns:
            Dict with type, content, and block information
        """
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            return {"type": "comment", "content": stripped, "block_start": False}

        # Check each rule category
        for construct_type, rules in self.rules.items():
            for rule in rules:
                if hasattr(rule, "matches") and rule.matches(stripped):
                    return {
                        "type": construct_type,
                        "content": stripped,
                        "block_start": rule.creates_block() if hasattr(rule, "creates_block") else False
                    }

        return {"type": "statement", "content": stripped, "block_start": False}

    def _apply_conversions(self, parsed_lines: List[ParsedLine]) -> List[str]:
        """
        Apply conversion rules to all lines.

        Args:
            parsed_lines: List of parsed lines

        Returns:
            List of converted code lines
        """
        converted = []
        prev_indent = 0

        for parsed_line in parsed_lines:
            # Handle closing braces for indentation decrease
            if self.target_lang in ["javascript", "java"]:
                indent_decrease = max(0, prev_indent - parsed_line.indent_level)
                for _ in range(indent_decrease):
                    # Add closing brace from previous iteration
                    if converted:
                        # Insert brace on previous line if needed
                        pass

            if parsed_line.construct_type in self.rules:
                rules = self.rules[parsed_line.construct_type]
                converted_line = self._apply_rules(parsed_line, rules)
            else:
                converted_line = self._convert_generic_line(parsed_line)

            converted.append(converted_line)
            prev_indent = parsed_line.indent_level

        return converted

    def _apply_rules(self, parsed_line: ParsedLine, rules: List) -> str:
        """
        Try to apply applicable rules to a line.

        Args:
            parsed_line: Parsed line with metadata
            rules: List of rules to try

        Returns:
            Converted line string
        """
        for rule in rules:
            if hasattr(rule, "matches") and rule.matches(parsed_line.original):
                try:
                    result = rule.convert(parsed_line, self.indentation_tracker, self.warnings)
                    if result.get("success"):
                        new_level = result.get("level", ConversionLevel.LEVEL_1)
                        if new_level.value > self.current_level.value:
                            self.current_level = new_level
                        return result.get("converted_line", parsed_line.original)
                    else:
                        if result.get("warning"):
                            self.warnings.add_warning(result["warning"])
                except Exception as e:
                    self.warnings.add_unsupported_keyword(
                        parsed_line.line_num,
                        parsed_line.construct_type,
                        str(e)
                    )

        # Fallback: convert generic line
        return self._convert_generic_line(parsed_line)

    def _convert_generic_line(self, parsed_line: ParsedLine) -> str:
        """
        Convert lines that don't match specific constructs.

        Args:
            parsed_line: Parsed line with metadata

        Returns:
            Converted line string
        """
        indent = parsed_line.get_target_indent(self.target_lang)
        line = parsed_line.original.strip()

        if not line:
            return ""

        # Handle comments
        if line.startswith("#"):
            # Python comment to JavaScript comment
            if self.target_lang == "javascript":
                return indent + "//" + line[1:]
            return indent + line

        # Basic variable name conversions for common patterns
        line = self._convert_common_patterns(line)

        return indent + line

    def _convert_common_patterns(self, line: str) -> str:
        """
        Convert common syntax patterns.

        Args:
            line: Code line

        Returns:
            Converted line
        """
        # Boolean values
        line = line.replace(" True", " true")
        line = line.replace(" False", " false")
        line = line.replace("(True", "(true")
        line = line.replace("(False", "(false")

        # Logical operators
        line = re.sub(r"\band\b", "&&", line)
        line = re.sub(r"\bor\b", "||", line)
        line = re.sub(r"\bnot\b\s+", "!", line)

        # None to null
        line = line.replace("None", "null")

        # Equality operators
        line = line.replace("==", "===")

        return line

    def _count_constructs(self, parsed_lines: List[ParsedLine]) -> Dict[str, int]:
        """Count construct types found in code."""
        counts = {}
        for line in parsed_lines:
            if line.construct_type != "statement":
                counts[line.construct_type] = counts.get(line.construct_type, 0) + 1
        return counts
