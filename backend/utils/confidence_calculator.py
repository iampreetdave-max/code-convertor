import ast
import os
import shutil
import subprocess
import tempfile
import re
from typing import List, Optional


class ConfidenceCalculator:
    """
    Calculates conversion confidence scores.

    The heuristic factors (line ratio, brace balance, completeness) form a
    "base" score. On top of that, when compile-checking is enabled, the OUTPUT
    is actually parsed in the target language (`ast.parse` for Python,
    `node --check` for JavaScript, `javac` for Java). A definitive parse failure
    is the strongest possible signal that the conversion is broken, so it caps
    confidence at LOW regardless of how clean the heuristics looked.

    All validators are PARSE/COMPILE-ONLY and never execute the converted code
    (`javac -proc:none`, `node --check`), so validating untrusted output is safe.

    ponytail: the JS/Java validators spawn a subprocess per conversion. That is
    fine for interactive use but adds latency on the sync request path — cap is
    MAX_VALIDATION_BYTES and a per-call timeout. Move to an async/cached layer if
    throughput ever matters. Disable entirely with CODECONV_COMPILE_CHECK=0.
    """

    # Outputs larger than this skip external validation (perf); score stays heuristic.
    MAX_VALIDATION_BYTES = 200_000
    # Subprocess timeouts (seconds). Java gets more room for JVM startup.
    JS_TIMEOUT = 10
    JAVA_TIMEOUT = 30

    # Cached tool lookups (class-level; resolved once per process).
    _TOOL_PATHS: dict = {}

    # ------------------------------------------------------------------ score
    def calculate(
        self,
        original_code: str,
        converted_code: str,
        lines_converted: int = 0,
        total_lines: int = 0,
        unsupported_count: int = 0,
        target_lang: Optional[str] = None,
        syntax_valid: Optional[bool] = None,
    ) -> float:
        """
        Calculate overall conversion confidence (0.0 - 1.0).

        Heuristic factors:
        - Structure preservation (40%): Do line counts match reasonably?
        - Syntax validity (30%): Are braces balanced? Valid constructs?
        - Conversion completeness (30%): How many lines successfully converted?

        Authoritative override:
        - If `syntax_valid` is False (output does not parse in `target_lang`),
          confidence is capped at 0.25.
        - `syntax_valid` may be passed in (to reuse a single validation run) or,
          if None and `target_lang` is given, it is computed here.

        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        original_lines = [l for l in original_code.split("\n") if l.strip()]
        converted_lines = [l for l in converted_code.split("\n") if l.strip()]

        # Factor 1: Structure preservation (40%)
        structure_score = self._calculate_structure_score(original_lines, converted_lines)

        # Factor 2: Syntax validity (30%)
        syntax_score = self._calculate_syntax_score(converted_code)

        # Factor 3: Conversion completeness (30%)
        if total_lines > 0:
            completion_score = lines_converted / total_lines
        else:
            completion_score = 1.0 if unsupported_count == 0 else 0.5

        # Apply penalty for unsupported constructs
        unsupported_penalty = min(unsupported_count * 0.15, 0.5)

        base = (
            (structure_score * 0.4) + (syntax_score * 0.3) + (completion_score * 0.3)
        ) * (1.0 - unsupported_penalty)
        base = max(0.0, min(base, 1.0))

        # Authoritative override: does the output actually parse in the target?
        if syntax_valid is None and target_lang is not None:
            syntax_valid = self.validate_output_syntax(converted_code, target_lang)
        if syntax_valid is False:
            # Output does not parse — it cannot be trusted, whatever the heuristics say.
            return max(0.0, min(base, 0.25))

        return base

    # --------------------------------------------------------- real validation
    def validate_output_syntax(self, code: str, target_lang: str) -> Optional[bool]:
        """
        Check whether `code` parses in `target_lang`.

        Returns:
            True  - parses cleanly
            False - has a definitive syntax/compile error
            None  - could not determine (checking disabled, tool missing, output
                    too large, empty, or an internal error). None never penalizes.
        """
        if not self._compile_check_enabled():
            return None
        if not code or not code.strip():
            return None
        if len(code) > self.MAX_VALIDATION_BYTES:
            return None

        lang = (target_lang or "").lower()
        if lang == "python":
            return self._validate_python(code)
        if lang == "javascript":
            return self._validate_javascript(code)
        if lang in ("typescript", "ts"):
            return self._validate_typescript(code)
        if lang == "java":
            return self._validate_java(code)
        return None

    @staticmethod
    def _compile_check_enabled() -> bool:
        # Read at call time so tests can toggle via env without import-order games.
        return os.environ.get("CODECONV_COMPILE_CHECK", "1") != "0"

    @classmethod
    def _tool(cls, name: str) -> Optional[str]:
        if name not in cls._TOOL_PATHS:
            cls._TOOL_PATHS[name] = shutil.which(name)
        return cls._TOOL_PATHS[name]

    @staticmethod
    def _validate_python(code: str) -> Optional[bool]:
        """Parse-only via the stdlib compiler; never executes the code."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
        except Exception:
            return None

    def _validate_javascript(self, code: str) -> Optional[bool]:
        node = self._tool("node")
        if not node:
            return None
        return self._run_check(
            code, suffix=".js",
            argv=lambda path: [node, "--check", path],
            timeout=self.JS_TIMEOUT,
        )

    def _validate_typescript(self, code: str) -> Optional[bool]:
        tsc = self._tool("tsc")
        if not tsc:
            return None  # ponytail: `npm i -g typescript` to enable TS validation
        # Note: tsc reports TYPE errors too, not only syntax; a standalone
        # converted file may fail on unresolved imports. skipLibCheck limits noise.
        return self._run_check(
            code, suffix=".ts",
            argv=lambda p: [tsc, "--noEmit", "--skipLibCheck", p],
            timeout=self.JS_TIMEOUT,
        )

    def _validate_java(self, code: str) -> Optional[bool]:
        javac = self._tool("javac")
        if not javac:
            return None
        # javac needs the file named after the public/top-level class.
        m = re.search(r"\bclass\s+([A-Za-z_]\w*)", code)
        if not m:
            return None  # no class to compile -> can't form a unit cheaply
        class_name = m.group(1)
        tmpdir = tempfile.mkdtemp(prefix="cc_javac_")
        path = os.path.join(tmpdir, class_name + ".java")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
            # -proc:none: never run annotation processors (no code execution).
            proc = subprocess.run(
                [javac, "-proc:none", "-nowarn", "-d", tmpdir, path],
                capture_output=True, text=True, timeout=self.JAVA_TIMEOUT, cwd=tmpdir,
            )
            return proc.returncode == 0
        except Exception:
            return None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @staticmethod
    def _run_check(code: str, suffix: str, argv, timeout: int) -> Optional[bool]:
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(code)
            proc = subprocess.run(argv(tmp), capture_output=True, text=True, timeout=timeout)
            return proc.returncode == 0
        except Exception:
            return None
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # ------------------------------------------------------- heuristic factors
    def _calculate_structure_score(self, original: List[str], converted: List[str]) -> float:
        """
        Score how well structure is preserved.
        - Similar line counts (good)
        - Similar nesting levels (good)
        """
        if not original:
            return 0.5

        line_ratio = len(converted) / len(original)

        # Allow some variance (JS often has more lines due to braces)
        # If ratio is between 0.7 and 1.5, score higher
        if 0.7 <= line_ratio <= 1.5:
            line_score = 0.95
        elif 0.5 <= line_ratio <= 2.0:
            line_score = 0.75
        else:
            line_score = 0.5

        return line_score

    def _calculate_syntax_score(self, code: str) -> float:
        """
        Score syntactic validity.
        - Balanced braces, brackets, parentheses
        - No obvious syntax errors
        """
        if not code.strip():
            return 0.0

        balanced = self._check_balanced_braces(code)
        semicolon_ratio = self._check_semicolon_consistency(code)

        return 0.7 if balanced else 0.5 + (semicolon_ratio * 0.2)

    def _check_balanced_braces(self, code: str) -> bool:
        """Check if braces, brackets, and parentheses are balanced."""
        stack = []
        pairs = {"(": ")", "[": "]", "{": "}"}

        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False

        return len(stack) == 0

    def _check_semicolon_consistency(self, code: str) -> float:
        """Check if semicolons are reasonably consistent (for JS)."""
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        if not lines:
            return 0.5

        with_semicolon = sum(1 for l in lines if l.endswith(";"))
        ratio = with_semicolon / len(lines)

        # JavaScript should mostly have semicolons (or be consistent)
        return 1.0 if 0.8 <= ratio <= 1.0 or ratio == 0.0 else 0.7
