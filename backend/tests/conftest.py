import os
import sys

# Ensure `backend/` is importable for all tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The bulk suite asserts against the legacy heuristic confidence and must not
# depend on node/javac being installed. Real compile-checking is exercised
# explicitly in test_confidence_real.py (which re-enables it per-test).
os.environ["CODECONV_COMPILE_CHECK"] = "0"
