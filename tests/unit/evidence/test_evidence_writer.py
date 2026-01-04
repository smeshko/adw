"""Tests for API evidence file writer.

This module tests writing captured API evidence to files.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from adw.evidence import HTTPX_AVAILABLE

# Skip all tests in this module if httpx is not available
pytestmark = pytest.mark.skipif(
    not HTTPX_AVAILABLE,
    reason="httpx not installed - API evidence writer tests skipped",
)

from adw.evidence.evidence_writer import APIEvidenceWriter  # noqa: E402
from adw.models.evidence import (  # noqa: E402
    APIEvidenceResult,
    APIEvidenceSummary,
    APIRequest,
    APIResponse,
)


class TestAPIEvidenceWriter:
    """Tests for APIEvidenceWriter class."""

    def test_create_writer(self) -> None:
        """Test creating an evidence writer."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)
            assert writer.run_dir == run_dir

    def test_write_result_creates_directory(self) -> None:
        """Test that write_result creates evidence directory."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            result = APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost/health"),
                response=APIResponse(
                    status_code=200,
                    body={"status": "ok"},
                    duration_seconds=0.01,
                ),
                success=True,
            )

            writer.write_result(result)

            evidence_dir = run_dir / "evidence" / "api"
            assert evidence_dir.exists()
            assert evidence_dir.is_dir()

    def test_write_result_creates_json_file(self) -> None:
        """Test that write_result creates a JSON file for the endpoint."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            result = APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost/health"),
                response=APIResponse(
                    status_code=200,
                    body={"status": "ok"},
                    duration_seconds=0.01,
                ),
                success=True,
            )

            file_path = writer.write_result(result)

            assert file_path.exists()
            assert file_path.name == "health.json"

    def test_written_json_contains_request_response(self) -> None:
        """Test that written JSON contains full request/response details."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            result = APIEvidenceResult(
                endpoint_name="users",
                request=APIRequest(
                    method="POST",
                    url="http://localhost/users",
                    headers={"Content-Type": "application/json"},
                    body={"name": "test"},
                ),
                response=APIResponse(
                    status_code=201,
                    headers={"X-Request-Id": "abc123"},
                    body={"id": 1, "name": "test"},
                    duration_seconds=0.05,
                ),
                success=True,
            )

            file_path = writer.write_result(result)

            # Read and verify contents
            with open(file_path) as f:
                data = json.load(f)

            assert data["endpoint_name"] == "users"
            assert data["request"]["method"] == "POST"
            assert data["request"]["body"] == {"name": "test"}
            assert data["response"]["status_code"] == 201
            assert data["response"]["body"] == {"id": 1, "name": "test"}

    def test_write_summary_creates_file(self) -> None:
        """Test that write_summary creates summary.json file."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            summary = APIEvidenceSummary(
                base_url="http://localhost:8000",
                total_endpoints=2,
                successful=2,
                failed=0,
                status_mismatches=0,
                results=[
                    APIEvidenceResult(
                        endpoint_name="health",
                        request=APIRequest(method="GET", url="http://localhost/health"),
                        response=APIResponse(
                            status_code=200, body={}, duration_seconds=0.01
                        ),
                        success=True,
                    ),
                ],
            )

            file_path = writer.write_summary(summary)

            assert file_path.exists()
            assert file_path.name == "summary.json"

    def test_write_summary_contains_all_data(self) -> None:
        """Test that summary contains all expected data."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            summary = APIEvidenceSummary(
                base_url="http://localhost:8000",
                total_endpoints=3,
                successful=2,
                failed=1,
                status_mismatches=1,
                results=[],
            )

            file_path = writer.write_summary(summary)

            with open(file_path) as f:
                data = json.load(f)

            assert data["base_url"] == "http://localhost:8000"
            assert data["total_endpoints"] == 3
            assert data["successful"] == 2
            assert data["failed"] == 1
            assert data["status_mismatches"] == 1

    def test_sanitizes_endpoint_name_for_filename(self) -> None:
        """Test that endpoint names are sanitized for use as filenames."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            result = APIEvidenceResult(
                endpoint_name="api/users/create",  # Contains slashes
                request=APIRequest(method="GET", url="http://localhost/test"),
                response=APIResponse(status_code=200, body={}, duration_seconds=0.01),
                success=True,
            )

            file_path = writer.write_result(result)

            # Should sanitize slashes to underscores or similar
            assert "/" not in file_path.name
            assert file_path.exists()

    def test_get_evidence_dir_returns_path(self) -> None:
        """Test that get_evidence_dir returns the evidence directory path."""
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / ".adw" / "runs" / "run123"
            writer = APIEvidenceWriter(run_dir=run_dir)

            evidence_dir = writer.get_evidence_dir()

            assert evidence_dir == run_dir / "evidence" / "api"
