import re
from typing import Dict, List, Optional
from converters.base_converter import BaseConverter, ConversionLevel
from utils.indentation import IndentationTracker, ParsedLine


class Rule:
    """Base class for conversion rules."""

    def __init__(self, name: str, level: ConversionLevel = ConversionLevel.LEVEL_1):
        self.name = name
        self.level = level

    def matches(self, line: str) -> bool:
        """Check if this rule applies."""
        return False

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        """Convert the line."""
        return {"success": False}

    def creates_block(self) -> bool:
        """Does this create a new block?"""
        return False


class PrintStatement(Rule):
    """Converts print(...) to console.log(...)."""

    def __init__(self):
        super().__init__("print_statement", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"\bprint\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # Match print(...) and extract arguments
        match = re.search(r"\bprint\s*\((.*?)\)", line)
        if match:
            args = match.group(1)
            # Convert argument syntax
            args = self._convert_print_args(args)
            converted = f"{indent}console.log({args});"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_print_args(self, args: str) -> str:
        """Convert print() arguments to console.log format."""
        # Handle f-strings: f"text {var}" → `text ${var}`
        def convert_fstring(match):
            content = match.group(1)
            # Replace {var} with ${var}
            converted = re.sub(r'\{(\w+)\}', r'${\1}', content)
            return "`" + converted + "`"

        args = re.sub(r'f["\']([^"\']*)["\']', convert_fstring, args)
        return args


class VariableDeclaration(Rule):
    """Converts variable assignments to let/const."""

    def __init__(self):
        super().__init__("variable", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*\w+\s*=\s*", line) is not None and "==" not in line

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*(\w+)\s*=\s*(.+)", line)
        if match:
            var_name = match.group(1)
            value = match.group(2).rstrip()

            # Determine if const or let
            if var_name.isupper():
                keyword = "const"
            else:
                keyword = "let"

            converted = f"{indent}{keyword} {var_name} = {value};"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}


class IfCondition(Rule):
    """Converts if statements."""

    def __init__(self):
        super().__init__("condition_if", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*if\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*if\s+(.+):\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            converted = f"{indent}if ({condition}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert Python condition to JavaScript."""
        condition = re.sub(r"\band\b", "&&", condition)
        condition = re.sub(r"\bor\b", "||", condition)
        condition = re.sub(r"\bnot\b\s+", "!", condition)
        condition = condition.replace("==", "===")
        condition = condition.replace("None", "null")
        condition = condition.replace("True", "true")
        condition = condition.replace("False", "false")
        return condition

    def creates_block(self) -> bool:
        return True


class ElifCondition(Rule):
    """Converts elif statements."""

    def __init__(self):
        super().__init__("condition_elif", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*elif\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*elif\s+(.+):\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            # Note: indentation decrease logic adds closing brace, so we only add "else if"
            converted = f"{indent}else if ({condition}) {{"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert Python condition to JavaScript."""
        condition = re.sub(r"\band\b", "&&", condition)
        condition = re.sub(r"\bor\b", "||", condition)
        condition = re.sub(r"\bnot\b\s+", "!", condition)
        condition = condition.replace("==", "===")
        condition = condition.replace("None", "null")
        condition = condition.replace("True", "true")
        condition = condition.replace("False", "false")
        return condition

    def creates_block(self) -> bool:
        return True


class ElseCondition(Rule):
    """Converts else statements."""

    def __init__(self):
        super().__init__("condition_else", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*else\s*:\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("javascript")
        # Note: indentation decrease logic adds closing brace, so we only add "else {"
        converted = f"{indent}else {{"
        tracker.enter_block()
        return {
            "success": True,
            "converted_line": converted,
            "level": self.level
        }

    def creates_block(self) -> bool:
        return True


class ForLoop(Rule):
    """Converts for loops."""

    def __init__(self):
        super().__init__("loop_for", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*for\s+\w+\s+in\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # for x in range(n):
        range_match = re.search(r"^\s*for\s+(\w+)\s+in\s+range\s*\(\s*(\d+)\s*\):", line)
        if range_match:
            var = range_match.group(1)
            end = range_match.group(2)
            converted = f"{indent}for (let {var} = 0; {var} < {end}; {var}++) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # for x in range(start, end):
        range_match = re.search(r"^\s*for\s+(\w+)\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\):", line)
        if range_match:
            var = range_match.group(1)
            start = range_match.group(2)
            end = range_match.group(3)
            converted = f"{indent}for (let {var} = {start}; {var} < {end}; {var}++) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # for x in list:
        list_match = re.search(r"^\s*for\s+(\w+)\s+in\s+(.+):", line)
        if list_match:
            var = list_match.group(1)
            iterable = list_match.group(2).strip()
            converted = f"{indent}for (let {var} of {iterable}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class WhileLoop(Rule):
    """Converts while loops."""

    def __init__(self):
        super().__init__("loop_while", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*while\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*while\s+(.+):\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            converted = f"{indent}while ({condition}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert Python condition to JavaScript."""
        condition = re.sub(r"\band\b", "&&", condition)
        condition = re.sub(r"\bor\b", "||", condition)
        condition = re.sub(r"\bnot\b\s+", "!", condition)
        condition = condition.replace("==", "===")
        condition = condition.replace("None", "null")
        condition = condition.replace("True", "true")
        condition = condition.replace("False", "false")
        return condition

    def creates_block(self) -> bool:
        return True


class FunctionDefinition(Rule):
    """Converts function definitions."""

    def __init__(self):
        super().__init__("function_def", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*def\s+\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # Match: def name(args):
        match = re.search(r"^\s*def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*[\w\[\],\s]+)?\s*:\s*$", line)
        if match:
            func_name = match.group(1)
            params = match.group(2)

            # Remove type hints from parameters if present
            params = re.sub(r":\s*[\w\[\],\s]+", "", params)

            converted = f"{indent}function {func_name}({params}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class TryExcept(Rule):
    """Converts try/except to try/catch."""

    def __init__(self):
        super().__init__("try_except", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*try\s*:\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("javascript")
        converted = f"{indent}try {{"
        tracker.enter_block()
        return {
            "success": True,
            "converted_line": converted,
            "level": self.level
        }

    def creates_block(self) -> bool:
        return True


class ExceptClause(Rule):
    """Converts except clause to catch."""

    def __init__(self):
        super().__init__("except_clause", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*except\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # except ExceptionType as e:
        match = re.search(r"^\s*except\s+(\w+)\s+as\s+(\w+)\s*:\s*$", line)
        if match:
            exc_type = match.group(1)
            var_name = match.group(2)
            # In JS, catch receives error object
            # Note: indentation decrease logic adds closing brace
            converted = f"{indent}catch ({var_name}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # except ExceptionType:
        match = re.search(r"^\s*except\s+(\w+)\s*:\s*$", line)
        if match:
            # Note: indentation decrease logic adds closing brace
            converted = f"{indent}catch (error) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # except:
        match = re.search(r"^\s*except\s*:\s*$", line)
        if match:
            # Note: indentation decrease logic adds closing brace
            converted = f"{indent}catch (error) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class ListComprehension(Rule):
    """Converts list comprehensions to array map/filter."""

    def __init__(self):
        super().__init__("list_comp", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"\[.+\s+for\s+\w+\s+in\s+.+\]", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # Simple list comprehension: [x*2 for x in list]
        match = re.search(r"\[(.+?)\s+for\s+(\w+)\s+in\s+(.+?)\]", line)
        if match:
            expr = match.group(1)
            var = match.group(2)
            iterable = match.group(3)

            # Convert to .map()
            converted = f"{iterable}.map({var} => {expr})"
            result_line = line.replace(match.group(0), converted)
            warnings.add_list_comprehension_warning(parsed_line.line_num, line)

            return {
                "success": True,
                "converted_line": indent + result_line.strip() + ";",
                "level": self.level
            }

        return {"success": False}


class PythonToJavaScriptConverter(BaseConverter):
    """Converts Python code to JavaScript."""

    def __init__(self):
        super().__init__("python", "javascript")

    def _initialize_rules(self):
        """Initialize all conversion rules for Python → JavaScript."""
        self.rules = {
            "output": [PrintStatement()],
            "variable": [VariableDeclaration()],
            "condition_if": [IfCondition()],
            "condition_elif": [ElifCondition()],
            "condition_else": [ElseCondition()],
            "loop_for": [ForLoop()],
            "loop_while": [WhileLoop()],
            "function": [FunctionDefinition()],
            "try": [TryExcept()],
            "except": [ExceptClause()],
            "list_comp": [ListComprehension()],
        }
