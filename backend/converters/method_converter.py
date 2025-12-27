"""
Method Converter - Handles method call conversions between Python and JavaScript.

Provides mapping and conversion logic for:
- String methods (upper, lower, strip, etc.)
- List/Array methods (append, push, pop, etc.)
- Dictionary/Object methods (keys, values, items, etc.)
- Built-in functions (len, str, int, type, etc.)
"""

import re
from typing import Dict, Optional, List, Tuple
from enum import Enum


class MethodCategory(Enum):
    """Categories of methods."""
    STRING = "string"
    LIST_ARRAY = "list_array"
    DICT_OBJECT = "dict_object"
    BUILTIN = "builtin"
    OTHER = "other"


class MethodMapping:
    """Represents a bidirectional method mapping."""

    def __init__(self, py_method: str, js_method: str, category: MethodCategory,
                 py_pattern: Optional[str] = None, js_pattern: Optional[str] = None,
                 py_converter: Optional[callable] = None, js_converter: Optional[callable] = None):
        """
        Initialize a method mapping.

        Args:
            py_method: Python method name
            js_method: JavaScript method name
            category: Method category
            py_pattern: Optional custom regex pattern for Python
            js_pattern: Optional custom regex pattern for JavaScript
            py_converter: Optional custom converter function (Python → JavaScript)
            js_converter: Optional custom converter function (JavaScript → Python)
        """
        self.py_method = py_method
        self.js_method = js_method
        self.category = category
        self.py_pattern = py_pattern
        self.js_pattern = js_pattern
        self.py_converter = py_converter
        self.js_converter = js_converter


