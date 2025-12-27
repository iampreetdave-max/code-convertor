# Phase 3 Week 2: JavaScript → Python Converter Scope

## Professional Scope Definition

This document explicitly defines what will and will NOT be implemented for JavaScript→Python conversion. This prevents scope creep and ensures intentional, professional scoping.

## IN SCOPE: Supported Constructs

### Level 1: Simple Replacements (100% Accuracy Expected)
- **Console Output**: `console.log(...) → print(...)`
- **Variable Declarations**: `let x = 5; → x = 5`; `const X = 5; → X = 5`; `var x = 5; → x = 5`
- **Boolean Values**: `true → True`, `false → False`
- **Null**: `null → None`
- **Comments**: `// comment → # comment`
- **Strings**: No conversion needed (identical syntax)
- **Numbers**: No conversion needed (identical syntax)

### Level 2: Structural Transformations (Most Important)
- **If Statements**: `if (condition) { ... } → if condition: ...`
- **Else If**: `else if (condition) { ... } → elif condition: ...`
- **Else Block**: `else { ... } → else: ...`
- **While Loops**: `while (condition) { ... } → while condition: ...`
- **Function Declarations**: `function name(params) { ... } → def name(params): ...`
- **Error Handling**:
  - `try { ... } catch (e) { ... } → try: ... except Exception as e: ...`
  - `try { ... } catch { ... } → try: ... except Exception: ...`
- **Condition Conversion**: `===`→`==`, `!==`→`!=`, `&&`→`and`, `||`→`or`, `!x`→`not x`
- **Indentation**: Convert 2-space JavaScript blocks to 4-space Python blocks

### Level 3: Complex Conversions (Warnings Allowed)
- **For Loops with Range**: `for (let i = 0; i < 5; i++) { ... } → for i in range(5): ...`
- **For-Of Loops**: `for (let x of array) { ... } → for x in array: ...`
- **For-In Loops**: `for (let key in obj) { ... } → for key in obj: ...` (with warning)
- **Arrow Functions (Simple)**: `x => x * 2 → lambda x: x * 2` (with warning about limitations)
- **Array Methods**: (warning-based, not automatic conversion)
  - `.map(x => ...)` → list comprehension or map function
  - `.filter(x => ...)` → list comprehension or filter function
  - `.forEach(...)` → for loop conversion

## OUT OF SCOPE: Explicitly Not Supported

### Classes and OOP
- ❌ Class definitions: `class Name { ... }`
- ❌ Constructors: `constructor() { ... }`
- ❌ Methods and inheritance
- ❌ `this` keyword
- ❌ Prototypes
- ❌ `new` operator
- **Reason**: Python and JavaScript OOP patterns are fundamentally different. Would require separate architecture.

### Advanced Arrow Functions
- ❌ Complex arrow functions with multiple statements: `(a, b) => { x = a + b; return x; }`
- ❌ Arrow functions with implicit returns beyond simple expressions
- ❌ Nested arrow functions
- **Reason**: Lambda syntax in Python is limited; full conversion unreliable.

### Async/Await
- ❌ `async` functions
- ❌ `await` expressions
- ❌ Promises: `.then()`, `.catch()`
- **Reason**: Python async is different (asyncio); would create false equivalence.

### Advanced Features
- ❌ Destructuring: `const { a, b } = obj`
- ❌ Spread operator: `...array`
- ❌ Template literals with complex expressions (beyond simple `${var}`)
- ❌ Computed property names
- ❌ Getters/setters
- ❌ Symbols
- ❌ Map/Set data structures
- **Reason**: Python lacks direct equivalents; conversions would be misleading.

### Closures and Scope
- ❌ Closure patterns
- ❌ Higher-order functions requiring scope preservation
- **Reason**: Complex scope semantics; conversions unreliable.

## Architecture Mirroring

### Same Components as Python→JavaScript

```python
# backend/converters/javascript_to_python.py

class JavaScriptToPythonConverter(BaseConverter):
    """Converts JavaScript to Python."""

    # Rule classes (11 total):
    # 1. ConsoleLogStatement (Level 1)
    # 2. VariableDeclaration (Level 1)
    # 3. IfStatement (Level 2)
    # 4. ElseIfStatement (Level 2)
    # 5. ElseStatement (Level 2)
    # 6. FunctionDeclaration (Level 2)
    # 7. WhileLoop (Level 2)
    # 8. TryBlock (Level 2)
    # 9. CatchBlock (Level 2)
    # 10. ForLoop (Level 3)
    # 11. ArrowFunction (Level 3)
```

