"""
Python to Java Converter

Converts Python code to Java using rule-based pattern matching.
Follows the same architecture as python_to_javascript.py:
- Rule classes that match and convert specific constructs
- BaseConverter handles the pipeline (parse → convert → output)

Key Java-specific challenges handled:
- Static typing (basic type inference from literals and usage)
- Class wrapping (standalone scripts get wrapped in public class Main)
- Semicolons on statements
- Access modifiers
- Import collection
- self → this translation
- Python idioms → Java idioms
"""

import re
from typing import Dict, List, Optional, Set
from converters.base_converter import BaseConverter, ConversionLevel
from utils.indentation import IndentationTracker, ParsedLine
from converters.java_method_converter import get_java_method_converter


# ---------------------------------------------------------------------------
# Type inference helpers
# ---------------------------------------------------------------------------

def infer_type_from_value(value: str) -> str:
    """
    Infer a Java type from a Python value expression.

    Returns a best-guess Java type string.
    """
    value = value.strip()

    # Boolean
    if value in ("True", "False", "true", "false"):
        return "boolean"

    # None / null
    if value in ("None", "null"):
        return "Object"

    # Integer literal (not float)
    if re.match(r'^-?\d+$', value):
        return "int"

    # Float literal
    if re.match(r'^-?\d+\.\d+$', value):
        return "double"

    # String literal
    if re.match(r'^["\']', value) or re.match(r'^f["\']', value):
        return "String"

    # List literal []
    if value.startswith('['):
        return "ArrayList<Object>"

    # Dict literal {}
    if value.startswith('{') and ':' in value:
        return "HashMap<String, Object>"

    # Set literal {} without colon
    if value.startswith('{') and ':' not in value and value != '{}':
        return "HashSet<Object>"

    # Tuple literal ()
    if value.startswith('(') and ',' in value:
        return "List<Object>"

    # Function call — try to guess return type
    if re.match(r'^int\s*\(', value):
        return "int"
    if re.match(r'^float\s*\(', value):
        return "double"
    if re.match(r'^str\s*\(', value):
        return "String"
    if re.match(r'^bool\s*\(', value):
        return "boolean"
    if re.match(r'^len\s*\(', value):
        return "int"
    if re.match(r'^input\s*\(', value):
        return "String"
    if re.match(r'^range\s*\(', value):
        return "int"

    # new ArrayList / HashMap etc from a previous conversion
    if "ArrayList" in value:
        return "ArrayList<Object>"
    if "HashMap" in value:
        return "HashMap<String, Object>"

    # Default — can't infer
    return "var"


def python_type_hint_to_java(hint: str) -> str:
    """Convert a Python type hint string to Java type."""
    hint = hint.strip()
    mapping = {
        "int": "int",
        "float": "double",
        "str": "String",
        "bool": "boolean",
        "None": "void",
        "list": "List<Object>",
        "dict": "Map<String, Object>",
        "set": "Set<Object>",
        "tuple": "List<Object>",
        "bytes": "byte[]",
        "any": "Object",
        "Any": "Object",
        "object": "Object",
        "Optional": "Object",
    }
    # Handle List[int], Dict[str, int], etc.
    generic_match = re.match(r'(\w+)\[(.+)\]', hint)
    if generic_match:
        outer = generic_match.group(1)
        inner = generic_match.group(2)
        if outer == "List":
            inner_java = python_type_hint_to_java(inner)
            # Primitives must be boxed in generics
            inner_java = _box_primitive(inner_java)
            return f"List<{inner_java}>"
        if outer == "Dict":
            parts = inner.split(",", 1)
            if len(parts) == 2:
                k = _box_primitive(python_type_hint_to_java(parts[0].strip()))
                v = _box_primitive(python_type_hint_to_java(parts[1].strip()))
                return f"Map<{k}, {v}>"
        if outer == "Set":
            inner_java = _box_primitive(python_type_hint_to_java(inner))
            return f"Set<{inner_java}>"
        if outer == "Optional":
            return python_type_hint_to_java(inner)
        if outer == "Tuple":
            return "List<Object>"

    return mapping.get(hint, hint)


def _box_primitive(t: str) -> str:
    """Box Java primitive type for use in generics."""
    box_map = {
        "int": "Integer",
        "double": "Double",
        "float": "Float",
        "boolean": "Boolean",
        "long": "Long",
        "char": "Character",
        "byte": "Byte",
        "short": "Short",
    }
    return box_map.get(t, t)


# ---------------------------------------------------------------------------
# Rule base class (same pattern as py→js)
# ---------------------------------------------------------------------------

