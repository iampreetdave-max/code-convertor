"""
JVM bytecode -> Java decompiler, backed by the bundled CFR jar.

CFR only *reads* the bytecode; it never executes it, so decompiling untrusted
.class/.jar uploads is safe. Everything runs in a throwaway temp dir that is
removed afterward.

Public entry point: decompile_bytecode(data, filename) -> dict.
"""
import os
import shutil
import subprocess
import tempfile

CFR_JAR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "cfr.jar")

TIMEOUT_SECONDS = 30
MAX_BYTES = 5 * 1024 * 1024      # 5MB upload cap
MAX_CLASSES = 50                 # cap decompiled .java files concatenated for a .jar

# Magic numbers used to tell a .class from a .jar (zip) when the filename lies.
CLASS_MAGIC = b"\xca\xfe\xba\xbe"
ZIP_MAGIC = b"PK\x03\x04"


class DecompileError(Exception):
    """Structured failure. status_code picks 400 (bad input) vs 500 (env/tool)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _kind(data: bytes, filename: str) -> str:
    """Return 'class' or 'jar'. Trust magic bytes over the (spoofable) extension."""
    if data.startswith(CLASS_MAGIC):
        return "class"
    if data.startswith(ZIP_MAGIC):
        return "jar"
    # Fall back to extension only if magic is inconclusive (rare/truncated files).
    lower = (filename or "").lower()
    if lower.endswith(".jar"):
        return "jar"
    if lower.endswith(".class"):
        return "class"
    raise DecompileError(
        "Not a Java .class or .jar file (bad magic bytes). Expected 0xCAFEBABE or a zip.",
        status_code=400,
    )


def decompile_bytecode(data: bytes, filename: str = "input.class") -> dict:
    """
    Decompile uploaded JVM bytecode to Java source.

    Args:
        data: raw bytes of a .class or .jar file.
        filename: original name, used only for extension hints / headers.

    Returns:
        {"language": "java", "source": <str>, "classes": <int>, "warnings": [<str>...]}

    Raises:
        DecompileError: with .status_code (400 bad input / 500 environment).
    """
    if not data:
        raise DecompileError("Empty file.", status_code=400)
    if len(data) > MAX_BYTES:
        raise DecompileError(
            f"File too large ({len(data)} bytes). Limit is {MAX_BYTES} bytes.",
            status_code=400,
        )

    java = shutil.which("java")
    if java is None:
        raise DecompileError("'java' runtime not found on PATH.", status_code=500)
    if not os.path.isfile(CFR_JAR):
        raise DecompileError(f"CFR jar missing at {CFR_JAR}.", status_code=500)

    kind = _kind(data, filename)
    warnings: list[str] = []

    tmp = tempfile.mkdtemp(prefix="cfr_")
    try:
        in_path = os.path.join(tmp, f"input.{kind}")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)
        with open(in_path, "wb") as f:
            f.write(data)

        try:
            proc = subprocess.run(
                [java, "-jar", CFR_JAR, in_path, "--outputdir", out_dir],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise DecompileError(
                f"Decompilation timed out after {TIMEOUT_SECONDS}s.", status_code=400
            )

        java_files = sorted(
            os.path.join(root, name)
            for root, _dirs, names in os.walk(out_dir)
            for name in names
            if name.endswith(".java")
        )

        if not java_files:
            # CFR reports its complaint on stderr (or stdout for --outputdir runs).
            detail = (proc.stderr or proc.stdout or "").strip()
            detail = detail.splitlines()[0] if detail else "no Java produced"
            raise DecompileError(f"Could not decompile file: {detail}", status_code=400)

        total = len(java_files)
        if total > MAX_CLASSES:
            warnings.append(
                f"Jar has {total} classes; only the first {MAX_CLASSES} were decompiled."
            )
            java_files = java_files[:MAX_CLASSES]

        parts = []
        for path in java_files:
            rel = os.path.relpath(path, out_dir).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                parts.append(f"// ==== {rel} ====\n{f.read().rstrip()}")

        return {
            "language": "java",
            "source": "\n\n".join(parts) + "\n",
            "classes": min(total, MAX_CLASSES),
            "warnings": warnings,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
