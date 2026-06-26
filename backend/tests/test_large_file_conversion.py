"""
Test script for large file conversion (1000+ lines).

Run this script with your ANTHROPIC_API_KEY set to test the full pipeline.

Usage:
    # Set your API key first
    set ANTHROPIC_API_KEY=your-key-here  (Windows)
    export ANTHROPIC_API_KEY=your-key-here  (Linux/Mac)

    # Run the test
    python -m pytest tests/test_large_file_conversion.py -v -s

    # Or run directly
    python tests/test_large_file_conversion.py
"""

import os
import sys
import time
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converters.python_to_java_llm import PythonToJavaLLMConverter


def generate_large_python_code(num_lines: int = 1000) -> str:
    """
    Generate a realistic large Python codebase for testing.
    Creates a mix of classes, functions, loops, and data structures.
    """
    code_parts = [
        '"""',
        'Large Python Module for Testing Code Conversion',
        'This module contains various Python constructs to test conversion.',
        '"""',
        '',
        'import os',
        'import sys',
        'from typing import List, Dict, Optional',
        'from dataclasses import dataclass',
        '',
        '',
        '# Constants',
        'MAX_ITEMS = 100',
        'DEFAULT_NAME = "Unknown"',
        'PI = 3.14159',
        '',
        '',
    ]

    # Add a dataclass
    code_parts.extend([
        '@dataclass',
        'class Person:',
        '    """Represents a person."""',
        '    name: str',
        '    age: int',
        '    email: Optional[str] = None',
        '',
        '    def greet(self) -> str:',
        '        """Return a greeting message."""',
        '        return f"Hello, my name is {self.name}"',
        '',
        '    def is_adult(self) -> bool:',
        '        """Check if person is an adult."""',
        '        return self.age >= 18',
        '',
        '',
    ])

    # Add a more complex class
    code_parts.extend([
        'class DataProcessor:',
        '    """Process data with various methods."""',
        '',
        '    def __init__(self, data: List[int]):',
        '        """Initialize with data list."""',
        '        self.data = data',
        '        self.processed = False',
        '        self.results = {}',
        '',
        '    def filter_positive(self) -> List[int]:',
        '        """Filter positive numbers."""',
        '        return [x for x in self.data if x > 0]',
        '',
        '    def calculate_sum(self) -> int:',
        '        """Calculate sum of all numbers."""',
        '        total = 0',
        '        for num in self.data:',
        '            total += num',
        '        return total',
        '',
        '    def calculate_average(self) -> float:',
        '        """Calculate average of numbers."""',
        '        if not self.data:',
        '            return 0.0',
        '        return self.calculate_sum() / len(self.data)',
        '',
        '    def find_max(self) -> Optional[int]:',
        '        """Find maximum value."""',
        '        if not self.data:',
        '            return None',
        '        max_val = self.data[0]',
        '        for num in self.data[1:]:',
        '            if num > max_val:',
        '                max_val = num',
        '        return max_val',
        '',
        '    def find_min(self) -> Optional[int]:',
        '        """Find minimum value."""',
        '        if not self.data:',
        '            return None',
        '        return min(self.data)',
        '',
        '    def process(self) -> Dict[str, any]:',
        '        """Process data and return results."""',
        '        self.results = {',
        '            "sum": self.calculate_sum(),',
        '            "average": self.calculate_average(),',
        '            "max": self.find_max(),',
        '            "min": self.find_min(),',
        '            "positive_count": len(self.filter_positive()),',
        '        }',
        '        self.processed = True',
        '        return self.results',
        '',
        '',
    ])

    # Add standalone functions
    for i in range(20):
        code_parts.extend([
            f'def utility_function_{i}(x: int, y: int) -> int:',
            f'    """Utility function {i}."""',
            f'    result = x + y + {i}',
            '    if result > 100:',
            '        result = result % 100',
            '    return result',
            '',
            '',
        ])

    # Add more complex control flow
    code_parts.extend([
        'def complex_logic(items: List[Dict]) -> List[str]:',
        '    """Process items with complex logic."""',
        '    results = []',
        '    for i, item in enumerate(items):',
        '        if "name" in item:',
        '            name = item["name"]',
        '            if len(name) > 10:',
        '                name = name[:10] + "..."',
        '            results.append(name)',
        '        elif "id" in item:',
        '            results.append(f"Item #{item[\'id\']}")',
        '        else:',
        '            results.append(f"Unknown item {i}")',
        '    return results',
        '',
        '',
    ])

    # Add exception handling
    code_parts.extend([
        'def safe_divide(a: float, b: float) -> Optional[float]:',
        '    """Safely divide two numbers."""',
        '    try:',
        '        result = a / b',
        '        return result',
        '    except ZeroDivisionError:',
        '        print("Error: Division by zero")',
        '        return None',
        '    except TypeError as e:',
        '        print(f"Error: Invalid types - {e}")',
        '        return None',
        '    finally:',
        '        print("Division operation completed")',
        '',
        '',
    ])

    # Add while loops
    code_parts.extend([
        'def countdown(n: int) -> List[int]:',
        '    """Countdown from n to 0."""',
        '    result = []',
        '    while n >= 0:',
        '        result.append(n)',
        '        n -= 1',
        '    return result',
        '',
        '',
    ])

    # Add nested structures
    code_parts.extend([
        'def process_matrix(matrix: List[List[int]]) -> int:',
        '    """Process a 2D matrix."""',
        '    total = 0',
        '    for row in matrix:',
        '        for cell in row:',
        '            if cell > 0:',
        '                total += cell',
        '    return total',
        '',
        '',
    ])

    # Add more utility functions to reach target line count
    current_lines = len(code_parts)
    functions_needed = (num_lines - current_lines) // 15

    for i in range(functions_needed):
        code_parts.extend([
            f'def generated_function_{i}(data: List[int]) -> Dict[str, int]:',
            f'    """Generated function {i} for testing."""',
            '    result = {}',
            '    for idx, value in enumerate(data):',
            '        key = f"item_{idx}"',
            '        if value > 0:',
            '            result[key] = value * 2',
            '        elif value < 0:',
            '            result[key] = abs(value)',
            '        else:',
            '            result[key] = 0',
            '    return result',
            '',
            '',
        ])

    # Add main block
    code_parts.extend([
        'if __name__ == "__main__":',
        '    # Test the module',
        '    print("Testing DataProcessor...")',
        '    processor = DataProcessor([1, -2, 3, -4, 5])',
        '    results = processor.process()',
        '    print(f"Results: {results}")',
        '',
        '    # Test Person',
        '    person = Person("Alice", 30, "alice@example.com")',
        '    print(person.greet())',
        '    print(f"Is adult: {person.is_adult()}")',
        '',
        '    # Test utility functions',
        '    for i in range(5):',
        '        print(f"utility_function_0({i}, {i+1}) = {utility_function_0(i, i+1)}")',
        '',
        '    print("All tests completed!")',
    ])

    return '\n'.join(code_parts)


