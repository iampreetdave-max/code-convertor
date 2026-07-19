"""
Security & safety regression tests (PR #1).

Covers the P0 fixes:
  1. The API must NOT serve the project root (no secret/source exposure).
  2. The frontend is still served at "/", health JSON at "/api/health".
  3. Request bodies above MAX_REQUEST_SIZE are rejected with 413.
  4. report_generator escapes the language/method fields (reflected XSS).

Each test targets a specific defect confirmed in the 2026-07 audit; if a fix
regresses, exactly one of these fails.
"""

import sys
import os

from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, MAX_REQUEST_SIZE
from core.report_generator import ReportGenerator

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. No secret / source exposure over HTTP
# ---------------------------------------------------------------------------

class TestNoFileExposure:
    """The old `StaticFiles(directory="..")` mount leaked .env, .git and source."""

    def test_dotenv_not_served(self):
        r = client.get("/.env")
        assert r.status_code != 200, "SECURITY: /.env is being served over HTTP"

    def test_dotenv_example_not_served(self):
        assert client.get("/.env.example").status_code != 200

    def test_backend_source_not_served(self):
        for path in ("/backend/main.py", "/backend/core/code_validator.py"):
            assert client.get(path).status_code != 200, f"SECURITY: {path} is served"

    def test_git_config_not_served(self):
        assert client.get("/.git/config").status_code != 200

    def test_launch_scripts_not_served(self):
        for path in ("/start.sh", "/start_server.bat"):
            assert client.get(path).status_code != 200

    def test_path_traversal_blocked(self):
        # Even if some static handler existed, traversal must not escape.
        r = client.get("/../.env")
        assert r.status_code != 200


# ---------------------------------------------------------------------------
# 2. Frontend + health still work
# ---------------------------------------------------------------------------

class TestFrontendStillServed:

    def test_root_serves_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "<" in r.text  # actual markup, not JSON

    def test_health_endpoint_json(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "Backend running"
        assert "supported_pairs" in data


# ---------------------------------------------------------------------------
# 3. Request-size limit is enforced
# ---------------------------------------------------------------------------

class TestRequestSizeLimit:

    def test_oversize_body_rejected_413(self):
        body = b"x" * (MAX_REQUEST_SIZE + 1)
        r = client.post("/convert", content=body)
        assert r.status_code == 413, f"expected 413, got {r.status_code}"

    def test_body_at_limit_not_size_rejected(self):
        # Exactly at the limit must pass the size gate (may still be a 4xx for
        # bad JSON, but must NOT be 413).
        body = b"x" * MAX_REQUEST_SIZE
        r = client.post("/convert", content=body)
        assert r.status_code != 413

    def test_normal_request_passes(self):
        r = client.post("/convert", json={
            "code": "print('hello')",
            "source_language": "python",
            "target_language": "javascript",
        })
        assert r.status_code == 200
        assert r.status_code != 413


# ---------------------------------------------------------------------------
# 4. Report generator escapes language/method fields (reflected XSS)
# ---------------------------------------------------------------------------

class TestReportXSS:

    PAYLOAD = "<script>alert('xss')</script>"

    def _build_html(self, **overrides):
        gen = ReportGenerator()
        kwargs = dict(
            original_code="x = 1",
            converted_code="let x = 1;",
            source_lang="python",
            target_lang="javascript",
            confidence=0.9,
            warnings=[],
            conversion_method="rule-based",
        )
        kwargs.update(overrides)
        report = gen.generate_report(**kwargs)
        return gen.to_html(report)

    def test_source_language_escaped(self):
        html = self._build_html(source_lang=self.PAYLOAD)
        assert "<script>" not in html.lower(), "XSS via source_language"
        assert "&lt;script&gt;" in html.lower()

    def test_target_language_escaped(self):
        html = self._build_html(target_lang=self.PAYLOAD)
        assert "<script>" not in html.lower(), "XSS via target_language"

    def test_conversion_method_escaped(self):
        html = self._build_html(conversion_method=self.PAYLOAD)
        assert "<script>" not in html.lower(), "XSS via conversion_method"

    def test_code_body_still_escaped(self):
        # Regression guard: code bodies were already escaped; keep them so.
        html = self._build_html(original_code=self.PAYLOAD)
        assert "<script>" not in html.lower()
