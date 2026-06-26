"""
Java Method Converter - Handles method call conversions between Python and Java.

Provides mapping and conversion logic for:
- String methods (upper, lower, strip, etc.)
- List/Array methods (append, add, pop, etc.)
- Dictionary/Map methods (keys, values, items, etc.)
- Built-in functions (len, str, int, type, etc.)
- Math functions (abs, min, max, pow, etc.)
"""

import re
from typing import Optional, List


class JavaMethodMapping:
    """Represents a Python → Java method mapping."""

    def __init__(self, py_method: str, java_method: str, category: str,
                 needs_import: Optional[str] = None,
                 transform: Optional[str] = None):
        """
        Args:
            py_method: Python method name
            java_method: Java method/replacement
            category: string, list, dict, builtin, math
            needs_import: Java import needed (e.g., "java.util.ArrayList")
            transform: Special transform type for complex conversions
        """
        self.py_method = py_method
        self.java_method = java_method
        self.category = category
        self.needs_import = needs_import
        self.transform = transform


class JavaMethodConverter:
    """Converts Python method calls to Java equivalents."""

    def __init__(self):
        self.mappings: List[JavaMethodMapping] = []
        self.required_imports: set = set()
        self._init_string_methods()
        self._init_list_methods()
        self._init_dict_methods()
        self._init_builtin_functions()
        self._init_math_functions()

    def _init_string_methods(self):
        methods = [
            JavaMethodMapping("upper", "toUpperCase", "string"),
            JavaMethodMapping("lower", "toLowerCase", "string"),
            JavaMethodMapping("strip", "trim", "string"),
            JavaMethodMapping("lstrip", "stripLeading", "string"),
            JavaMethodMapping("rstrip", "stripTrailing", "string"),
            JavaMethodMapping("replace", "replace", "string"),
            JavaMethodMapping("split", "split", "string"),
            JavaMethodMapping("startswith", "startsWith", "string"),
            JavaMethodMapping("endswith", "endsWith", "string"),
            JavaMethodMapping("find", "indexOf", "string"),
            JavaMethodMapping("count", "chars().filter(c -> c == ch).count()", "string",
                              transform="string_count"),
            JavaMethodMapping("isdigit", "matches(\"\\\\d+\")", "string",
                              transform="string_predicate"),
            JavaMethodMapping("isalpha", "matches(\"[a-zA-Z]+\")", "string",
                              transform="string_predicate"),
            JavaMethodMapping("isalnum", "matches(\"[a-zA-Z0-9]+\")", "string",
                              transform="string_predicate"),
            JavaMethodMapping("capitalize", "substring(0, 1).toUpperCase() + .substring(1)", "string",
                              transform="capitalize"),
            JavaMethodMapping("title", "title", "string", transform="unsupported"),
            JavaMethodMapping("swapcase", "swapcase", "string", transform="unsupported"),
            JavaMethodMapping("isupper", "equals(.toUpperCase())", "string",
                              transform="string_self_compare"),
            JavaMethodMapping("islower", "equals(.toLowerCase())", "string",
                              transform="string_self_compare"),
            JavaMethodMapping("join", "String.join", "string", transform="join"),
            JavaMethodMapping("format", "String.format", "string", transform="str_format"),
            JavaMethodMapping("encode", "getBytes", "string"),
            JavaMethodMapping("zfill", "format", "string", transform="unsupported"),
        ]
        self.mappings.extend(methods)

    def _init_list_methods(self):
        methods = [
            JavaMethodMapping("append", "add", "list"),
            JavaMethodMapping("extend", "addAll", "list"),
            JavaMethodMapping("insert", "add", "list"),  # add(index, element)
            JavaMethodMapping("remove", "remove", "list", transform="list_remove"),
            JavaMethodMapping("pop", "remove", "list", transform="list_pop"),
            JavaMethodMapping("clear", "clear", "list"),
            JavaMethodMapping("index", "indexOf", "list"),
            JavaMethodMapping("sort", "sort", "list", transform="list_sort"),
            JavaMethodMapping("reverse", "reverse", "list",
                              needs_import="java.util.Collections",
                              transform="collections_reverse"),
            JavaMethodMapping("copy", "new ArrayList<>", "list",
                              needs_import="java.util.ArrayList",
                              transform="list_copy"),
        ]
        self.mappings.extend(methods)

    def _init_dict_methods(self):
        methods = [
            JavaMethodMapping("keys", "keySet", "dict"),
            JavaMethodMapping("values", "values", "dict"),
            JavaMethodMapping("items", "entrySet", "dict"),
            JavaMethodMapping("get", "getOrDefault", "dict", transform="dict_get"),
            JavaMethodMapping("pop", "remove", "dict"),
            JavaMethodMapping("update", "putAll", "dict"),
            JavaMethodMapping("clear", "clear", "dict"),
            JavaMethodMapping("setdefault", "putIfAbsent", "dict"),
            JavaMethodMapping("containsKey", "containsKey", "dict"),
        ]
        self.mappings.extend(methods)

    def _init_builtin_functions(self):
        methods = [
            JavaMethodMapping("len", ".size()", "builtin", transform="len"),
            JavaMethodMapping("str", "String.valueOf", "builtin"),
            JavaMethodMapping("int", "Integer.parseInt", "builtin"),
            JavaMethodMapping("float", "Double.parseDouble", "builtin"),
            JavaMethodMapping("bool", "Boolean.valueOf", "builtin"),
            JavaMethodMapping("type", ".getClass().getSimpleName()", "builtin", transform="type"),
            JavaMethodMapping("isinstance", "instanceof", "builtin", transform="isinstance"),
            JavaMethodMapping("sorted", "sorted", "builtin",
                              needs_import="java.util.Collections",
                              transform="sorted"),
            JavaMethodMapping("reversed", "reversed", "builtin",
                              needs_import="java.util.Collections",
                              transform="reversed"),
            JavaMethodMapping("enumerate", "enumerate", "builtin", transform="enumerate"),
            JavaMethodMapping("zip", "zip", "builtin", transform="unsupported"),
            JavaMethodMapping("map", "stream().map", "builtin", transform="stream_map"),
            JavaMethodMapping("filter", "stream().filter", "builtin", transform="stream_filter"),
            JavaMethodMapping("any", "stream().anyMatch", "builtin", transform="stream_any"),
            JavaMethodMapping("all", "stream().allMatch", "builtin", transform="stream_all"),
            JavaMethodMapping("sum", "stream().mapToInt(Integer::intValue).sum()", "builtin",
                              transform="stream_sum"),
            JavaMethodMapping("input", "scanner.nextLine", "builtin",
                              needs_import="java.util.Scanner",
                              transform="input"),
        ]
        self.mappings.extend(methods)

    def _init_math_functions(self):
        methods = [
            JavaMethodMapping("abs", "Math.abs", "math"),
            JavaMethodMapping("min", "Math.min", "math"),
            JavaMethodMapping("max", "Math.max", "math"),
            JavaMethodMapping("round", "Math.round", "math"),
            JavaMethodMapping("pow", "Math.pow", "math"),
            JavaMethodMapping("sqrt", "Math.sqrt", "math"),
        ]
        self.mappings.extend(methods)

    def convert_line(self, line: str) -> Optional[str]:
        """
        Convert Python method calls in a line to Java equivalents.

        Args:
            line: Python code line

        Returns:
            Converted Java line or None if no conversion found
        """
        result = line
        converted_any = False

        # --- Handle built-in function calls first (not dot methods) ---

        # print() → System.out.println()
        # Handled separately in the rule, but also catch inline prints
        result_new = re.sub(r'\bprint\s*\(', 'System.out.println(', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # len(x) → x.size() for collections, x.length() for strings, x.length for arrays
        def convert_len(match):
            arg = match.group(1).strip()
            # Heuristic: if it looks like a string literal, use .length()
            if arg.startswith('"') or arg.startswith("'"):
                return f"{arg}.length()"
            # Default to .size() (works for List, Set, Map)
            return f"{arg}.size()"
        result_new = re.sub(r'\blen\s*\(\s*([^)]+)\s*\)', convert_len, result)
        if result_new != result:
            result = result_new
            converted_any = True

        # str(x) → String.valueOf(x)
        result_new = re.sub(r'\bstr\s*\(\s*([^)]+)\s*\)', r'String.valueOf(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # int(x) → Integer.parseInt(x)
        result_new = re.sub(r'\bint\s*\(\s*([^)]+)\s*\)', r'Integer.parseInt(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # float(x) → Double.parseDouble(x)
        result_new = re.sub(r'\bfloat\s*\(\s*([^)]+)\s*\)', r'Double.parseDouble(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # abs(x) → Math.abs(x)
        result_new = re.sub(r'\babs\s*\(\s*([^)]+)\s*\)', r'Math.abs(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # min(a, b) → Math.min(a, b)
        result_new = re.sub(r'\bmin\s*\(\s*([^)]+)\s*\)', r'Math.min(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # max(a, b) → Math.max(a, b)
        result_new = re.sub(r'\bmax\s*\(\s*([^)]+)\s*\)', r'Math.max(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # round(x) → Math.round(x)
        result_new = re.sub(r'\bround\s*\(\s*([^)]+)\s*\)', r'Math.round(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # pow(a, b) → Math.pow(a, b)
        result_new = re.sub(r'\bpow\s*\(\s*([^)]+)\s*\)', r'Math.pow(\1)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # isinstance(x, Type) → x instanceof Type
        def convert_isinstance(match):
            args = match.group(1)
            parts = args.split(",", 1)
            if len(parts) == 2:
                obj = parts[0].strip()
                type_name = parts[1].strip()
                # Map Python types to Java
                type_map = {
                    "str": "String", "int": "Integer", "float": "Double",
                    "bool": "Boolean", "list": "List", "dict": "Map",
                    "set": "Set", "tuple": "List",
                }
                type_name = type_map.get(type_name, type_name)
                return f"{obj} instanceof {type_name}"
            return match.group(0)
        result_new = re.sub(r'\bisinstance\s*\(\s*([^)]+)\s*\)', convert_isinstance, result)
        if result_new != result:
            result = result_new
            converted_any = True

        # type(x) → x.getClass().getSimpleName()
        result_new = re.sub(r'\btype\s*\(\s*([^)]+)\s*\)', r'\1.getClass().getSimpleName()', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # --- Handle dot method calls ---
        # Simple 1:1 method renames
        simple_renames = [
            ("upper", "toUpperCase"),
            ("lower", "toLowerCase"),
            ("strip", "trim"),
            ("lstrip", "stripLeading"),
            ("rstrip", "stripTrailing"),
            ("startswith", "startsWith"),
            ("endswith", "endsWith"),
            ("find", "indexOf"),
            ("append", "add"),
            ("extend", "addAll"),
            ("index", "indexOf"),
            ("keys", "keySet"),
            ("values", "values"),
            ("items", "entrySet"),
            ("update", "putAll"),
            ("setdefault", "putIfAbsent"),
            ("encode", "getBytes"),
        ]

        for py_name, java_name in simple_renames:
            pattern = rf'\.{re.escape(py_name)}\s*\('
            replacement = f'.{java_name}('
            result_new = re.sub(pattern, replacement, result)
            if result_new != result:
                result = result_new
                converted_any = True

        # .sort() → Collections.sort(obj)  (in-place sort)
        sort_match = re.search(r'(\w+)\.sort\s*\(\s*\)', result)
        if sort_match:
            obj = sort_match.group(1)
            result = result[:sort_match.start()] + f'Collections.sort({obj})' + result[sort_match.end():]
            self.required_imports.add("java.util.Collections")
            converted_any = True

        # .reverse() → Collections.reverse(obj)
        reverse_match = re.search(r'(\w+)\.reverse\s*\(\s*\)', result)
        if reverse_match:
            obj = reverse_match.group(1)
            result = result[:reverse_match.start()] + f'Collections.reverse({obj})' + result[reverse_match.end():]
            self.required_imports.add("java.util.Collections")
            converted_any = True

        # .copy() → new ArrayList<>(obj)
        copy_match = re.search(r'(\w+)\.copy\s*\(\s*\)', result)
        if copy_match:
            obj = copy_match.group(1)
            result = result[:copy_match.start()] + f'new ArrayList<>({obj})' + result[copy_match.end():]
            self.required_imports.add("java.util.ArrayList")
            converted_any = True

        # .pop() → .remove(.size() - 1)   (no args = last element)
        pop_no_args_match = re.search(r'(\w+)\.pop\s*\(\s*\)', result)
        if pop_no_args_match:
            obj = pop_no_args_match.group(1)
            result = result[:pop_no_args_match.start()] + f'{obj}.remove({obj}.size() - 1)' + result[pop_no_args_match.end():]
            converted_any = True

        # .pop(i) → .remove(i)
        pop_args_match = re.search(r'\.pop\s*\(\s*([^)]+)\s*\)', result)
        if pop_args_match:
            result = re.sub(r'\.pop\s*\(', '.remove(', result)
            converted_any = True

        # ".join(list) → String.join("", list)
        join_match = re.search(r'(["\'][^"\']*["\'])\.join\s*\(\s*([^)]+)\s*\)', result)
        if join_match:
            separator = join_match.group(1)
            iterable = join_match.group(2)
            result = result[:join_match.start()] + f'String.join({separator}, {iterable})' + result[join_match.end():]
            converted_any = True

        # .get(key, default) → .getOrDefault(key, default)
        result_new = re.sub(r'\.get\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)', r'.getOrDefault(\1, \2)', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # .get(key) → .get(key)  (already valid in Java)

        # .isdigit() → .matches("\\d+")
        result_new = re.sub(r'\.isdigit\s*\(\s*\)', '.matches("\\\\d+")', result)
        if result_new != result:
            result = result_new
            converted_any = True

        # .isalpha() → .matches("[a-zA-Z]+")
        result_new = re.sub(r'\.isalpha\s*\(\s*\)', '.matches("[a-zA-Z]+")', result)
        if result_new != result:
            result = result_new
            converted_any = True

        return result if converted_any else None

    def get_required_imports(self) -> set:
        """Return set of Java imports needed based on conversions performed."""
        return self.required_imports

    def reset_imports(self):
        """Reset import tracking for a new conversion."""
        self.required_imports = set()


# Global instance
_java_method_converter = None


def get_java_method_converter() -> JavaMethodConverter:
    """Get or create the global Java method converter instance."""
    global _java_method_converter
    if _java_method_converter is None:
        _java_method_converter = JavaMethodConverter()
    return _java_method_converter
