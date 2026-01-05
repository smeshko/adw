"""Unit tests for EvidenceValidator implementation.

Tests for the validator that checks evidence gathering results
and reports missing or failed evidence.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.models import RunContext
from adw.models.evidence import (
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceType,
)
from adw.validation.models import ValidationIssue, ValidationSource
from adw.validation.validators.evidence_validator import EvidenceValidator


@pytest.fixture
def mock_context() -> RunContext:
    """Create a mock RunContext for testing."""
    return RunContext(
        run_id="01HQ0000000000000000000000",
        feature_description="Test feature",
        current_phase="validation",
        phase_history=["plan", "build", "verify"],
        started_at=datetime.now(UTC),
        completed_at=None,
        status="running",
        artifacts={
            "verify": ["evidence_manifest.json"],
        },
        phase_tokens={},
        worktree_path=Path("/tmp/test"),
        use_worktree=False,
        branch_name=None,
    )


@pytest.fixture
def passing_manifest() -> EvidenceManifest:
    """Create a manifest with all passing evidence."""
    return EvidenceManifest(
        run_id="01HQ0000000000000000000000",
        platform="backend",
        evidence_directory="/tmp/evidence",
        total_items=3,
        passed=3,
        failed=0,
        errors=0,
        skipped=0,
        items=[
            EvidenceItem(
                name="api_users_get",
                type=EvidenceType.API,
                path="api_users_get.json",
                status=EvidenceStatus.PASS,
            ),
            EvidenceItem(
                name="api_auth_login",
                type=EvidenceType.API,
                path="api_auth_login.json",
                status=EvidenceStatus.PASS,
            ),
            EvidenceItem(
                name="api_products_list",
                type=EvidenceType.API,
                path="api_products_list.json",
                status=EvidenceStatus.PASS,
            ),
        ],
    )


@pytest.fixture
def failing_manifest() -> EvidenceManifest:
    """Create a manifest with failed evidence."""
    return EvidenceManifest(
        run_id="01HQ0000000000000000000000",
        platform="backend",
        evidence_directory="/tmp/evidence",
        total_items=3,
        passed=1,
        failed=2,
        errors=0,
        skipped=0,
        items=[
            EvidenceItem(
                name="api_users_get",
                type=EvidenceType.API,
                path="api_users_get.json",
                status=EvidenceStatus.PASS,
            ),
            EvidenceItem(
                name="api_auth_login",
                type=EvidenceType.API,
                path="api_auth_login.json",
                status=EvidenceStatus.FAIL,
                details={"error": "HTTP 500 response"},
            ),
            EvidenceItem(
                name="api_products_list",
                type=EvidenceType.API,
                path="api_products_list.json",
                status=EvidenceStatus.FAIL,
                details={"error": "Connection refused"},
            ),
        ],
    )


class TestEvidenceValidator:
    """Test cases for EvidenceValidator class."""

    def test_validate_all_evidence_passes(
        self,
        mock_context: RunContext,
        passing_manifest: EvidenceManifest,
    ) -> None:
        """Returns empty list when all evidence passes."""
        validator = EvidenceValidator()

        with patch.object(
            validator, "_load_manifest", return_value=passing_manifest
        ):
            issues = validator.validate(mock_context)

            assert issues == []

    def test_validate_failed_evidence(
        self,
        mock_context: RunContext,
        failing_manifest: EvidenceManifest,
    ) -> None:
        """Returns issues for failed evidence items."""
        validator = EvidenceValidator()

        with patch.object(
            validator, "_load_manifest", return_value=failing_manifest
        ):
            issues = validator.validate(mock_context)

            assert len(issues) == 2
            assert all(i.source == ValidationSource.EVIDENCE for i in issues)
            messages = [i.message for i in issues]
            assert any("api_auth_login" in m for m in messages)
            assert any("api_products_list" in m for m in messages)

    def test_validate_no_manifest(
        self, mock_context: RunContext
    ) -> None:
        """Returns issue when manifest not found."""
        validator = EvidenceValidator()

        with patch.object(
            validator, "_load_manifest", return_value=None
        ):
            issues = validator.validate(mock_context)

            assert len(issues) == 1
            assert issues[0].source == ValidationSource.EVIDENCE
            assert "manifest" in issues[0].message.lower()
            assert issues[0].severity in ["high", "medium"]

    def test_validate_skipped_evidence(
        self, mock_context: RunContext
    ) -> None:
        """Optionally reports skipped evidence."""
        manifest = EvidenceManifest(
            run_id="01HQ0000000000000000000000",
            platform="web",
            evidence_directory="/tmp/evidence",
            total_items=2,
            passed=1,
            failed=0,
            errors=0,
            skipped=1,
            items=[
                EvidenceItem(
                    name="screenshot_home",
                    type=EvidenceType.SCREENSHOT,
                    path="screenshot_home.png",
                    status=EvidenceStatus.PASS,
                ),
                EvidenceItem(
                    name="screenshot_dashboard",
                    type=EvidenceType.SCREENSHOT,
                    path="screenshot_dashboard.png",
                    status=EvidenceStatus.SKIPPED,
                ),
            ],
        )
        validator = EvidenceValidator(report_skipped=True)

        with patch.object(validator, "_load_manifest", return_value=manifest):
            issues = validator.validate(mock_context)

            # Should report skipped as info-level issue
            assert len(issues) >= 1
            skipped_issues = [i for i in issues if "skipped" in i.message.lower()]
            assert len(skipped_issues) >= 1

    def test_name_property(self) -> None:
        """EvidenceValidator returns correct name."""
        validator = EvidenceValidator()
        assert validator.name == "evidence"

    def test_validate_error_evidence(
        self, mock_context: RunContext
    ) -> None:
        """Returns issues for evidence with errors."""
        manifest = EvidenceManifest(
            run_id="01HQ0000000000000000000000",
            platform="cli",
            evidence_directory="/tmp/evidence",
            total_items=1,
            passed=0,
            failed=0,
            errors=1,
            skipped=0,
            items=[
                EvidenceItem(
                    name="cli_help",
                    type=EvidenceType.CLI,
                    path="cli_help.txt",
                    status=EvidenceStatus.ERROR,
                    details={"error": "Command not found"},
                ),
            ],
        )
        validator = EvidenceValidator()

        with patch.object(validator, "_load_manifest", return_value=manifest):
            issues = validator.validate(mock_context)

            assert len(issues) == 1
            assert issues[0].source == ValidationSource.EVIDENCE
            assert issues[0].severity == "high"
