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


class Comment(Rule):
    """Converts JavaScript comments to Python comments."""

    def __init__(self):
        super().__init__("comment", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*//", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        match = re.search(r"^\s*//(.*)$", line)
        if match:
            comment_text = match.group(1)
            converted = f"{indent}#{comment_text}"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}


class ConsoleLogStatement(Rule):
    """Converts console.log(...) to print(...)."""

    def __init__(self):
        super().__init__("console_log", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"\bconsole\.log\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # Match console.log(...) and extract arguments
        match = re.search(r"\bconsole\.log\s*\((.*?)\);?\s*$", line)
        if match:
            args = match.group(1)
            # Convert argument syntax
            args = self._convert_log_args(args)
            converted = f"{indent}print({args})"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_log_args(self, args: str) -> str:
        """Convert console.log() arguments to print format."""
        # Handle template literals: `text ${var}` → f"text {var}"
        def convert_template(match):
            content = match.group(1)
            # Replace ${var} with {var}
            converted = re.sub(r'\$\{(\w+)\}', r'{\1}', content)
            return 'f"' + converted + '"'

        args = re.sub(r'`([^`]*)`', convert_template, args)
        return args


class VariableDeclaration(Rule):
    """Converts variable declarations to Python assignments."""

    def __init__(self):
        super().__init__("variable", ConversionLevel.LEVEL_1)
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*(let|const|var)\s+\w+\s*=\s*", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        match = re.search(r"^\s*(let|const|var)\s+(\w+)\s*=\s*(.+?);?\s*$", line)
        if match:
            keyword = match.group(1)
            var_name = match.group(2)
            value = match.group(3).rstrip()

            # Remove semicolon if present
            if value.endswith(";"):
                value = value[:-1].strip()

            # Check if value is an arrow function: check for =>
            if "=>" in value:
                # Convert arrow function in value
                # Matches: x => ..., (x) => ..., (x, y) => ...
                arrow_match = re.search(r"(?:\(([^)]*)\)|(\w+))\s*=>\s*(.+)$", value)
                if arrow_match:
                    # Group 1: params in parentheses, Group 2: single param without parens
                    params = arrow_match.group(1) if arrow_match.group(1) else arrow_match.group(2)
                    body = arrow_match.group(3).strip()
                    # Only convert simple expressions (single parameter and simple body)
                    if "{" not in body and ";" not in body and "," not in params:
                        value = f"lambda {params}: {body}"
                        warnings.add_warning(
                            "Arrow functions converted to lambda. "
                            "Python lambdas are limited to single expressions; complex functions need manual conversion."
                        )
            else:
                # Convert method calls in the value
                converted_value = self.method_converter.convert_javascript_to_python(value)
                if converted_value:
                    value = converted_value.rstrip()
                else:
                    # Convert regular value syntax
                    value = self._convert_value(value)

            converted = f"{indent}{var_name} = {value}"
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_value(self, value: str) -> str:
        """Convert JavaScript values to Python."""
        value = value.replace("true", "True")
        value = value.replace("false", "False")
        value = value.replace("null", "None")
        return value


class IfStatement(Rule):
    """Converts if statements."""

    def __init__(self):
        super().__init__("condition_if", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*if\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        match = re.search(r"^\s*if\s*\((.+?)\)\s*\{\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            converted = f"{indent}if {condition}:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert JavaScript condition to Python."""
        condition = re.sub(r"\s*&&\s*", " and ", condition)
        condition = re.sub(r"\s*\|\|\s*", " or ", condition)
        condition = re.sub(r"!\s*", "not ", condition)
        condition = condition.replace("===", "==")
        condition = condition.replace("!==", "!=")
        condition = condition.replace("null", "None")
        condition = condition.replace("true", "True")
        condition = condition.replace("false", "False")
        return condition

    def creates_block(self) -> bool:
        return True


class ElseIfStatement(Rule):
    """Converts else if statements."""

    def __init__(self):
        super().__init__("condition_elif", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"else\s+if\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        match = re.search(r"else\s+if\s*\((.+?)\)\s*\{\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            converted = f"{indent}elif {condition}:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert JavaScript condition to Python."""
        condition = re.sub(r"\s*&&\s*", " and ", condition)
        condition = re.sub(r"\s*\|\|\s*", " or ", condition)
        condition = re.sub(r"!\s*", "not ", condition)
        condition = condition.replace("===", "==")
        condition = condition.replace("!==", "!=")
        condition = condition.replace("null", "None")
        condition = condition.replace("true", "True")
        condition = condition.replace("false", "False")
        return condition

    def creates_block(self) -> bool:
        return True


class ElseStatement(Rule):
    """Converts else statements."""

    def __init__(self):
        super().__init__("condition_else", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"else\s*\{\s*$", line) is not None and "else if" not in line

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("python")
        converted = f"{indent}else:"
        tracker.enter_block()
        return {
            "success": True,
            "converted_line": converted,
            "level": self.level
        }

    def creates_block(self) -> bool:
        return True


class FunctionDeclaration(Rule):
    """Converts function declarations."""

    def __init__(self):
        super().__init__("function_def", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*function\s+\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # Match: function name(params) {
        match = re.search(r"^\s*function\s+(\w+)\s*\((.*?)\)\s*\{\s*$", line)
        if match:
            func_name = match.group(1)
            params = match.group(2)

            converted = f"{indent}def {func_name}({params}):"
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
        return re.search(r"^\s*while\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        match = re.search(r"^\s*while\s*\((.+?)\)\s*\{\s*$", line)
        if match:
            condition = match.group(1)
            condition = self._convert_condition(condition)
            converted = f"{indent}while {condition}:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def _convert_condition(self, condition: str) -> str:
        """Convert JavaScript condition to Python."""
        condition = re.sub(r"\s*&&\s*", " and ", condition)
        condition = re.sub(r"\s*\|\|\s*", " or ", condition)
        condition = re.sub(r"!\s*", "not ", condition)
        condition = condition.replace("===", "==")
        condition = condition.replace("!==", "!=")
        condition = condition.replace("null", "None")
        condition = condition.replace("true", "True")
        condition = condition.replace("false", "False")
        return condition

    def creates_block(self) -> bool:
        return True


class TryBlock(Rule):
    """Converts try blocks."""

    def __init__(self):
        super().__init__("try", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*try\s*\{\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("python")
        converted = f"{indent}try:"
        tracker.enter_block()
        return {
            "success": True,
            "converted_line": converted,
            "level": self.level
        }

    def creates_block(self) -> bool:
        return True


class CatchBlock(Rule):
    """Converts catch blocks to except."""

    def __init__(self):
        super().__init__("except", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"catch\s*", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # catch (e) { or } catch (e) {
        match = re.search(r"catch\s*\(\s*(\w+)\s*\)\s*\{\s*$", line)
        if match:
            var_name = match.group(1)
            converted = f"{indent}except Exception as {var_name}:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # catch { or } catch {
        match = re.search(r"catch\s*\{\s*$", line)
        if match:
            converted = f"{indent}except Exception:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class ForLoop(Rule):
    """Converts for loops."""

    def __init__(self):
        super().__init__("loop_for", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*for\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # for (let i = 0; i < 5; i++) {
        range_match = re.search(
            r"^\s*for\s*\(\s*(?:let|var|const)\s+(\w+)\s*=\s*(\d+);\s*\1\s*<\s*(\d+);\s*\1\+\+\s*\)\s*\{\s*$",
            line
        )
        if range_match:
            var = range_match.group(1)
            start = range_match.group(2)
            end = range_match.group(3)
            if start == "0":
                converted = f"{indent}for {var} in range({end}):"
            else:
                converted = f"{indent}for {var} in range({start}, {end}):"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # for (let x of array) {
        of_match = re.search(r"^\s*for\s*\(\s*(?:let|var|const)\s+(\w+)\s+of\s+(.+?)\)\s*\{\s*$", line)
        if of_match:
            var = of_match.group(1)
            iterable = of_match.group(2).strip()
            converted = f"{indent}for {var} in {iterable}:"
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        # for (let key in obj) {
        in_match = re.search(r"^\s*for\s*\(\s*(?:let|var|const)\s+(\w+)\s+in\s+(.+?)\)\s*\{\s*$", line)
        if in_match:
            var = in_match.group(1)
            obj = in_match.group(2).strip()
            converted = f"{indent}for {var} in {obj}:"
            warnings.add_warning(
                "for-in loops converted to Python for loops. "
                "This may behave differently in Python - use .items() if needed."
            )
            tracker.enter_block()
            return {
                "success": True,
                "converted_line": converted,
                "level": self.level
            }

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class ArrowFunction(Rule):
    """Converts arrow functions to lambda."""

    def __init__(self):
        super().__init__("arrow_function", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"=>", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # Simple arrow: x => x * 2 or (x) => x * 2
        match = re.search(r"(\(?\w+\)?)\s*=>\s*(.+?)(?:;|$)", line)
        if match:
            params = match.group(1).strip()
            # Remove parentheses if present
            params = params.replace("(", "").replace(")", "")
            body = match.group(2).strip()

            # Only convert simple expressions (no multi-statement blocks)
            if "{" not in body and ";" not in body:
                result_line = line[:match.start()] + f"lambda {params}: {body}" + line[match.end():]
                warnings.add_warning(
                    "Arrow functions converted to lambda. "
                    "Python lambdas are limited to single expressions; complex functions need manual conversion."
                )
                return {
                    "success": True,
                    "converted_line": indent + result_line.strip(),
                    "level": self.level
                }

        return {"success": False}


class MethodCall(Rule):
    """Converts JavaScript method calls to Python."""

    def __init__(self):
        super().__init__("method_call", ConversionLevel.LEVEL_1)
        self.method_converter = get_method_converter()

    def matches(self, line: str) -> bool:
        """Check if line contains method calls."""
        # Simple heuristic: contains dot followed by identifier and parenthesis
        return re.search(r"\.\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("python")

        # Try to convert method calls
        converted = self.method_converter.convert_javascript_to_python(line)
        if converted:
            # Preserve indentation
            result_line = indent + converted.lstrip()
            return {
                "success": True,
                "converted_line": result_line,
                "level": self.level
            }

        return {"success": False}


class JavaScriptToPythonConverter(BaseConverter):
    """Converts JavaScript code to Python."""

    def __init__(self):
        super().__init__("javascript", "python")

    def _initialize_rules(self):
        """Initialize all conversion rules for JavaScript → Python."""
        self.rules = {
            "comment": [Comment()],
            "output": [ConsoleLogStatement()],
            "variable": [VariableDeclaration()],
            "condition_if": [IfStatement()],
            "condition_elif": [ElseIfStatement()],
            "condition_else": [ElseStatement()],
            "loop_for": [ForLoop()],
            "loop_while": [WhileLoop()],
            "function": [FunctionDeclaration()],
            "try": [TryBlock()],
            "except": [CatchBlock()],
            "arrow_function": [ArrowFunction()],
            "method_call": [MethodCall()],
        }

    def _convert_common_patterns(self, line: str) -> str:
        """Convert common JavaScript syntax patterns to Python."""
        # Must do === and !== BEFORE ! replacement to avoid double conversion
        line = re.sub(r"===", "==", line)
        line = re.sub(r"!==", "!=", line)
        line = re.sub(r"&&", "and", line)
        line = re.sub(r"\|\|", "or", line)
        # Convert ! to 'not ' only if not part of !==
        line = re.sub(r"!(?!=)", "not ", line)

        # Boolean values - more specific patterns
        line = re.sub(r"\btrue\b", "True", line)
        line = re.sub(r"\bfalse\b", "False", line)

        # null/None
        line = re.sub(r"\bnull\b", "None", line)

        return line