### Same Quality Gates as Python→JavaScript

1. **Indentation Balance**:
   - Check that indentation levels are consistent
   - Python uses 4 spaces per level (vs JavaScript 2 spaces)
   - Verify no syntax breaks due to indentation errors

2. **Syntax Validity**:
   - Python must have valid syntax (no stray braces, etc.)
   - Colons after block-starting statements required
   - Proper indentation for all blocks

3. **Confidence Calculation**:
   - Structure preservation (40%): Line count ratio
   - Syntax validity (30%): Valid Python indentation
   - Conversion completeness (30%): Lines successfully converted
   - Unsupported penalty: -15% per unsupported construct

4. **Construct Detection**:
   - Metadata must list all detected constructs
   - Confidence scores per construct type
   - Clear warnings for unsupported/risky conversions

5. **Warning Generation**:
   - Type hints not needed (removed without warning)
   - Arrow functions → lambda (warning about limitations)
   - Complex methods → warnings about manual review needed
   - Async/classes → clear rejection with explanation

## Testing Strategy

### Test Categories

1. **Level 1 Simple Replacements** (5 tests)
   - console.log() → print()
   - Variable declarations (let/const/var)
   - Boolean/null conversions
   - Comments
   - Simple assignment

2. **Level 2 Structural** (10 tests)
   - If/else conditions
   - If/elif/else chains
   - While loops
   - Function definitions
   - Try/catch blocks
   - Condition operators (===, &&, ||, !)

3. **Level 3 Complex** (5 tests)
   - For loops with range
   - For-of/for-in loops
   - Arrow functions to lambda
   - Nested structures
   - Multiple indentation levels

4. **Quality Gates** (5 tests)
   - Indentation consistency (4-space Python standard)
   - Balanced logic (colons after conditions/loops/functions)
   - Confidence scoring ranges
   - Warning generation accuracy
   - Unsupported construct detection

### Total Test Count: 25+ tests

All tests must verify:
- ✅ Correct syntax conversion
- ✅ Proper indentation (4 spaces per level)
- ✅ Confidence > 0.7 for basic conversions
- ✅ Warnings for Level 3 constructs
- ✅ No syntax errors in output

## Conversion Rules Priority

### Rule Matching Order

1. **Comments** (highest priority - must match before other patterns)
2. **Console.log** (output statements)
3. **Variable Declarations** (let/const/var)
4. **Function Declarations** (function keyword)
5. **Try Block** (try keyword)
6. **Catch Block** (catch keyword)
7. **If Statement** (if keyword)
8. **Else If** (else if keywords)
9. **Else** (else keyword)
10. **While Loop** (while keyword)
11. **For Loop** (for keyword - includes for-of, for-in, standard)
12. **Arrow Function** (=> operator)
13. **Generic Statement** (fallback - basic syntax conversion only)

## Known Limitations & Workarounds

| Limitation | Workaround | Warning Level |
|---|---|---|
| Complex arrow functions | Use lambda for simple cases; manual conversion for complex | ⚠️ Level 3 Warning |
| Method chaining | Suggest breaking into separate statements | ⚠️ Note |
| Computed properties | Manual conversion required | ❌ Error |
| Destructuring | Not supported | ❌ Error |
| Prototypes | Not supported | ❌ Error |
| Classes | Not supported | ❌ Error |
| Async/await | Not supported | ❌ Error |

## Success Criteria

✅ **Complete** when:
- All 25+ tests passing
- Bidirectional conversion working (Py→JS + JS→Py)
- Same architecture used for both directions
- Confidence scores correlate with actual quality
- Warnings are honest and actionable
- No architectural debt introduced
- Clear scope documentation

## Professional Statement

> "JavaScript → Python conversion is intentionally scoped to match Python → JavaScript parity at the same complexity levels. Classes, async/await, and advanced scope features are out of scope and clearly documented. The architecture proves language-agnostic design by using identical patterns for both directions. This is a professional milestone: bidirectional support complete."

---

## Implementation Checklist

- [ ] Create `backend/converters/javascript_to_python.py` (11 rule classes)
- [ ] Register in `backend/core/conversion_engine.py`
- [ ] Create `backend/tests/test_js2py_examples.py` (25+ tests)
- [ ] Run all tests and verify quality gates
- [ ] Update `frontend.html` to support JS→Python conversion
- [ ] Commit with message: "Implement Phase 3 Week 2: JavaScript→Python converter with bidirectional support"
- [ ] Push to branch
- [ ] Mark Phase 3 Week 2 complete

---

**Scope Approved**: ✅ Intentional, Professional, Documented