class Rule:
    """Base class for conversion rules."""

    def __init__(self, name: str, level: ConversionLevel = ConversionLevel.LEVEL_1):
        self.name = name
        self.level = level

    def matches(self, line: str) -> bool:
        return False

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        return {"success": False}

    def creates_block(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Level 1 — Simple statement conversions
# ---------------------------------------------------------------------------

class PrintStatement(Rule):
    """print(...) → System.out.println(...)"""

    def __init__(self):
        super().__init__("print_statement", ConversionLevel.LEVEL_1)
        self.method_converter = get_java_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"\bprint\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"\bprint\s*\(", line)
        if match:
            start = match.end() - 1
            args = self._extract_balanced_parens(line, start)
            if args is not None:
                args = self._convert_print_args(args)
                converted = f"{indent}System.out.println({args});"
                return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def _extract_balanced_parens(self, text: str, start_pos: int) -> Optional[str]:
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
        # f-strings → String.format or concatenation
        def convert_fstring(match):
            content = match.group(1)
            # Find all {expr} placeholders
            placeholders = re.findall(r'\{([^}]+)\}', content)
            if placeholders:
                format_str = re.sub(r'\{[^}]+\}', '%s', content)
                args_str = ", ".join(placeholders)
                return f'String.format("{format_str}", {args_str})'
            return f'"{content}"'

        args = re.sub(r'f["\']([^"\']*)["\']', convert_fstring, args)

        # Convert Python booleans/None in arguments
        args = re.sub(r'\bTrue\b', 'true', args)
        args = re.sub(r'\bFalse\b', 'false', args)
        args = re.sub(r'\bNone\b', 'null', args)

        return args


class VariableDeclaration(Rule):
    """x = value → Type x = value;"""

    def __init__(self):
        super().__init__("variable", ConversionLevel.LEVEL_1)
        self.method_converter = get_java_method_converter()

    def matches(self, line: str) -> bool:
        stripped = line.strip()
        # Match simple assignment or self.x assignment, not ==, not augmented
        if re.search(r"^\s*(?:self\.)?\w+\s*=\s*", stripped) and "==" not in stripped:
            if not re.search(r"^\s*(?:self\.)?\w+\s*[+\-*/|&^%]=", stripped):
                return True
        return False

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # Match: self.var_name = value  (instance attribute)
        self_match = re.search(r"^\s*self\.(\w+)\s*=\s*(.+)", line)
        if self_match:
            var_name = self_match.group(1)
            value = self_match.group(2).rstrip().rstrip(";")
            value = self._convert_value(value)
            value = re.sub(r"\bself\.", "this.", value)
            converted_value = self.method_converter.convert_line(value)
            if converted_value:
                value = converted_value
            converted = f"{indent}this.{var_name} = {value};"
            return {"success": True, "converted_line": converted, "level": self.level}

        # Match: var_name = value
        match = re.search(r"^\s*(\w+)\s*=\s*(.+)", line)
        if match:
            var_name = match.group(1)
            value = match.group(2).rstrip().rstrip(";")

            # Skip Python keywords that look like assignments
            if var_name in ("if", "else", "elif", "for", "while", "def", "class",
                            "return", "import", "from", "try", "except", "finally",
                            "with", "as", "pass", "break", "continue", "raise",
                            "yield", "lambda", "global", "nonlocal", "assert", "del"):
                return {"success": False}

            # Convert the value
            value = self._convert_value(value)

            # self. → this. in value
            value = re.sub(r"\bself\.", "this.", value)

            # Convert method calls in value
            converted_value = self.method_converter.convert_line(value)
            if converted_value:
                value = converted_value

            # Infer type
            java_type = infer_type_from_value(value)

            # Convert constants (ALL_CAPS) to final
            if var_name.isupper() and "_" in var_name or var_name.isupper():
                converted = f"{indent}static final {java_type} {var_name} = {value};"
            else:
                converted = f"{indent}{java_type} {var_name} = {value};"

            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def _convert_value(self, value: str) -> str:
        """Convert Python value syntax to Java."""
        # Booleans
        value = re.sub(r"\bTrue\b", "true", value)
        value = re.sub(r"\bFalse\b", "false", value)
        value = re.sub(r"\bNone\b", "null", value)

        # f-strings → String.format
        def convert_fstring(match):
            content = match.group(1)
            placeholders = re.findall(r'\{([^}]+)\}', content)
            if placeholders:
                format_str = re.sub(r'\{[^}]+\}', '%s', content)
                args_str = ", ".join(placeholders)
                return f'String.format("{format_str}", {args_str})'
            return f'"{content}"'
        value = re.sub(r'f["\']([^"\']*)["\']', convert_fstring, value)

        # ** power operator → Math.pow
        value = re.sub(r'(\w+)\s*\*\*\s*(\w+)', r'Math.pow(\1, \2)', value)

        # // floor division → Math.floorDiv
        value = re.sub(r'(\w+)\s*//\s*(\w+)', r'Math.floorDiv(\1, \2)', value)

        # List literal [] → new ArrayList<>(Arrays.asList(...))
        list_match = re.match(r'^\[(.+)\]$', value)
        if list_match and 'for' not in value:
            items = list_match.group(1)
            return f'new ArrayList<>(Arrays.asList({items}))'

        # Empty list
        if value == '[]':
            return 'new ArrayList<>()'

        # Empty dict
        if value == '{}':
            return 'new HashMap<>()'

        # Dict literal {k: v, ...} → basic Map.of() for small dicts
        dict_match = re.match(r'^\{(.+)\}$', value)
        if dict_match and ':' in value and 'for' not in value:
            content = dict_match.group(1)
            # Convert k: v pairs to k, v
            pairs = re.sub(r'([^,{]+)\s*:\s*([^,}]+)', r'\1, \2', content)
            return f'new HashMap<>(Map.of({pairs}))'

        # Lambda → inline comment (no direct Java lambda from Python lambda in assignment)
        lambda_match = re.match(r'^lambda\s+([^:]+):\s*(.+)$', value)
        if lambda_match:
            params = lambda_match.group(1).strip()
            body = lambda_match.group(2).strip()
            # Wrap in a functional interface style
            return f'({params}) -> {body}'

        # len(x) → x.size()
        def convert_len(match):
            arg = match.group(1).strip()
            return f"{arg}.size()"
        value = re.sub(r'\blen\s*\(\s*([^)]+)\s*\)', convert_len, value)

        return value


class AugmentedAssignment(Rule):
    """x += 1 → x += 1; (just add semicolon and convert values)"""

    def __init__(self):
        super().__init__("augmented_assign", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*\w+\s*[+\-*/|&^%]=\s*", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")

        # Convert values
        line = re.sub(r"\bTrue\b", "true", line)
        line = re.sub(r"\bFalse\b", "false", line)
        line = re.sub(r"\bNone\b", "null", line)
        line = re.sub(r"\bself\.", "this.", line)

        converted = f"{indent}{line};"
        return {"success": True, "converted_line": converted, "level": self.level}


class ReturnStatement(Rule):
    """return value → return value;"""

    def __init__(self):
        super().__init__("return_stmt", ConversionLevel.LEVEL_1)
        self.method_converter = get_java_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*return\b", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"^\s*return\s*(.*)?$", line)
        if match:
            value = (match.group(1) or "").strip()

            if value:
                # Convert Python values
                value = re.sub(r"\bTrue\b", "true", value)
                value = re.sub(r"\bFalse\b", "false", value)
                value = re.sub(r"\bNone\b", "null", value)
                value = re.sub(r"\bself\.", "this.", value)

                # Convert method calls
                converted_value = self.method_converter.convert_line(value)
                if converted_value:
                    value = converted_value

                # Multiple return values → not directly supported
                if ',' in value and not re.search(r'[\(\[\{]', value):
                    warnings.add_warning(
                        f"Line {parsed_line.line_num}: Multiple return values not supported in Java. "
                        f"Consider returning an array or custom object."
                    )

                converted = f"{indent}return {value};"
            else:
                converted = f"{indent}return;"

            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}


class ImportStatement(Rule):
    """import x / from x import y → // import handled (Java imports added at top)"""

    def __init__(self):
        super().__init__("import_stmt", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*(import|from)\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")

        warnings.add_warning(
            f"Line {parsed_line.line_num}: Python import '{line}' removed. "
            f"Add equivalent Java import manually if needed."
        )
        converted = f"{indent}// {line}  // TODO: Add Java equivalent import"
        return {"success": True, "converted_line": converted, "level": self.level}


class PassStatement(Rule):
    """pass → // pass"""

    def __init__(self):
        super().__init__("pass_stmt", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*pass\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("java")
        return {"success": True, "converted_line": f"{indent}// pass", "level": self.level}


class BreakContinue(Rule):
    """break/continue → break;/continue;"""

    def __init__(self):
        super().__init__("break_continue", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*(break|continue)\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")
        return {"success": True, "converted_line": f"{indent}{line};", "level": self.level}


class RaiseStatement(Rule):
    """raise ValueError('msg') → throw new IllegalArgumentException('msg');"""

    def __init__(self):
        super().__init__("raise_stmt", ConversionLevel.LEVEL_1)
        self.exception_map = {
            "ValueError": "IllegalArgumentException",
            "TypeError": "ClassCastException",
            "KeyError": "NoSuchElementException",
            "IndexError": "IndexOutOfBoundsException",
            "FileNotFoundError": "FileNotFoundException",
            "IOError": "IOException",
            "OSError": "IOException",
            "ZeroDivisionError": "ArithmeticException",
            "NotImplementedError": "UnsupportedOperationException",
            "RuntimeError": "RuntimeException",
            "AttributeError": "UnsupportedOperationException",
            "StopIteration": "NoSuchElementException",
            "OverflowError": "ArithmeticException",
            "Exception": "Exception",
        }

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*raise\b", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")

        # raise ExceptionType("message")
        match = re.search(r'raise\s+(\w+)\s*\(\s*(.*)\s*\)', line)
        if match:
            exc_type = match.group(1)
            exc_args = match.group(2)
            java_exc = self.exception_map.get(exc_type, exc_type)
            converted = f"{indent}throw new {java_exc}({exc_args});"
            return {"success": True, "converted_line": converted, "level": self.level}

        # raise (re-raise)
        if re.search(r'^\s*raise\s*$', line):
            converted = f"{indent}throw e;"
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}


class AssertStatement(Rule):
    """assert condition, msg → assert condition : msg;"""

    def __init__(self):
        super().__init__("assert_stmt", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*assert\b", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")

        # assert condition, message
        match = re.search(r'assert\s+(.+?),\s*(.+)', line)
        if match:
            condition = self._convert_condition(match.group(1))
            message = match.group(2)
            converted = f'{indent}assert {condition} : {message};'
            return {"success": True, "converted_line": converted, "level": self.level}

        # assert condition
        match = re.search(r'assert\s+(.+)', line)
        if match:
            condition = self._convert_condition(match.group(1))
            converted = f'{indent}assert {condition};'
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def _convert_condition(self, cond: str) -> str:
        cond = re.sub(r"\band\b", "&&", cond)
        cond = re.sub(r"\bor\b", "||", cond)
        cond = re.sub(r"\bnot\b\s+", "!", cond)
        cond = cond.replace("True", "true").replace("False", "false").replace("None", "null")
        cond = re.sub(r'\bis\s+None\b', '== null', cond)
        cond = re.sub(r'\bis\s+not\s+None\b', '!= null', cond)
        return cond


# ---------------------------------------------------------------------------
# Level 2 — Structural conversions (conditions, functions, try/catch)
# ---------------------------------------------------------------------------

class IfCondition(Rule):
    """if condition: → if (condition) {"""

    def __init__(self):
        super().__init__("condition_if", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*if\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"^\s*if\s+(.+):\s*$", line)
        if match:
            condition = self._convert_condition(match.group(1))
            converted = f"{indent}if ({condition}) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def _convert_condition(self, cond: str) -> str:
        cond = re.sub(r"\bis\s+not\s+None\b", "!= null", cond)
        cond = re.sub(r"\bis\s+None\b", "== null", cond)
        cond = re.sub(r"\bNone\b", "null", cond)
        cond = re.sub(r"\band\b", "&&", cond)
        cond = re.sub(r"\bor\b", "||", cond)
        cond = re.sub(r"\bnot\b\s+", "!", cond)
        cond = cond.replace("True", "true").replace("False", "false")

        # len(x) → x.size()
        cond = re.sub(r'\blen\s*\(\s*([^)]+)\s*\)', r'\1.size()', cond)

        # x in list → list.contains(x)
        cond = re.sub(r'(\w+)\s+in\s+(\w+)', r'\2.contains(\1)', cond)
        cond = re.sub(r'(\w+)\s+not\s+in\s+(\w+)', r'!\2.contains(\1)', cond)

        # == for strings should ideally be .equals() but we can't always know
        # Leave == as is; add warning if comparing string literals
        if '==' in cond and ('"' in cond or "'" in cond):
            cond = cond.replace("==", ".equals(")
            # This is a rough heuristic — not perfect but catches common patterns

        return cond

    def creates_block(self) -> bool:
        return True


class ElifCondition(Rule):
    """elif condition: → } else if (condition) {"""

    def __init__(self):
        super().__init__("condition_elif", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*elif\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"^\s*elif\s+(.+):\s*$", line)
        if match:
            condition = IfCondition()._convert_condition(match.group(1))
            converted = f"{indent}else if ({condition}) {{"
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class ElseCondition(Rule):
    """else: → } else {"""

    def __init__(self):
        super().__init__("condition_else", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*else\s*:\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("java")
        converted = f"{indent}else {{"
        tracker.enter_block()
        return {"success": True, "converted_line": converted, "level": self.level}

    def creates_block(self) -> bool:
        return True


class FunctionDefinition(Rule):
    """def func(args): → public static returnType func(args) {"""

    def __init__(self):
        super().__init__("function_def", ConversionLevel.LEVEL_2)
        self._is_inside_class = False

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*def\s+\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"^\s*def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*([^:]+))?\s*:\s*$", line)
        if match:
            func_name = match.group(1)
            params_str = match.group(2)
            return_hint = match.group(3)

            # Determine return type
            if return_hint:
                return_type = python_type_hint_to_java(return_hint.strip())
            else:
                return_type = "void"  # Default, could be improved with body analysis

            # Check if this is __init__ (constructor)
            if func_name == "__init__":
                params = self._convert_params(params_str, skip_self=True)
                # Constructor — use class name (will be fixed by class wrapper)
                converted = f"{indent}public Main({params}) {{"
                tracker.enter_block()
                return {"success": True, "converted_line": converted, "level": self.level}

            # Check if this is a dunder method
            dunder = self._convert_dunder(func_name, params_str, return_hint, indent)
            if dunder:
                tracker.enter_block()
                return {"success": True, "converted_line": dunder, "level": self.level}

            # Check for self parameter (instance method)
            has_self = params_str.strip().startswith("self")
            if has_self:
                params = self._convert_params(params_str, skip_self=True)
                modifier = "public"
            else:
                params = self._convert_params(params_str, skip_self=False)
                modifier = "public static"

            # Check for @staticmethod / @classmethod (detected by no self)
            converted = f"{indent}{modifier} {return_type} {func_name}({params}) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def _convert_params(self, params_str: str, skip_self: bool = False) -> str:
        """Convert Python function parameters to Java typed parameters."""
        if not params_str.strip():
            return ""

        params = []
        raw_params = self._split_params(params_str)

        for p in raw_params:
            p = p.strip()
            if not p:
                continue
            if skip_self and p in ("self", "cls"):
                skip_self = False  # Only skip the first one
                continue

            # Handle type hints: param: Type
            hint_match = re.match(r'(\w+)\s*:\s*(.+?)(?:\s*=\s*(.+))?$', p)
            if hint_match:
                name = hint_match.group(1)
                type_hint = hint_match.group(2).strip()
                default = hint_match.group(3)
                java_type = python_type_hint_to_java(type_hint)
                params.append(f"{java_type} {name}")
            else:
                # No type hint — check for default value
                default_match = re.match(r'(\w+)\s*=\s*(.+)', p)
                if default_match:
                    name = default_match.group(1)
                    default_val = default_match.group(2).strip()
                    java_type = infer_type_from_value(default_val)
                    params.append(f"{java_type} {name}")
                elif p == "*args":
                    params.append("Object... args")
                elif p == "**kwargs":
                    params.append("Map<String, Object> kwargs")
                else:
                    # Completely untyped — use Object
                    params.append(f"Object {p}")

        return ", ".join(params)

    def _split_params(self, params_str: str) -> List[str]:
        """Split parameters respecting brackets."""
        result = []
        depth = 0
        current = ""
        for c in params_str:
            if c in "([{":
                depth += 1
                current += c
            elif c in ")]}":
                depth -= 1
                current += c
            elif c == "," and depth == 0:
                result.append(current)
                current = ""
            else:
                current += c
        if current.strip():
            result.append(current)
        return result

    def _convert_dunder(self, name: str, params: str, return_hint, indent: str) -> Optional[str]:
        """Convert Python dunder methods to Java equivalents."""
        dunder_map = {
            "__str__": ("public String toString", ""),
            "__repr__": ("public String toString", ""),
            "__len__": ("public int size", ""),
            "__eq__": ("public boolean equals", "Object obj"),
            "__hash__": ("public int hashCode", ""),
            "__lt__": ("public int compareTo", "Object other"),
            "__contains__": ("public boolean contains", "Object item"),
            "__iter__": ("public Iterator iterator", ""),
            "__enter__": ("public void open", ""),
            "__exit__": ("public void close", ""),
        }
        if name in dunder_map:
            signature, override_params = dunder_map[name]
            if not override_params:
                override_params = self._convert_params(params, skip_self=True)
            return f"{indent}@Override\n{indent}{signature}({override_params}) {{"
        return None

    def creates_block(self) -> bool:
        return True


class ClassDefinition(Rule):
    """class MyClass(Parent): → public class MyClass extends Parent {"""

    def __init__(self):
        super().__init__("class_def", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*class\s+\w+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # class Name(Parent1, Parent2):
        match = re.search(r"^\s*class\s+(\w+)\s*\(([^)]*)\)\s*:\s*$", line)
        if match:
            class_name = match.group(1)
            parents = match.group(2).strip()
            parent_list = [p.strip() for p in parents.split(",") if p.strip()]

            extends = ""
            implements = ""
            if parent_list:
                # First parent = extends, rest could be interfaces
                if parent_list[0] not in ("object", "ABC"):
                    extends = f" extends {parent_list[0]}"
                if len(parent_list) > 1:
                    ifaces = [p for p in parent_list[1:] if p not in ("object", "ABC")]
                    if ifaces:
                        implements = f" implements {', '.join(ifaces)}"

            converted = f"{indent}public class {class_name}{extends}{implements} {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # class Name:
        match = re.search(r"^\s*class\s+(\w+)\s*:\s*$", line)
        if match:
            class_name = match.group(1)
            converted = f"{indent}public class {class_name} {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class TryExcept(Rule):
    """try: → try {"""

    def __init__(self):
        super().__init__("try_except", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*try\s*:\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("java")
        tracker.enter_block()
        return {"success": True, "converted_line": f"{indent}try {{", "level": self.level}

    def creates_block(self) -> bool:
        return True


class ExceptClause(Rule):
    """except ExcType as e: → catch (ExcType e) {"""

    EXCEPTION_MAP = {
        "ValueError": "IllegalArgumentException",
        "TypeError": "ClassCastException",
        "KeyError": "NoSuchElementException",
        "IndexError": "IndexOutOfBoundsException",
        "FileNotFoundError": "FileNotFoundException",
        "IOError": "IOException",
        "OSError": "IOException",
        "ZeroDivisionError": "ArithmeticException",
        "NotImplementedError": "UnsupportedOperationException",
        "RuntimeError": "RuntimeException",
        "AttributeError": "UnsupportedOperationException",
        "StopIteration": "NoSuchElementException",
        "OverflowError": "ArithmeticException",
        "Exception": "Exception",
    }

    def __init__(self):
        super().__init__("except_clause", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*except\s*", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # except ExcType as e:
        match = re.search(r"^\s*except\s+(\w+)\s+as\s+(\w+)\s*:\s*$", line)
        if match:
            exc = self.EXCEPTION_MAP.get(match.group(1), match.group(1))
            var = match.group(2)
            tracker.enter_block()
            return {"success": True, "converted_line": f"{indent}catch ({exc} {var}) {{", "level": self.level}

        # except ExcType:
        match = re.search(r"^\s*except\s+(\w+)\s*:\s*$", line)
        if match:
            exc = self.EXCEPTION_MAP.get(match.group(1), match.group(1))
            tracker.enter_block()
            return {"success": True, "converted_line": f"{indent}catch ({exc} e) {{", "level": self.level}

        # except:
        match = re.search(r"^\s*except\s*:\s*$", line)
        if match:
            tracker.enter_block()
            return {"success": True, "converted_line": f"{indent}catch (Exception e) {{", "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class FinallyClause(Rule):
    """finally: → finally {"""

    def __init__(self):
        super().__init__("finally_clause", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*finally\s*:\s*$", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        indent = parsed_line.get_target_indent("java")
        tracker.enter_block()
        return {"success": True, "converted_line": f"{indent}finally {{", "level": self.level}

    def creates_block(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Level 3 — Complex conversions (loops, comprehensions, with, decorators)
# ---------------------------------------------------------------------------

class ForLoop(Rule):
    """for x in iterable: → for (Type x : iterable) { / for (int x = 0; ...) {"""

    def __init__(self):
        super().__init__("loop_for", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        # Match both "for x in" and "for x, y in" patterns
        return re.search(r"^\s*for\s+\w+\s*,?\s*\w*\s+in\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # for k, v in dict.items(): — MUST be before generic for x in y
        match = re.search(r"^\s*for\s+(\w+)\s*,\s*(\w+)\s+in\s+(\w+)\.items\s*\(\s*\)\s*:", line)
        if match:
            key, val, dict_name = match.group(1), match.group(2), match.group(3)
            converted = (
                f"{indent}for (var entry : {dict_name}.entrySet()) {{\n"
                f"{indent}  var {key} = entry.getKey();\n"
                f"{indent}  var {val} = entry.getValue();"
            )
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # for i, x in enumerate(list):
        match = re.search(r"^\s*for\s+(\w+)\s*,\s*(\w+)\s+in\s+enumerate\s*\(\s*(\w+)\s*\)\s*:", line)
        if match:
            idx, val, lst = match.group(1), match.group(2), match.group(3)
            converted = (
                f"{indent}for (int {idx} = 0; {idx} < {lst}.size(); {idx}++) {{\n"
                f"{indent}  var {val} = {lst}.get({idx});"
            )
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # for x in range(n): — single arg, can be variable or literal
        match = re.search(r"^\s*for\s+(\w+)\s+in\s+range\s*\(\s*([^,)]+)\s*\)\s*:", line)
        if match and ',' not in match.group(2):
            var, end = match.group(1), match.group(2).strip()
            converted = f"{indent}for (int {var} = 0; {var} < {end}; {var}++) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # for x in range(start, end):
        match = re.search(r"^\s*for\s+(\w+)\s+in\s+range\s*\(\s*([^,)]+)\s*,\s*([^,)]+)\s*\)\s*:", line)
        if match:
            var = match.group(1)
            start = match.group(2).strip()
            end = match.group(3).strip()
            converted = f"{indent}for (int {var} = {start}; {var} < {end}; {var}++) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # for x in range(start, end, step):
        match = re.search(r"^\s*for\s+(\w+)\s+in\s+range\s*\(\s*([^,)]+)\s*,\s*([^,)]+)\s*,\s*([^,)]+)\s*\)\s*:", line)
        if match:
            var = match.group(1)
            start = match.group(2).strip()
            end = match.group(3).strip()
            step = match.group(4).strip()
            converted = f"{indent}for (int {var} = {start}; {var} < {end}; {var} += {step}) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # for x in iterable:
        match = re.search(r"^\s*for\s+(\w+)\s+in\s+(.+):\s*$", line)
        if match:
            var = match.group(1)
            iterable = match.group(2).strip()
            converted = f"{indent}for (var {var} : {iterable}) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class WhileLoop(Rule):
    """while condition: → while (condition) {"""

    def __init__(self):
        super().__init__("loop_while", ConversionLevel.LEVEL_2)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*while\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        match = re.search(r"^\s*while\s+(.+):\s*$", line)
        if match:
            condition = IfCondition()._convert_condition(match.group(1))
            converted = f"{indent}while ({condition}) {{"
            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class ListComprehension(Rule):
    """[expr for x in list] → list.stream().map(x -> expr).collect(Collectors.toList())"""

    def __init__(self):
        super().__init__("list_comp", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"\[.+\s+for\s+\w+\s+in\s+.+\]", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # [expr for x in list if cond]
        match = re.search(r"\[(.+?)\s+for\s+(\w+)\s+in\s+(.+?)\s+if\s+(.+?)\]", line)
        if match:
            expr, var, iterable, cond = match.group(1), match.group(2), match.group(3), match.group(4)
            stream = f"{iterable}.stream().filter({var} -> {cond}).map({var} -> {expr}).collect(Collectors.toList())"
            result_line = line.replace(match.group(0), stream)
            warnings.add_list_comprehension_warning(parsed_line.line_num, line)
            return {"success": True, "converted_line": indent + result_line.strip() + ";", "level": self.level}

        # [expr for x in list]
        match = re.search(r"\[(.+?)\s+for\s+(\w+)\s+in\s+(.+?)\]", line)
        if match:
            expr, var, iterable = match.group(1), match.group(2), match.group(3)
            stream = f"{iterable}.stream().map({var} -> {expr}).collect(Collectors.toList())"
            result_line = line.replace(match.group(0), stream)
            warnings.add_list_comprehension_warning(parsed_line.line_num, line)
            return {"success": True, "converted_line": indent + result_line.strip() + ";", "level": self.level}

        return {"success": False}


class WithStatement(Rule):
    """with open(f) as x: → try (... x = ...) {"""

    def __init__(self):
        super().__init__("with_stmt", ConversionLevel.LEVEL_3)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*with\s+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        # with open(file, mode) as var:
        match = re.search(r"^\s*with\s+open\s*\(\s*(.+?)\s*(?:,\s*['\"](\w)['\"])?\s*\)\s+as\s+(\w+)\s*:", line)
        if match:
            filename = match.group(1)
            mode = match.group(2) or "r"
            var = match.group(3)

            if mode in ("r", "r+"):
                converted = (
                    f"{indent}try (BufferedReader {var} = new BufferedReader(new FileReader({filename}))) {{"
                )
            elif mode in ("w", "w+", "a"):
                converted = (
                    f"{indent}try (BufferedWriter {var} = new BufferedWriter(new FileWriter({filename}))) {{"
                )
            else:
                converted = f"{indent}try (var {var} = new FileReader({filename})) {{"

            tracker.enter_block()
            return {"success": True, "converted_line": converted, "level": self.level}

        # Generic with statement
        match = re.search(r"^\s*with\s+(.+)\s+as\s+(\w+)\s*:", line)
        if match:
            resource = match.group(1)
            var = match.group(2)
            converted = f"{indent}try (var {var} = {resource}) {{"
            tracker.enter_block()
            warnings.add_warning(
                f"Line {parsed_line.line_num}: 'with' statement converted to try-with-resources. "
                f"Ensure the resource implements AutoCloseable."
            )
            return {"success": True, "converted_line": converted, "level": self.level}

        return {"success": False}

    def creates_block(self) -> bool:
        return True


class DecoratorRule(Rule):
    """@decorator → // @decorator (comment out with warning)"""

    def __init__(self):
        super().__init__("decorator", ConversionLevel.LEVEL_1)

    def matches(self, line: str) -> bool:
        return re.search(r"^\s*@\w+", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original.strip()
        indent = parsed_line.get_target_indent("java")

        # @staticmethod and @classmethod are handled by function detection
        if line in ("@staticmethod", "@classmethod"):
            return {"success": True, "converted_line": f"{indent}// {line}", "level": self.level}

        # @property → comment
        if line == "@property":
            return {"success": True, "converted_line": f"{indent}// {line}  // TODO: convert to getter", "level": self.level}

        # @Override is valid Java
        if line == "@Override":
            return {"success": True, "converted_line": f"{indent}@Override", "level": self.level}

        warnings.add_decorator_warning(parsed_line.line_num, line.lstrip("@"))
        return {"success": True, "converted_line": f"{indent}// {line}  // TODO: no Java equivalent", "level": self.level}


class MethodCall(Rule):
    """Converts Python method calls to Java using JavaMethodConverter."""

    def __init__(self):
        super().__init__("method_call", ConversionLevel.LEVEL_1)
        self.method_converter = get_java_method_converter()

    def matches(self, line: str) -> bool:
        return re.search(r"\.\w+\s*\(", line) is not None

    def convert(self, parsed_line: ParsedLine, tracker: IndentationTracker, warnings) -> Dict:
        line = parsed_line.original
        indent = parsed_line.get_target_indent("java")

        converted = self.method_converter.convert_line(line)
        if converted:
            result_line = indent + converted.lstrip()
            return {"success": True, "converted_line": result_line, "level": self.level}

        return {"success": False}


# ---------------------------------------------------------------------------
# Main Converter Class
# ---------------------------------------------------------------------------

class PythonToJavaConverter(BaseConverter):
    """Converts Python code to Java."""

    def __init__(self):
        super().__init__("python", "java")

    def _initialize_rules(self):
        """Initialize all conversion rules for Python → Java."""
        self.rules = {
            "output": [PrintStatement()],
            "variable": [VariableDeclaration()],
            "augmented_assign": [AugmentedAssignment()],
            "return": [ReturnStatement()],
            "import": [ImportStatement()],
            "pass": [PassStatement()],
            "break_continue": [BreakContinue()],
            "raise": [RaiseStatement()],
            "assert": [AssertStatement()],
            "condition_if": [IfCondition()],
            "condition_elif": [ElifCondition()],
            "condition_else": [ElseCondition()],
            "function": [FunctionDefinition()],
            "class": [ClassDefinition()],
            "try": [TryExcept()],
            "except": [ExceptClause()],
            "finally": [FinallyClause()],
            "loop_for": [ForLoop()],
            "loop_while": [WhileLoop()],
            "list_comp": [ListComprehension()],
            "with": [WithStatement()],
            "decorator": [DecoratorRule()],
            "method_call": [MethodCall()],
        }

    def _identify_construct(self, line: str) -> Dict:
        """Override to handle Java-specific construct identification."""
        stripped = line.strip()

        if not stripped:
            return {"type": "comment", "content": stripped, "block_start": False}

        # Comments
        if stripped.startswith("#"):
            return {"type": "comment", "content": stripped, "block_start": False}

        # Decorators
        if stripped.startswith("@"):
            return {"type": "decorator", "content": stripped, "block_start": False}

        # Imports
        if re.match(r"^(import|from)\s+", stripped):
            return {"type": "import", "content": stripped, "block_start": False}

        # Class definition
        if re.match(r"^class\s+", stripped):
            return {"type": "class", "content": stripped, "block_start": True}

        # Function definition
        if re.match(r"^def\s+", stripped):
            return {"type": "function", "content": stripped, "block_start": True}

        # Control flow
        if re.match(r"^if\s+", stripped):
            return {"type": "condition_if", "content": stripped, "block_start": True}
        if re.match(r"^elif\s+", stripped):
            return {"type": "condition_elif", "content": stripped, "block_start": True}
        if re.match(r"^else\s*:", stripped):
            return {"type": "condition_else", "content": stripped, "block_start": True}

        # Loops
        if re.match(r"^for\s+\w+\s*,?\s*\w*\s+in\s+", stripped):
            return {"type": "loop_for", "content": stripped, "block_start": True}
        if re.match(r"^while\s+", stripped):
            return {"type": "loop_while", "content": stripped, "block_start": True}

        # Exception handling
        if re.match(r"^try\s*:", stripped):
            return {"type": "try", "content": stripped, "block_start": True}
        if re.match(r"^except\b", stripped):
            return {"type": "except", "content": stripped, "block_start": True}
        if re.match(r"^finally\s*:", stripped):
            return {"type": "finally", "content": stripped, "block_start": True}

        # With statement
        if re.match(r"^with\s+", stripped):
            return {"type": "with", "content": stripped, "block_start": True}

        # Return
        if re.match(r"^return\b", stripped):
            return {"type": "return", "content": stripped, "block_start": False}

        # Raise
        if re.match(r"^raise\b", stripped):
            return {"type": "raise", "content": stripped, "block_start": False}

        # Assert
        if re.match(r"^assert\b", stripped):
            return {"type": "assert", "content": stripped, "block_start": False}

        # Pass
        if re.match(r"^pass\s*$", stripped):
            return {"type": "pass", "content": stripped, "block_start": False}

        # Break / Continue
        if re.match(r"^(break|continue)\s*$", stripped):
            return {"type": "break_continue", "content": stripped, "block_start": False}

        # Print
        if re.search(r"\bprint\s*\(", stripped):
            return {"type": "output", "content": stripped, "block_start": False}

        # List comprehension
        if re.search(r"\[.+\s+for\s+\w+\s+in\s+.+\]", stripped):
            return {"type": "list_comp", "content": stripped, "block_start": False}

        # Augmented assignment (+=, -= etc.) — check before regular assignment
        if re.search(r"^\w+\s*[+\-*/|&^%]=\s*", stripped):
            return {"type": "augmented_assign", "content": stripped, "block_start": False}

        # Variable assignment
        if re.search(r"^\w+\s*=\s*", stripped) and "==" not in stripped:
            return {"type": "variable", "content": stripped, "block_start": False}

        # Method calls
        if re.search(r"\.\w+\s*\(", stripped):
            return {"type": "method_call", "content": stripped, "block_start": False}

        return {"type": "statement", "content": stripped, "block_start": False}

    def _convert_common_patterns(self, line: str) -> str:
        """Override to handle Java-specific common patterns."""
        # Boolean values
        line = re.sub(r"\bTrue\b", "true", line)
        line = re.sub(r"\bFalse\b", "false", line)

        # Logical operators
        line = re.sub(r"\band\b", "&&", line)
        line = re.sub(r"\bor\b", "||", line)
        line = re.sub(r"\bnot\b\s+", "!", line)

        # None → null
        line = re.sub(r"\bNone\b", "null", line)

        # self. → this.
        line = re.sub(r"\bself\.", "this.", line)

        # Equality — leave as == (Java uses == for primitives)
        # Don't triple-equal like JS

        return line

    def _convert_generic_line(self, parsed_line: ParsedLine) -> str:
        """Override to add semicolons and handle Java specifics."""
        indent = parsed_line.get_target_indent("java")
        line = parsed_line.original.strip()

        if not line:
            return ""

        # Comments: # → //
        if line.startswith("#"):
            return indent + "//" + line[1:]

        # Convert common patterns
        line = self._convert_common_patterns(line)

        # self. → this.
        line = re.sub(r"\bself\.", "this.", line)

        # Add semicolon if it's a statement (not a block opener)
        if not line.endswith("{") and not line.endswith("}") and not line.endswith(";"):
            line = line + ";"

        return indent + line
