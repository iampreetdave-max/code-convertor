import re
from typing import Dict, List, Optional
from converters.base_converter import BaseConverter, ConversionLevel
from utils.indentation import IndentationTracker, ParsedLine
from converters.method_converter import get_method_converter


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
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"\bprint\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # Match print(...) with balanced parentheses
        match = re.search(r"\bprint\s*\(", line)
        if match:
            # Find the opening parenthesis
            start = match.end() - 1
            args = self._extract_balanced_parens(line, start)
            if args is not None:
                # Convert method calls in arguments first
                converted_args = self.method_converter.convert_python_to_javascript(args)
                if converted_args:
                    args = converted_args

                # Convert argument syntax
                args = self._convert_print_args(args)
                converted = f"{indent}console.log({args});"
                return {
                    "success": True,
                    "converted_line": converted,
                    "level": self.level
                }

        return {"success": False}

    def _extract_balanced_parens(self, text: str, start_pos: int) -> Optional[str]:
        """Extract content between balanced parentheses starting at start_pos."""
        if start_pos >= len(text) or text[start_pos] != '(':
            return None

        count = 0
        for i in range(start_pos, len(text)):
            if text[i] == '(':
                count += 1
            elif text[i] == ')':
                count -= 1
                if count == 0:
                    return text[start_pos + 1:i]
        return None

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
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*\w+\s*=\s*", line) is not None and "==" not in line

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*(\w+)\s*=\s*(.+)", line)
        if match:
            var_name = match.group(1)
            value = match.group(2).rstrip()

            # Remove trailing semicolon if present
            if value.endswith(";"):
                value = value[:-1].strip()

            # Convert method calls in the value
            converted_value = self.method_converter.convert_python_to_javascript(value)
            if converted_value:
                value = converted_value.rstrip()

            # Convert Python syntax to JavaScript
            value = self._convert_python_value(value)

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

    def _convert_python_value(self, value: str) -> str:
        """Convert Python value syntax to JavaScript."""
        # Boolean values
        value = re.sub(r"\bTrue\b", "true", value)
        value = re.sub(r"\bFalse\b", "false", value)
        # None
        value = re.sub(r"\bNone\b", "null", value)
        return value


class IfCondition(Rule):
    """Converts if statements."""

    def __init__(self):
        super().__init__("condition_if", ConversionLevel.LEVEL_2)
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*if\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        match = re.search(r"^\s*if\s+(.+):\s*$", line)
        if match:
            condition = match.group(1)
            # Convert method calls in condition first
            converted_condition = self.method_converter.convert_python_to_javascript(condition)
            if converted_condition:
                condition = converted_condition
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

        # Match: def name(args): with return type optional
        match = re.search(r"^\s*def\s+(\w+)\s*\((.*?)\)\s*(?:\s*->\s*[^:]+)?\s*:\s*$", line)
        if match:
            func_name = match.group(1)
            params = match.group(2)

            # Remove type hints from parameters - handles complex types
            # Use a more sophisticated approach that handles nested brackets
            params = self._remove_type_hints(params)

            converted = f"{indent}function {func_name}({params}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _remove_type_hints(self, params: str) -> str:
        """Remove type hints from function parameters, handling complex nested types."""
        result = []
        i = 0
        while i < len(params):
            if params[i] == ':':
                # Found a type hint - skip until comma or end
                bracket_depth = 0
                i += 1
                while i < len(params):
                    if params[i] == '[':
                        bracket_depth += 1
                    elif params[i] == ']':
                        bracket_depth -= 1
                    elif params[i] == ',' and bracket_depth == 0:
                        break
                    elif params[i] == ')' and bracket_depth == 0:
                        break
                    i += 1
                # Remove trailing whitespace from result
                while result and result[-1] in (' ', '\t'):
                    result.pop()
            else:
                result.append(params[i])
                i += 1
        return ''.join(result).strip()

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

        # except (ExceptionType1, ExceptionType2) as e: OR except ExceptionType | OtherType as e:
        match = re.search(r"^\s*except\s+[\(\[]?[\w|,\s]+[\)\]]?\s+as\s+(\w+)\s*:\s*$", line)
        if match:
            var_name = match.group(1)
            # In JS, catch receives error object
            # Note: indentation decrease logic adds closing brace
            converted = f"{indent}catch ({var_name}) {{"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # except (ExceptionType1, ExceptionType2): OR except Type1 | Type2:
        match = re.search(r"^\s*except\s+[\(\[]?[\w|,\s]+[\)\]]?\s*:\s*$", line)
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


class MethodCall(Rule):
    """Converts Python method calls to JavaScript."""

    def __init__(self):
        super().__init__("method_call", ConversionLevel.LEVEL_1)
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        """Check if line contains method calls."""
        # Simple heuristic: contains dot followed by identifier and parenthesis
        return re.search(r"\.\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("javascript")

        # Try to convert method calls
        converted = self.method_converter.convert_python_to_javascript(line)
        if converted:
            # Preserve indentation
            result_line = indent + converted.lstrip()
            return {
                "success": True,
                "converted_line": result_line,
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
            "method_call": [MethodCall()],
        }
