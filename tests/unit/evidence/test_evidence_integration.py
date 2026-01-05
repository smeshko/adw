"""Tests for evidence gathering integration into orchestrator (Story ISS-010).

This module tests that evidence gathering is properly called during the
verify phase and that evidence is correctly copied to artifacts.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.evidence import EvidenceSummary, get_evidence_strategy
from adw.models.evidence import (
    CLIEvidenceSummary,
    EvidenceStrategy,
    MobileDeviceType,
    PlatformType,
    WebEvidenceSummary,
)


class TestGetEvidenceStrategy:
    """Tests for the get_evidence_strategy function."""

    def test_cli_platform_returns_terminal_output(self) -> None:
        """CLI platform should use terminal output strategy."""
        strategy = get_evidence_strategy(PlatformType.CLI)
        assert strategy == EvidenceStrategy.TERMINAL_OUTPUT

    def test_web_platform_returns_screenshot(self) -> None:
        """WEB platform should use screenshot strategy."""
        strategy = get_evidence_strategy(PlatformType.WEB)
        assert strategy == EvidenceStrategy.SCREENSHOT

    def test_mobile_platform_returns_screenshot(self) -> None:
        """MOBILE platform should use screenshot strategy."""
        strategy = get_evidence_strategy(PlatformType.MOBILE)
        assert strategy == EvidenceStrategy.SCREENSHOT

    def test_backend_platform_returns_api_capture(self) -> None:
        """BACKEND platform should use API capture strategy."""
        strategy = get_evidence_strategy(PlatformType.BACKEND)
        assert strategy == EvidenceStrategy.API_CAPTURE

    def test_unknown_platform_defaults_to_terminal(self) -> None:
        """UNKNOWN platform should default to terminal output."""
        strategy = get_evidence_strategy(PlatformType.UNKNOWN)
        assert strategy == EvidenceStrategy.TERMINAL_OUTPUT


class TestCLIEvidenceGathererIntegration:
    """Tests for CLI evidence gathering integration."""

    def test_cli_gatherer_should_gather_for_cli_platform(self) -> None:
        """CLI gatherer should return True for CLI platform."""
        from adw.evidence import CLIEvidenceGatherer

        gatherer = CLIEvidenceGatherer(
            project_root=Path("/tmp/project"),
            evidence_dir=Path("/tmp/evidence"),
        )

        assert gatherer.should_gather(PlatformType.CLI) is True

    def test_cli_gatherer_should_gather_for_unknown_platform(self) -> None:
        """CLI gatherer should return True for UNKNOWN platform (default)."""
        from adw.evidence import CLIEvidenceGatherer

        gatherer = CLIEvidenceGatherer(
            project_root=Path("/tmp/project"),
            evidence_dir=Path("/tmp/evidence"),
        )

        assert gatherer.should_gather(PlatformType.UNKNOWN) is True

    def test_cli_gatherer_should_not_gather_for_web_platform(self) -> None:
        """CLI gatherer should return False for WEB platform."""
        from adw.evidence import CLIEvidenceGatherer

        gatherer = CLIEvidenceGatherer(
            project_root=Path("/tmp/project"),
            evidence_dir=Path("/tmp/evidence"),
        )

        assert gatherer.should_gather(PlatformType.WEB) is False


class TestOrchestratorEvidenceIntegration:
    """Tests for evidence gathering integration in orchestrator.

    These tests verify that _gather_evidence_after_verify is correctly
    integrated and calls the appropriate evidence gathering modules.
    """

    @pytest.fixture
    def mock_run_context(self) -> MagicMock:
        """Create a mock RunContext with platform set."""
        context = MagicMock()
        context.run_id = "01TEST00000000000000000001"
        context.platform = "cli"
        return context

    @pytest.fixture
    def orchestrator_with_mocks(self, tmp_path: Path) -> MagicMock:
        """Create a minimal orchestrator-like object for testing."""
        from adw.core.orchestrator import Orchestrator

        # Create mock dependencies
        mock_context_manager = MagicMock()
        mock_snapshot_manager = MagicMock()
        mock_artifact_manager = MagicMock()
        mock_run_dir_manager = MagicMock()
        mock_index_manager = MagicMock()

        # Create runs directory (orchestrator derives project_path from this)
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_dir_manager,
            index_manager=mock_index_manager,
        )

        return orchestrator

    def test_gather_evidence_creates_evidence_directory(
        self, orchestrator_with_mocks: MagicMock, mock_run_context: MagicMock
    ) -> None:
        """Evidence directory should be created during gathering."""
        orchestrator = orchestrator_with_mocks

        # Mock CLIEvidenceGatherer
        with patch("adw.core.orchestrator.CLIEvidenceGatherer") as mock_gatherer:
            mock_instance = MagicMock()
            mock_instance.should_gather.return_value = True
            mock_instance.gather.return_value = CLIEvidenceSummary(
                total_commands=0, passed=0, failed=0, results=[]
            )
            mock_gatherer.return_value = mock_instance

            # Run evidence gathering
            orchestrator._gather_evidence_after_verify(mock_run_context)

            # Check evidence directory was created
            evidence_dir = (
                orchestrator.runs_dir / mock_run_context.run_id / "evidence"
            )
            assert evidence_dir.exists()

    def test_gather_evidence_calls_cli_gatherer_for_cli_platform(
        self, orchestrator_with_mocks: MagicMock, mock_run_context: MagicMock
    ) -> None:
        """CLI gatherer should be called for CLI platform."""
        orchestrator = orchestrator_with_mocks
        mock_run_context.platform = "cli"

        with patch("adw.core.orchestrator.CLIEvidenceGatherer") as mock_gatherer:
            mock_instance = MagicMock()
            mock_instance.should_gather.return_value = True
            mock_instance.gather.return_value = CLIEvidenceSummary(
                total_commands=0, passed=0, failed=0, results=[]
            )
            mock_gatherer.return_value = mock_instance

            orchestrator._gather_evidence_after_verify(mock_run_context)

            # Verify CLIEvidenceGatherer was instantiated
            mock_gatherer.assert_called_once()

    def test_gather_evidence_does_not_fail_run_on_error(
        self, orchestrator_with_mocks: MagicMock, mock_run_context: MagicMock
    ) -> None:
        """Evidence gathering errors should not fail the run."""
        orchestrator = orchestrator_with_mocks

        with patch("adw.core.orchestrator.CLIEvidenceGatherer") as mock_gatherer:
            mock_gatherer.side_effect = Exception("Gathering failed")

            # Should not raise
            summaries = orchestrator._gather_evidence_after_verify(mock_run_context)

            # Should return empty list on error
            assert summaries == []


class TestEvidenceManifestGeneration:
    """Tests for evidence manifest generation integration."""

    def test_generate_evidence_manifest_creates_file(self, tmp_path: Path) -> None:
        """Manifest generation should create manifest.json file."""
        from adw.evidence import generate_evidence_manifest

        # Set up evidence directory with some files
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "test.txt").write_text("test output")

        # Generate manifest without summaries (will scan directory)
        manifest = generate_evidence_manifest(
            run_id="01TEST00000000000000000001",
            platform="cli",
            evidence_directory=evidence_dir,
            summaries=None,
        )

        # Verify manifest was created
        manifest_file = evidence_dir / "manifest.json"
        assert manifest_file.exists()
        assert manifest.total_items >= 0


class TestRunContextPlatformField:
    """Tests for platform field in RunContext (Task 3)."""

    def test_run_context_has_platform_field(self) -> None:
        """RunContext should have platform field."""
        from datetime import UTC, datetime

        from adw.models import RunContext

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        # Platform should be None by default
        assert context.platform is None

    def test_run_context_platform_can_be_set(self) -> None:
        """RunContext platform field should be settable."""
        from datetime import UTC, datetime

        from adw.models import RunContext

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
            platform="cli",
        )

        assert context.platform == "cli"

    def test_run_context_platform_persists_to_json(self) -> None:
        """Platform field should be included in JSON serialization."""
        from datetime import UTC, datetime

        from adw.models import RunContext

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
            platform="web",
        )

        json_data = context.model_dump()
        assert "platform" in json_data
        assert json_data["platform"] == "web"