class MethodConverter:
    """Central method conversion system."""

    def __init__(self):
        """Initialize with all method mappings."""
        self.mappings: List[MethodMapping] = []
        self._init_string_methods()
        self._init_list_array_methods()
        self._init_dict_object_methods()
        self._init_builtin_functions()

    def _init_string_methods(self):
        """Initialize string method mappings."""
        string_methods = [
            MethodMapping("upper", "toUpperCase", MethodCategory.STRING),
            MethodMapping("lower", "toLowerCase", MethodCategory.STRING),
            MethodMapping("strip", "trim", MethodCategory.STRING),
            MethodMapping("lstrip", "trimStart", MethodCategory.STRING),
            MethodMapping("rstrip", "trimEnd", MethodCategory.STRING),
            MethodMapping("replace", "replace", MethodCategory.STRING),
            MethodMapping("split", "split", MethodCategory.STRING),
            MethodMapping("join", "join", MethodCategory.STRING),
            MethodMapping("startswith", "startsWith", MethodCategory.STRING),
            MethodMapping("endswith", "endsWith", MethodCategory.STRING),
            MethodMapping("find", "indexOf", MethodCategory.STRING),
            MethodMapping("count", "split().length - 1", MethodCategory.STRING),
            MethodMapping("isdigit", "match(/^\\d+$/) !== null", MethodCategory.STRING),
            MethodMapping("isalpha", "match(/^[a-zA-Z]+$/) !== null", MethodCategory.STRING),
            MethodMapping("isalnum", "match(/^[a-zA-Z0-9]+$/) !== null", MethodCategory.STRING),
            MethodMapping("capitalize", "charAt(0).toUpperCase() + slice(1)", MethodCategory.STRING),
            MethodMapping("swapcase", None, MethodCategory.STRING),  # No direct equivalent
            MethodMapping("title", None, MethodCategory.STRING),  # Needs custom logic
            MethodMapping("isupper", "match(/[a-z]/) === null && match(/[A-Z]/) !== null", MethodCategory.STRING),
            MethodMapping("islower", "match(/[A-Z]/) === null && match(/[a-z]/) !== null", MethodCategory.STRING),
        ]
        self.mappings.extend(string_methods)

    def _init_list_array_methods(self):
        """Initialize list/array method mappings."""
        list_array_methods = [
            MethodMapping("append", "push", MethodCategory.LIST_ARRAY),
            MethodMapping("extend", "concat", MethodCategory.LIST_ARRAY),
            MethodMapping("insert", "splice", MethodCategory.LIST_ARRAY),
            MethodMapping("remove", "splice", MethodCategory.LIST_ARRAY),
            MethodMapping("pop", "pop", MethodCategory.LIST_ARRAY),
            MethodMapping("clear", "splice(0)", MethodCategory.LIST_ARRAY),
            MethodMapping("index", "indexOf", MethodCategory.LIST_ARRAY),
            MethodMapping("count", "filter(x => x === value).length", MethodCategory.LIST_ARRAY),
            MethodMapping("sort", "sort", MethodCategory.LIST_ARRAY),
            MethodMapping("reverse", "reverse", MethodCategory.LIST_ARRAY),
            MethodMapping("copy", "slice", MethodCategory.LIST_ARRAY),
            MethodMapping("slice", "slice", MethodCategory.LIST_ARRAY),
        ]
        self.mappings.extend(list_array_methods)

    def _init_dict_object_methods(self):
        """Initialize dictionary/object method mappings."""
        dict_object_methods = [
            MethodMapping("keys", "Object.keys", MethodCategory.DICT_OBJECT),
            MethodMapping("values", "Object.values", MethodCategory.DICT_OBJECT),
            MethodMapping("items", "Object.entries", MethodCategory.DICT_OBJECT),
            MethodMapping("get", "get or bracket notation", MethodCategory.DICT_OBJECT),
            # Note: dict.pop() and list.pop() both exist, so we don't map pop to avoid conflicts
            MethodMapping("popitem", "Object.entries()[0]", MethodCategory.DICT_OBJECT),
            MethodMapping("clear", "for...in delete", MethodCategory.DICT_OBJECT),
            MethodMapping("update", "Object.assign", MethodCategory.DICT_OBJECT),
            MethodMapping("copy", "Object.assign({}, obj)", MethodCategory.DICT_OBJECT),
            MethodMapping("setdefault", "|| operator", MethodCategory.DICT_OBJECT),
            MethodMapping("fromkeys", "Object.fromEntries", MethodCategory.DICT_OBJECT),
        ]
        self.mappings.extend(dict_object_methods)

    def _init_builtin_functions(self):
        """Initialize built-in function mappings."""
        builtin_functions = [
            MethodMapping("len", "length", MethodCategory.BUILTIN),
            MethodMapping("str", "String", MethodCategory.BUILTIN),
            MethodMapping("int", "parseInt", MethodCategory.BUILTIN),
            MethodMapping("float", "parseFloat", MethodCategory.BUILTIN),
            MethodMapping("bool", "Boolean", MethodCategory.BUILTIN),
            MethodMapping("list", "Array", MethodCategory.BUILTIN),
            MethodMapping("dict", "Object", MethodCategory.BUILTIN),
            MethodMapping("set", "Set", MethodCategory.BUILTIN),
            MethodMapping("tuple", "Array", MethodCategory.BUILTIN),
            MethodMapping("type", "typeof", MethodCategory.BUILTIN),
            MethodMapping("abs", "Math.abs", MethodCategory.BUILTIN),
            MethodMapping("min", "Math.min", MethodCategory.BUILTIN),
            MethodMapping("max", "Math.max", MethodCategory.BUILTIN),
            MethodMapping("sum", "reduce((a, b) => a + b)", MethodCategory.BUILTIN),
            MethodMapping("round", "Math.round", MethodCategory.BUILTIN),
            MethodMapping("pow", "Math.pow", MethodCategory.BUILTIN),
            MethodMapping("sqrt", "Math.sqrt", MethodCategory.BUILTIN),
            MethodMapping("sorted", "sort", MethodCategory.BUILTIN),
            MethodMapping("reversed", "reverse", MethodCategory.BUILTIN),
            MethodMapping("enumerate", "forEach((value, index))", MethodCategory.BUILTIN),
            MethodMapping("zip", "zip function needed", MethodCategory.BUILTIN),
            MethodMapping("range", "for loop or Array.from({length})", MethodCategory.BUILTIN),
            MethodMapping("map", "map", MethodCategory.BUILTIN),
            MethodMapping("filter", "filter", MethodCategory.BUILTIN),
            MethodMapping("any", "some", MethodCategory.BUILTIN),
            MethodMapping("all", "every", MethodCategory.BUILTIN),
        ]
        self.mappings.extend(builtin_functions)

    def convert_python_to_javascript(self, line: str) -> Optional[str]:
        """
        Convert Python method calls to JavaScript.

        Args:
            line: Python code line

        Returns:
            Converted JavaScript line or None if no conversion found
        """
        result = line
        converted_any = False

        # Apply all mappings, allowing multiple conversions per line (chained methods)
        for mapping in self.mappings:
            if not mapping.js_method:
                continue

            # Try custom converter first
            if mapping.py_converter:
                converted = mapping.py_converter(result, mapping)
                if converted:
                    result = converted
                    converted_any = True
                    continue

            # Default conversion patterns - convert ALL occurrences
            if self._matches_python_method(result, mapping.py_method):
                new_result = self._convert_all_method_calls(result, mapping.py_method, mapping.js_method)
                if new_result != result:
                    result = new_result
                    converted_any = True

        return result if converted_any else None

    def convert_javascript_to_python(self, line: str) -> Optional[str]:
        """
        Convert JavaScript method calls to Python.

        Args:
            line: JavaScript code line

        Returns:
            Converted Python line or None if no conversion found
        """
        result = line
        converted_any = False

        # Apply all mappings, allowing multiple conversions per line (chained methods)
        for mapping in self.mappings:
            if not mapping.py_method:
                continue

            # Try custom converter first
            if mapping.js_converter:
                converted = mapping.js_converter(result, mapping)
                if converted:
                    result = converted
                    converted_any = True
                    continue

            # Default conversion patterns - convert ALL occurrences
            if self._matches_javascript_method(result, mapping.js_method):
                new_result = self._convert_all_method_calls(result, mapping.js_method, mapping.py_method)
                if new_result != result:
                    result = new_result
                    converted_any = True

        return result if converted_any else None

    @staticmethod
    def _matches_python_method(line: str, method_name: str) -> bool:
        """Check if line contains Python method call."""
        # Skip if method_name is None or empty
        if not method_name:
            return False

        # Pattern: .method( or .method()
        pattern = rf"\.{re.escape(method_name)}\s*\("
        return re.search(pattern, line) is not None

    @staticmethod
    def _matches_javascript_method(line: str, method_name: str) -> bool:
        """Check if line contains JavaScript method call."""
        # Skip if method_name is None or empty
        if not method_name:
            return False

        # Handle special cases like Object.keys, Math.abs, etc.
        if "." in method_name:
            # e.g., "Object.keys" or "Math.abs"
            parts = method_name.split(".")
            actual_method = parts[-1]
        else:
            actual_method = method_name

        # Pattern: .method( or .method()
        pattern = rf"\.{re.escape(actual_method)}\s*\("
        return re.search(pattern, line) is not None

    @staticmethod
    def _convert_method_call(line: str, old_method: str, new_method: str) -> str:
        """
        Convert method call from old_method to new_method.

        Args:
            line: Code line
            old_method: Method to replace
            new_method: Method to replace with

        Returns:
            Converted line (first occurrence only)
        """
        # Handle special cases
        if "." in new_method:
            # e.g., "Object.keys" - use direct replacement
            pattern = rf"\.{re.escape(old_method)}"
            return re.sub(pattern, "." + new_method, line, count=1)
        else:
            # Simple method name
            pattern = rf"\.{re.escape(old_method)}"
            return re.sub(pattern, "." + new_method, line, count=1)

    @staticmethod
    def _convert_all_method_calls(line: str, old_method: str, new_method: str) -> str:
        """
        Convert ALL method calls from old_method to new_method.

        Args:
            line: Code line
            old_method: Method to replace
            new_method: Method to replace with

        Returns:
            Converted line (all occurrences)
        """
        # Handle special cases
        if "." in new_method:
            # e.g., "Object.keys" - use direct replacement
            pattern = rf"\.{re.escape(old_method)}"
            return re.sub(pattern, "." + new_method, line)
        else:
            # Simple method name
            pattern = rf"\.{re.escape(old_method)}"
            return re.sub(pattern, "." + new_method, line)

    def get_mapping(self, method_name: str, direction: str) -> Optional[MethodMapping]:
        """
        Get mapping for a method.

        Args:
            method_name: Method name
            direction: "py2js" or "js2py"

        Returns:
            MethodMapping or None
        """
        for mapping in self.mappings:
            if direction == "py2js" and mapping.py_method == method_name:
                return mapping
            elif direction == "js2py" and mapping.js_method == method_name:
                return mapping
        return None

    def get_all_mappings_by_category(self, category: MethodCategory) -> List[MethodMapping]:
        """Get all mappings in a category."""
        return [m for m in self.mappings if m.category == category]


# Global instance for convenient access
_method_converter_instance = None


def get_method_converter() -> MethodConverter:
    """Get or create the global method converter instance."""
    global _method_converter_instance
    if _method_converter_instance is None:
        _method_converter_instance = MethodConverter()
    return _method_converter_instance
