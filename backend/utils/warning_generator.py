from typing import List, Dict


class WarningGenerator:
    """Generates meaningful warnings about conversion issues."""

    def __init__(self):
        self.warnings: List[str] = []
        self.unsupported_constructs: List[Dict] = []

    def add_warning(self, message: str):
        """Add a general warning."""
        if message not in self.warnings:
            self.warnings.append(message)

    def add_type_hint_warning(self, line: int, hint: str):
        """Python type hints → JavaScript (not applicable)."""
        msg = f"Line {line}: Type hint '{hint}' removed (not applicable in JavaScript)"
        self.add_warning(msg)

    def add_decorator_warning(self, line: int, decorator: str):
        """Python decorator → JavaScript (needs manual conversion)."""
        msg = f"Line {line}: Decorator '@{decorator}' may need manual conversion to higher-order function"
        self.add_warning(msg)

    def add_list_comprehension_warning(self, line: int, original: str):
        """Python list comprehension → JavaScript .map()/.filter()."""
        msg = f"Line {line}: List comprehension converted to .map()/.filter() - verify logic matches"
        self.add_warning(msg)
        self.unsupported_constructs.append({
            "line": line,
            "construct": "list comprehension",
            "type": "warning",
            "description": original
        })

    def add_unpacking_warning(self, line: int, construct: str):
        """Python unpacking (*args, **kwargs) → JavaScript."""
        msg = f"Line {line}: {construct} unpacking not directly supported - converted to rest parameters, manual review needed"
        self.add_warning(msg)
        self.unsupported_constructs.append({
            "line": line,
            "construct": construct,
            "type": "warning"
        })

    def add_docstring_warning(self, line: int):
        """Python docstring → JavaScript JSDoc."""
        msg = f"Line {line}: Docstring converted to JSDoc comment - verify formatting"
        self.add_warning(msg)

    def add_indentation_warning(self, issue: str):
        """Indentation-related warnings."""
        msg = f"Indentation: {issue}"
        self.add_warning(msg)

    def add_unsupported_keyword(self, line: int, keyword: str, reason: str = ""):
        """Generic unsupported keyword."""
        msg = f"Line {line}: '{keyword}' - {reason}" if reason else f"Line {line}: '{keyword}' not supported"
        self.add_warning(msg)
        self.unsupported_constructs.append({
            "line": line,
            "construct": keyword,
            "type": "error",
            "description": reason
        })

    def add_conversion_issue(self, line: int, issue: str):
        """General conversion issue."""
        msg = f"Line {line}: {issue}"
        self.add_warning(msg)

    def add_method_conversion_note(self, line: int, python_method: str, js_equivalent: str):
        """Note about method conversion (e.g., len() → .length)."""
        msg = f"Line {line}: Python '{python_method}' converted to JavaScript '{js_equivalent}' - verify it matches your intent"
        self.add_warning(msg)

    def add_string_format_conversion(self, line: int):
        """String formatting conversion (f-strings → template literals)."""
        msg = f"Line {line}: Python f-string converted to JavaScript template literal - syntax verified"
        self.add_warning(msg)

    def clear(self):
        """Clear all warnings and constructs."""
        self.warnings = []
        self.unsupported_constructs = []

    def get_all(self) -> tuple:
        """Return (warnings, unsupported_constructs)."""
        return self.warnings, self.unsupported_constructs