def test_large_file_token_calculation():
    """Test that token calculation works for large files."""
    converter = PythonToJavaLLMConverter()

    # Test small file
    small_code = "x = 5\nprint(x)"
    small_tokens = converter._calculate_max_tokens(small_code)
    assert small_tokens >= 4096, f"Small file should have at least 4096 tokens, got {small_tokens}"

    # Test medium file (500+ lines)
    medium_code = generate_large_python_code(600)
    medium_tokens = converter._calculate_max_tokens(medium_code)
    assert medium_tokens >= 16384, f"Medium file should have at least 16384 tokens, got {medium_tokens}"

    # Test large file (1000+ lines)
    large_code = generate_large_python_code(1100)
    large_tokens = converter._calculate_max_tokens(large_code)
    assert large_tokens >= 32768, f"Large file should have at least 32768 tokens, got {large_tokens}"

    print(f"[OK] Token calculation test passed")
    print(f"  Small file: {small_tokens} tokens")
    print(f"  Medium file ({len(medium_code.splitlines())} lines): {medium_tokens} tokens")
    print(f"  Large file ({len(large_code.splitlines())} lines): {large_tokens} tokens")


def test_large_file_api_integration():
    """
    Test large file conversion via API.
    Requires server running and ANTHROPIC_API_KEY set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[WARN] Skipping API integration test: ANTHROPIC_API_KEY not set")
        return

    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code != 200:
            print("[WARN] Skipping API integration test: Server not running")
            return
    except requests.exceptions.ConnectionError:
        print("[WARN] Skipping API integration test: Server not running on port 8000")
        return

    # Generate test code
    test_code = generate_large_python_code(100)  # Start with smaller for API test
    print(f"Testing with {len(test_code.splitlines())} lines of Python code...")

    # Send conversion request
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:8000/convert",
        json={
            "code": test_code,
            "source_language": "python",
            "target_language": "java"
        },
        timeout=120  # 2 minute timeout for large files
    )
    elapsed = time.time() - start_time

    assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"

    result = response.json()
    print(f"[OK] API conversion completed in {elapsed:.2f}s")
    print(f"  Confidence: {result['conversion_confidence']}")
    print(f"  Output lines: {len(result['converted_code'].splitlines())}")
    print(f"  Warnings: {len(result['warnings'])}")

    if result['metadata'].get('method') == 'llm':
        print(f"  Input tokens: {result['metadata'].get('input_tokens', 'N/A')}")
        print(f"  Output tokens: {result['metadata'].get('output_tokens', 'N/A')}")


def test_direct_converter_large_file():
    """
    Test large file conversion directly with converter.
    Requires ANTHROPIC_API_KEY set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[WARN] Skipping direct converter test: ANTHROPIC_API_KEY not set")
        return

    converter = PythonToJavaLLMConverter()

    # Test with increasingly large files
    for num_lines in [50, 200, 500]:
        test_code = generate_large_python_code(num_lines)
        actual_lines = len(test_code.splitlines())

        print(f"\nTesting {actual_lines} lines of Python code...")
        start_time = time.time()

        result = converter.convert(test_code)
        elapsed = time.time() - start_time

        print(f"[OK] Conversion completed in {elapsed:.2f}s")
        print(f"  Confidence: {result.conversion_confidence}")
        print(f"  Output lines: {len(result.converted_code.splitlines())}")
        print(f"  Input tokens: {result.metadata.get('input_tokens', 'N/A')}")
        print(f"  Output tokens: {result.metadata.get('output_tokens', 'N/A')}")
        print(f"  Max tokens allocated: {result.metadata.get('max_tokens_allocated', 'N/A')}")

        # Basic validation
        assert result.conversion_confidence > 0, "Confidence should be > 0"
        assert "class" in result.converted_code.lower(), "Output should contain Java class"


if __name__ == "__main__":
    print("=" * 60)
    print("Large File Conversion Tests")
    print("=" * 60)
    print()

    # Test 1: Token calculation (no API key needed)
    print("Test 1: Token Calculation")
    print("-" * 40)
    test_large_file_token_calculation()
    print()

    # Test 2: API integration (requires server + API key)
    print("Test 2: API Integration")
    print("-" * 40)
    test_large_file_api_integration()
    print()

    # Test 3: Direct converter (requires API key)
    print("Test 3: Direct Converter")
    print("-" * 40)
    test_direct_converter_large_file()
    print()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
