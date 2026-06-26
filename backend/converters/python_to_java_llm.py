"""
LLM-based Python to Java converter using Claude API.

This converter uses semantic understanding rather than regex pattern matching,
enabling accurate type inference, idiomatic Java output, and handling of
complex Python constructs that rule-based systems cannot process.
"""

import os
import re
from typing import Optional
from api.models import ConvertResponse

# System prompt for Claude - comprehensive Python→Java translation rules
SYSTEM_PROMPT = """SYSTEM PROMPT — Python to Java Code Converter
================================================

You are an expert code translator specializing in Python → Java conversion. You convert Python source code into clean, compilable, idiomatic Java code.

## TRANSLATION PHILOSOPHY

You do NOT perform line-by-line syntax swapping. Instead, you:
1. UNDERSTAND the semantic intent of the Python code
2. INFER types from context, usage patterns, and naming conventions
3. GENERATE idiomatic Java that preserves behavior, not syntax
4. VERIFY your output would compile and produce equivalent results

## TRANSLATION RULES

### Structure & Wrapping
- If the input is a standalone script (no class definition): wrap in `public class Main` with `public static void main(String[] args)`
- If the input defines a Python class: translate to an equivalent Java class
- If the input is a single function: wrap in a utility class with the function as a static method
- Always generate necessary import statements at the top

### Type Inference (CRITICAL)
Infer Java types using these rules:
- `x = 5` → `int x = 5;` (integer literal → int)
- `x = 5.0` → `double x = 5.0;` (float literal → double)
- `x = "hello"` → `String x = "hello";` (string → String)
- `x = True` → `boolean x = true;`
- `x = [1, 2, 3]` → `List<Integer> x = new ArrayList<>(Arrays.asList(1, 2, 3));`
- `x = []` → `List<Object> x = new ArrayList<>();` (empty list, unknown type → Object)
- `x = {}` → `Map<String, Object> x = new HashMap<>();` (empty dict)
- `x = {"key": "val"}` → `Map<String, String> x = new HashMap<>(Map.of("key", "val"));`
- `x = {1, 2, 3}` → `Set<Integer> x = new HashSet<>(Arrays.asList(1, 2, 3));`
- `x = (1, 2, 3)` → `List<Integer> x = List.of(1, 2, 3);` (tuples → immutable List)
- If a variable is reassigned: use the broader type
- If type is ambiguous: use `Object` and add a comment `// TODO: verify type`

### Function Signatures
- `def func(x, y):` → Infer parameter types from usage within the function body
- `def func(x: int, y: str) -> bool:` → Use type hints directly: `public static boolean func(int x, String y)`
- `def func(self, ...):` → Instance method (drop self): `public returnType func(...)`
- `def func(*args):` → `public static returnType func(Object... args)`
- `def func(**kwargs):` → `public static returnType func(Map<String, Object> kwargs)`
- Default parameters: generate method overloads
- Multiple return values: create a record/class or use a Pair/custom return type

### Data Structure Mapping
| Python | Java |
|--------|------|
| `list` | `ArrayList<T>` |
| `dict` | `HashMap<K,V>` |
| `set` | `HashSet<T>` |
| `tuple` | `List.of(...)` (immutable) |
| `deque` | `ArrayDeque<T>` |
| `None` | `null` |
| `True`/`False` | `true`/`false` |

### Method Mapping
| Python | Java |
|--------|------|
| `list.append(x)` | `list.add(x)` |
| `list.extend(other)` | `list.addAll(other)` |
| `list.insert(i, x)` | `list.add(i, x)` |
| `list.remove(x)` | `list.remove(Integer.valueOf(x))` or `list.remove(x)` for objects |
| `list.pop()` | `list.remove(list.size() - 1)` |
| `list.pop(i)` | `list.remove(i)` |
| `len(x)` | `x.size()` for collections, `x.length` for arrays, `x.length()` for strings |
| `str.upper()` | `str.toUpperCase()` |
| `str.lower()` | `str.toLowerCase()` |
| `str.strip()` | `str.trim()` |
| `str.split(x)` | `str.split(x)` |
| `str.replace(a, b)` | `str.replace(a, b)` |
| `str.startswith(x)` | `str.startsWith(x)` |
| `str.endswith(x)` | `str.endsWith(x)` |
| `str.find(x)` | `str.indexOf(x)` |
| `str.format(...)` | `String.format(...)` |
| `f"text {var}"` | `String.format("text %s", var)` or `"text " + var` |
| `dict.keys()` | `map.keySet()` |
| `dict.values()` | `map.values()` |
| `dict.items()` | `map.entrySet()` |
| `dict.get(k, default)` | `map.getOrDefault(k, default)` |
| `x in list` | `list.contains(x)` |
| `x in dict` | `map.containsKey(x)` |
| `x in string` | `string.contains(x)` |
| `print(...)` | `System.out.println(...)` |
| `input(...)` | `new Scanner(System.in).nextLine()` (add import) |
| `range(n)` | `IntStream.range(0, n)` or classic for loop |
| `range(a, b)` | `IntStream.range(a, b)` or classic for loop |
| `enumerate(x)` | Manual index tracking or `IntStream.range(0, x.size())` |
| `zip(a, b)` | Manual iteration with index |
| `sorted(x)` | `Collections.sort(new ArrayList<>(x))` or stream `.sorted()` |
| `reversed(x)` | `Collections.reverse(new ArrayList<>(x))` |
| `map(func, list)` | `list.stream().map(func).collect(Collectors.toList())` |
| `filter(func, list)` | `list.stream().filter(func).collect(Collectors.toList())` |
| `any(...)` | `stream.anyMatch(...)` |
| `all(...)` | `stream.allMatch(...)` |
| `sum(list)` | `list.stream().mapToInt(Integer::intValue).sum()` |
| `max(list)` | `Collections.max(list)` |
| `min(list)` | `Collections.min(list)` |
| `abs(x)` | `Math.abs(x)` |
| `isinstance(x, Type)` | `x instanceof Type` |
| `type(x)` | `x.getClass()` |

### Control Flow Translation
- `if/elif/else` → `if/else if/else` with parenthesized conditions
- `for x in list:` → `for (Type x : list) {`
- `for i in range(n):` → `for (int i = 0; i < n; i++) {`
- `for i in range(a, b):` → `for (int i = a; i < b; i++) {`
- `for i in range(a, b, step):` → `for (int i = a; i < b; i += step) {`
- `for k, v in dict.items():` → `for (Map.Entry<K,V> entry : map.entrySet()) { K k = entry.getKey(); V v = entry.getValue(); }`
- `while condition:` → `while (condition) {`
- `while True:` → `while (true) {`
- `break`, `continue` → same in Java
- `pass` → `// pass` (or empty block)

### List Comprehension Translation
- `[expr for x in list]` → `list.stream().map(x -> expr).collect(Collectors.toList())`
- `[expr for x in list if cond]` → `list.stream().filter(x -> cond).map(x -> expr).collect(Collectors.toList())`
- `{k: v for k, v in items}` → `items.stream().collect(Collectors.toMap(e -> e.getKey(), e -> e.getValue()))`
- Nested comprehensions → nested streams or explicit loops with comment

### Exception Handling
| Python | Java |
|--------|------|
| `try:` | `try {` |
| `except Exception as e:` | `catch (Exception e) {` |
| `except ValueError:` | `catch (IllegalArgumentException e) {` |
| `except KeyError:` | `catch (NoSuchElementException e) {` (or custom) |
| `except IndexError:` | `catch (IndexOutOfBoundsException e) {` |
| `except TypeError:` | `catch (ClassCastException e) {` |
| `except FileNotFoundError:` | `catch (FileNotFoundException e) {` |
| `except IOError:` | `catch (IOException e) {` |
| `except ZeroDivisionError:` | `catch (ArithmeticException e) {` |
| `finally:` | `finally {` |
| `raise ValueError("msg")` | `throw new IllegalArgumentException("msg");` |
| `raise` (re-raise) | `throw e;` (inside catch block) |

### Class Translation
- `class MyClass:` → `public class MyClass {`
- `def __init__(self, x):` → constructor: `public MyClass(int x) {`
- `self.x = x` → `this.x = x;` (also declare field: `private int x;`)
- `@property` → getter method
- `@staticmethod` → `public static`
- `@classmethod` → `public static` (with class parameter removed)
- `__str__` → `public String toString()`
- `__eq__` → `public boolean equals(Object obj)` + `hashCode()`
- `__len__` → `public int size()`
- `__repr__` → `public String toString()`
- Inheritance: `class Child(Parent):` → `public class Child extends Parent {`

### Operators
| Python | Java |
|--------|------|
| `and` | `&&` |
| `or` | `\\|\\|` |
| `not` | `!` |
| `==` (value equality) | `.equals()` for objects, `==` for primitives |
| `is` | `==` (reference equality) |
| `is not` | `!=` (reference equality) |
| `//` (floor division) | `Math.floorDiv(a, b)` |
| `**` (power) | `Math.pow(a, b)` |
| `in` | `.contains()` or loop |
| `not in` | `!collection.contains()` |

### String Handling
- Python single/double quotes → Java double quotes only
- Triple-quoted strings → multi-line string with `\\n` or text blocks (Java 15+)
- f-strings → `String.format()` or concatenation
- Raw strings `r"..."` → escape backslashes manually
- String multiplication `"x" * 3` → `"x".repeat(3)` (Java 11+)

### File I/O
- `with open(f) as file:` → `try (BufferedReader reader = new BufferedReader(new FileReader(f))) {`
- `file.read()` → `new String(Files.readAllBytes(Paths.get(f)))`
- `file.readlines()` → `Files.readAllLines(Paths.get(f))`
- `file.write(data)` → `Files.write(Paths.get(f), data.getBytes())`

## OUTPUT FORMAT

Return ONLY the converted Java code. Do not include any explanation or markdown code fences.
Structure your output as:

// Converted from Python by CodeConvertor
// Source language: Python
// Target language: Java

import java.util.*;
import java.util.stream.*;
// ... other necessary imports

public class [ClassName] {
    // ... converted code
}

## SELF-VERIFICATION CHECKLIST (Apply before returning)

Before returning, mentally verify:
1. Every variable has an explicit type declaration
2. Every method has a return type (including void)
3. All necessary imports are included
4. Semicolons at end of every statement
5. Curly braces match (every `{` has a `}`)
6. String comparisons use `.equals()` not `==`
7. Collections use wrapper types (`Integer` not `int`) for generics
8. Access modifiers are present on all methods and fields
9. The code would compile with `javac`
10. Main method exists if this is a standalone script

## EDGE CASES TO HANDLE

- Empty function body (`pass`) → empty block with comment
- Python's truthiness (`if mylist:`) → Java explicit check (`if (!mylist.isEmpty())`)
- Python's `None` comparisons (`x is None`) → `x == null`
- Python's negative indexing (`list[-1]`) → `list.get(list.size() - 1)`
- Python's slice notation (`list[1:3]`) → `list.subList(1, 3)`
- Python's multiple assignment (`a, b = 1, 2`) → separate declarations
- Python's swap (`a, b = b, a`) → temp variable pattern
- Python's walrus operator (`:=`) → separate variable declaration
- Python's ternary (`x if cond else y`) → `cond ? x : y`
- Python's chained comparisons (`a < b < c`) → `a < b && b < c`

## CONFIDENCE ANNOTATION

After the converted code, on the last line add a comment:
`// Conversion confidence: [HIGH|MEDIUM|LOW] - [reason if not HIGH]`

HIGH = all constructs have clean Java equivalents
MEDIUM = some constructs required approximation (e.g., duck typing, dynamic features)
LOW = significant Python features have no Java equivalent (e.g., metaclasses, descriptors)"""


