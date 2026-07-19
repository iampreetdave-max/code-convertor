"""
Real end-to-end tests: compile Java with javac, decompile the .class with CFR.

Skips (rather than fails) if javac isn't on PATH, so the suite stays green on
machines without a JDK. The demo machine has both java and javac.
"""
import os
import shutil
import subprocess
import tempfile

import pytest

from converters.bytecode_decompiler import decompile_bytecode, DecompileError

HAS_JAVAC = shutil.which("javac") is not None and shutil.which("java") is not None

SAMPLE = """
public class Greeter {
    public String greet(String name) {
        return "Hello, " + name + "!";
    }

    public int add(int a, int b) {
        return a + b;
    }
}
"""


def _compile_to_class(source: str, class_name: str) -> bytes:
    """Compile `source` with javac and return the .class bytes."""
    tmp = tempfile.mkdtemp(prefix="javac_")
    try:
        src = os.path.join(tmp, f"{class_name}.java")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source)
        subprocess.run(["javac", src], cwd=tmp, capture_output=True, text=True, check=True)
        with open(os.path.join(tmp, f"{class_name}.class"), "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.skipif(not HAS_JAVAC, reason="javac/java not on PATH")
def test_decompiles_class_to_readable_java():
    class_bytes = _compile_to_class(SAMPLE, "Greeter")
    result = decompile_bytecode(class_bytes, "Greeter.class")

    assert result["language"] == "java"
    assert result["classes"] == 1
    src = result["source"]
    # Readable Java: class name, method names, and a recognizable literal survive.
    assert "class Greeter" in src
    assert "greet" in src
    assert "add" in src
    assert "Hello, " in src


def test_invalid_input_raises_structured_error():
    with pytest.raises(DecompileError) as exc:
        decompile_bytecode(b"this is not bytecode", "junk.class")
    assert exc.value.status_code == 400


def test_empty_input_raises():
    with pytest.raises(DecompileError) as exc:
        decompile_bytecode(b"", "empty.class")
    assert exc.value.status_code == 400


def test_oversized_input_raises():
    with pytest.raises(DecompileError) as exc:
        decompile_bytecode(b"\xca\xfe\xba\xbe" + b"\x00" * (6 * 1024 * 1024), "big.class")
    assert exc.value.status_code == 400


@pytest.mark.skipif(not HAS_JAVAC, reason="javac/java not on PATH")
def test_endpoint_via_testclient():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    class_bytes = _compile_to_class(SAMPLE, "Greeter")
    resp = client.post(
        "/decompile",
        files={"file": ("Greeter.class", class_bytes, "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] == "java"
    assert body["classes"] == 1
    assert "class Greeter" in body["source"]

    # Invalid upload -> graceful 400, not a crash.
    bad = client.post(
        "/decompile",
        files={"file": ("junk.class", b"nope", "application/octet-stream")},
    )
    assert bad.status_code == 400
