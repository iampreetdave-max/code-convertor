"""Comprehensive tests for Python → Java converter."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from converters.python_to_java import PythonToJavaConverter


def run_test(name, python_code, expected_fragments):
    converter = PythonToJavaConverter()
    result = converter.convert(python_code)
    output = result.converted_code
    ok = all(frag in output for frag in expected_fragments)
    status = "PASS" if ok else "FAIL"
    print(f"  [{'OK' if ok else 'X'}] {status} | {name}")
    if not ok:
        for frag in expected_fragments:
            if frag not in output:
                print(f"       MISSING: '{frag}'")
        print(f"       OUTPUT: {repr(output[:200])}")
    return ok


def main():
    total = 0
    passed = 0
    tests = [
        # === LEVEL 1: Simple Statements ===
        ("print basic", 'print("hello")', ["System.out.println"]),
        ("print fstring", 'print(f"hi {name}")', ["String.format"]),
        ("var int", "x = 42", ["int x = 42;"]),
        ("var float", "pi = 3.14", ["double pi = 3.14;"]),
        ("var string", 'name = "ratin"', ['String name = "ratin";']),
        ("var bool", "flag = True", ["boolean flag = true;"]),
        ("var none", "x = None", ["x = null;"]),
        ("var list", "items = [1, 2, 3]", ["ArrayList"]),
        ("var empty list", "items = []", ["new ArrayList<>()"]),
        ("var dict empty", "data = {}", ["new HashMap<>()"]),
        ("constant", "MAX_SIZE = 100", ["static final", "MAX_SIZE"]),
        ("return value", "    return x + 1", ["return x + 1;"]),
        ("return bare", "    return", ["return;"]),
        ("import", "import os", ["// import os"]),
        ("pass", "    pass", ["// pass"]),
        ("break", "        break", ["break;"]),
        ("continue", "        continue", ["continue;"]),
        ("raise ValueError", 'raise ValueError("bad")', ["throw new IllegalArgumentException"]),
        ("raise RuntimeError", 'raise RuntimeError("x")', ["throw new RuntimeException"]),
        ("assert", "assert x > 0", ["assert x > 0;"]),
        ("augmented +=", "x += 5", ["x += 5;"]),

        # === LEVEL 2: Structural ===
        ("if stmt", "if x > 10:\n    print(x)", ["if (x > 10) {"]),
        ("elif", "if x > 10:\n    pass\nelif x > 5:\n    pass", ["else if (x > 5) {"]),
        ("else", "if x:\n    pass\nelse:\n    pass", ["else {"]),
        ("func basic", "def greet(name):\n    print(name)", ["public static", "greet"]),
        ("func typed", "def add(x: int, y: int) -> int:\n    return x + y",
         ["int add(int x, int y)"]),
        ("func self", "def get(self):\n    return self.x",
         ["public", "get()", "return this.x;"]),
        ("class", "class Dog:\n    pass", ["public class Dog {"]),
        ("class extend", "class Dog(Animal):\n    pass", ["extends Animal"]),
        ("try", "try:\n    x = 1", ["try {"]),
        ("except typed", "try:\n    pass\nexcept ValueError as e:\n    pass",
         ["catch (IllegalArgumentException e) {"]),
        ("except bare", "try:\n    pass\nexcept:\n    pass",
         ["catch (Exception e) {"]),
        ("finally", "try:\n    pass\nfinally:\n    pass", ["finally {"]),

        # === LEVEL 3: Complex ===
        ("for range", "for i in range(10):\n    print(i)",
         ["for (int i = 0; i < 10; i++) {"]),
        ("for range 2-arg", "for i in range(5, 20):\n    print(i)",
         ["for (int i = 5; i < 20; i++) {"]),
        ("for each", "for item in items:\n    print(item)",
         ["for (var item : items) {"]),
        ("for dict", "for k, v in data.items():\n    print(k)",
         ["entrySet()", "getKey()", "getValue()"]),
        ("for enumerate", "for i, x in enumerate(lst):\n    print(i)",
         ["lst.size()", "lst.get("]),
        ("while", "while x > 0:\n    x -= 1", ["while (x > 0) {"]),
        ("list comp", "doubled = [x * 2 for x in nums]",
         [".stream().map(", "Collectors.toList()"]),
        ("list comp filter", "evens = [x for x in nums if x % 2 == 0]",
         [".stream().filter("]),
        ("with open", 'with open("f.txt", "r") as f:\n    data = f.read()',
         ["try (BufferedReader", "FileReader"]),
        ("decorator", "@staticmethod\ndef h():\n    pass", ["// @staticmethod"]),

        # === Boolean / Operator Conversions ===
        ("and op", "if x and y:\n    pass", ["&&"]),
        ("or op", "if x or y:\n    pass", ["||"]),
        ("not op", "if not x:\n    pass", ["!"]),
        ("is None", "if x is None:\n    pass", ["== null"]),
        ("is not None", "if x is not None:\n    pass", ["!= null"]),
        ("self to this", "    self.name = name", ["this.name"]),

        # === Comments ===
        ("comment", "# this is a comment", ["// this is a comment"]),
    ]

    for name, code, expected in tests:
        total += 1
        if run_test(name, code, expected):
            passed += 1

    # === Full program test ===
    total += 1
    full_program = """
def fibonacci(n: int) -> int:
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a = 0
        b = 1
        for i in range(2, n + 1):
            temp = a + b
            a = b
            b = temp
        return b
""".strip()
    if run_test("full fibonacci", full_program,
                ["int fibonacci(int n)", "if (n <= 0)", "return 0;", "return 1;",
                 "for (int i = "]):
        passed += 1

    # === Full class test ===
    total += 1
    class_program = """
class Calculator:
    def __init__(self, value: int):
        self.value = value

    def add(self, x: int) -> int:
        self.value += x
        return self.value

    def reset(self):
        self.value = 0
""".strip()
    if run_test("full class", class_program,
                ["public class Calculator {", "this.value", "public int add(int x)",
                 "return this.value;"]):
        passed += 1

    print(f"\n{'='*50}")
    print(f"  RESULTS: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"{'='*50}")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