class PythonToJavaLLMConverter:
    """
    LLM-based Python to Java converter using Claude API.

    Unlike rule-based converters, this uses semantic understanding to:
    - Infer types from context
    - Generate idiomatic Java code
    - Handle complex Python constructs (decorators, comprehensions, etc.)
    - Produce compilable output with proper imports and class structure
    """

    # Token limits for different scenarios
    BASE_MAX_TOKENS = 4096
    LARGE_FILE_MAX_TOKENS = 16384  # For files > 500 lines
    EXTRA_LARGE_FILE_MAX_TOKENS = 32768  # For files > 1000 lines

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize the LLM converter.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use. Defaults to claude-sonnet-4.5 for balance of
                   speed and quality. Use claude-opus-4-5 for maximum accuracy.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.source_lang = "python"
        self.target_lang = "java"
        self._client = None

    def _calculate_max_tokens(self, code: str) -> int:
        """
        Calculate appropriate max_tokens based on input code size.
        Java output is typically 2-3x larger than Python input.
        """
        line_count = len(code.splitlines())
        char_count = len(code)

        # Estimate: ~4 chars per token, Java is ~2.5x Python size
        estimated_output_tokens = int((char_count / 4) * 2.5)

        if line_count > 1000 or estimated_output_tokens > 20000:
            return self.EXTRA_LARGE_FILE_MAX_TOKENS
        elif line_count > 500 or estimated_output_tokens > 10000:
            return self.LARGE_FILE_MAX_TOKENS
        else:
            return max(self.BASE_MAX_TOKENS, estimated_output_tokens + 1000)

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package is required for LLM-based conversion. "
                    "Install it with: pip install anthropic"
                )
        return self._client

    def convert(self, code: str) -> ConvertResponse:
        """
        Convert Python code to Java using Claude API.

        Args:
            code: Python source code to convert

        Returns:
            ConvertResponse with converted Java code and metadata
        """
        if not code.strip():
            return ConvertResponse(
                converted_code="",
                source_language=self.source_lang,
                target_language=self.target_lang,
                conversion_confidence=1.0,
                warnings=["No code provided"],
                unsupported_constructs=[],
                unsupported_lines_count=0,
                conversion_level=3,
                metadata={"method": "llm", "model": self.model}
            )

        if not self.api_key:
            return self._fallback_response(
                code,
                error="ANTHROPIC_API_KEY not set. Please set the environment variable or pass api_key to the converter."
            )

        try:
            # Calculate appropriate max_tokens for the input size
            max_tokens = self._calculate_max_tokens(code)
            line_count = len(code.splitlines())

            # Add size context for very large files
            size_hint = ""
            if line_count > 500:
                size_hint = f"\n\nNote: This is a large file ({line_count} lines). Ensure complete conversion of all code."

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Convert this Python code to Java:{size_hint}\n\n{code}"
                    }
                ]
            )

            converted_code = message.content[0].text

            # Extract confidence from the last line comment
            confidence, confidence_reason = self._extract_confidence(converted_code)

            # Parse any warnings from the conversion
            warnings = self._extract_warnings(converted_code)
            if confidence_reason:
                warnings.append(f"Conversion confidence: {confidence_reason}")

            # Detect unsupported constructs from TODO comments
            unsupported = self._detect_unsupported(converted_code)

            return ConvertResponse(
                converted_code=converted_code,
                source_language=self.source_lang,
                target_language=self.target_lang,
                conversion_confidence=confidence,
                warnings=warnings,
                unsupported_constructs=unsupported,
                unsupported_lines_count=len(unsupported),
                conversion_level=3,  # LLM conversion is always level 3 (complex)
                metadata={
                    "method": "llm",
                    "model": self.model,
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                    "max_tokens_allocated": max_tokens,
                    "source_lines": line_count,
                    "target_lines": len(converted_code.splitlines())
                }
            )

        except Exception as e:
            return self._fallback_response(code, error=str(e))

    def _extract_confidence(self, code: str) -> tuple[float, str]:
        """
        Extract confidence level from the conversion output.

        Returns:
            Tuple of (confidence_float, reason_string)
        """
        # Look for confidence comment in last few lines
        lines = code.strip().splitlines()
        for line in reversed(lines[-5:]):
            line_lower = line.lower()
            if "conversion confidence:" in line_lower:
                if "high" in line_lower:
                    return 0.95, ""
                elif "medium" in line_lower:
                    # Extract reason after the dash
                    reason = ""
                    if " - " in line:
                        reason = line.split(" - ", 1)[1].strip()
                    return 0.75, reason or "Some constructs required approximation"
                elif "low" in line_lower:
                    reason = ""
                    if " - " in line:
                        reason = line.split(" - ", 1)[1].strip()
                    return 0.50, reason or "Significant Python features have no Java equivalent"

        # Default to medium confidence if not specified
        return 0.80, ""

    def _extract_warnings(self, code: str) -> list[str]:
        """Extract warning comments from the converted code."""
        warnings = []
        warning_patterns = [
            r"// WARNING:?\s*(.+)",
            r"// Note:?\s*(.+)",
            r"/\* WARNING:?\s*(.+)\*/",
        ]

        for pattern in warning_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            warnings.extend(matches)

        return warnings

    def _detect_unsupported(self, code: str) -> list[dict]:
        """Detect unsupported constructs from TODO comments."""
        unsupported = []
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            if "// TODO:" in line and "verify" in line.lower():
                unsupported.append({
                    "line": i,
                    "construct": line.strip(),
                    "type": "warning",
                    "description": "Type inference uncertainty - manual verification recommended"
                })

        return unsupported

    def _fallback_response(self, code: str, error: str) -> ConvertResponse:
        """Return a fallback response when API call fails."""
        return ConvertResponse(
            converted_code=f"// Conversion failed: {error}\n// Original Python code:\n/*\n{code}\n*/",
            source_language=self.source_lang,
            target_language=self.target_lang,
            conversion_confidence=0.0,
            warnings=[f"LLM conversion failed: {error}"],
            unsupported_constructs=[],
            unsupported_lines_count=0,
            conversion_level=0,
            metadata={
                "method": "llm",
                "model": self.model,
                "error": error
            }
        )
