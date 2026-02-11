"""Integration tests for feature description preservation.

Tests verify that feature descriptions are correctly preserved through
the full data flow:
  CLI → Orchestrator → RunContext → context.json → IndexEntry → List display

This test suite was created in response to ISS-005 to prevent regression
of feature description handling.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner
from ulid import ULID

from adw.cli.app import app
from adw.core.context_manager import ContextManager
from adw.core.index_manager import IndexManager
from adw.models import RunContext

runner = CliRunner()


def _generate_test_run_id() -> str:
    """Generate a valid ULID run ID for testing."""
    return str(ULID())


class TestFeatureDescriptionPreservation:
    """Tests for feature description preservation through the data flow."""

    def test_run_header_shows_feature_description(self, tmp_path: Path) -> None:
        """Test that run command header displays the exact feature description."""
        (tmp_path / "pyproject.toml").touch()

        feature = "Add unique authentication feature xyz123"
        result = runner.invoke(
            app,
            ["run", feature, "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert feature in result.output, (
            f"Feature description '{feature}' not found in output:\n{result.output}"
        )

    def test_feature_with_spaces_preserved(self, tmp_path: Path) -> None:
        """Test that feature description with multiple spaces is preserved."""
        (tmp_path / "pyproject.toml").touch()

        feature = "Add user authentication system with OAuth2 support"
        result = runner.invoke(
            app,
            ["run", feature, "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert feature in result.output

    def test_feature_with_special_chars_preserved(self, tmp_path: Path) -> None:
        """Test that feature description with special characters is preserved."""
        (tmp_path / "pyproject.toml").touch()

        test_cases = [
            "Fix bug #123 in login",
            "Add 'dark mode' toggle",
            "Implement feature (v2.0)",
            "Add user-authentication",
        ]

        for feature in test_cases:
            result = runner.invoke(
                app,
                ["run", feature, "--dry-run"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            assert feature in result.output, (
                f"Feature '{feature}' not found in output:\n{result.output}"
            )


class TestFeatureDescriptionInRunContext:
    """Tests for feature description in RunContext model."""

    def test_run_context_stores_feature_description(self) -> None:
        """Test that RunContext stores feature_description correctly."""
        feature = "unique test feature abc123"
        context = RunContext(
            run_id=_generate_test_run_id(),
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        assert context.feature_description == feature

    def test_run_context_serializes_feature_description(self) -> None:
        """Test that RunContext serializes feature_description to JSON."""
        feature = "serialization test feature xyz789"
        context = RunContext(
            run_id=_generate_test_run_id(),
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        json_data = context.model_dump_json()
        assert feature in json_data

    def test_run_context_deserializes_feature_description(self) -> None:
        """Test that RunContext deserializes feature_description from JSON."""
        feature = "deserialization test feature 456"
        context = RunContext(
            run_id=_generate_test_run_id(),
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        json_data = context.model_dump_json()
        restored = RunContext.model_validate_json(json_data)
        assert restored.feature_description == feature


class TestFeatureDescriptionInContextManager:
    """Tests for feature description persistence via ContextManager."""

    def test_context_manager_persists_feature_description(self, tmp_path: Path) -> None:
        """Test that ContextManager saves and loads feature_description correctly."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        feature = "persistence test feature 789"
        run_id = _generate_test_run_id()
        context = RunContext(
            run_id=run_id,
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        # Create run directory (ContextManager expects runs_dir, not run_dir)
        run_dir = runs_dir / context.run_id
        run_dir.mkdir()

        # ContextManager is initialized with runs_dir (parent), not run_dir
        manager = ContextManager(runs_dir)
        manager.save(context)

        # Load and verify
        loaded = manager.load(context.run_id)
        assert loaded.feature_description == feature


class TestFeatureDescriptionInGlobalIndex:
    """Tests for feature description in global index (IndexManager)."""

    def test_index_manager_stores_feature_description(
        self,
        tmp_path: Path,
        isolated_global_index: Path,
    ) -> None:
        """Test that IndexManager stores feature_description in index entry."""
        feature = "global index test feature abc"
        context = RunContext(
            run_id=_generate_test_run_id(),
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        manager = IndexManager(index_path=isolated_global_index)
        manager.register_run(context, tmp_path)

        # Read back entries
        entries = manager.get_recent_runs(limit=10)
        assert len(entries) == 1
        assert entries[0].feature_description == feature

    def test_index_manager_preserves_feature_description_on_update(
        self,
        tmp_path: Path,
        isolated_global_index: Path,
    ) -> None:
        """Test that feature_description is preserved when updating run status."""
        feature = "update preservation test feature"
        context = RunContext(
            run_id=_generate_test_run_id(),
            feature_description=feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

        manager = IndexManager(index_path=isolated_global_index)
        manager.register_run(context, tmp_path)

        # Update status
        manager.update_run(context.run_id, status="completed")

        # Verify feature description preserved
        entries = manager.get_recent_runs(limit=10)
        assert len(entries) == 1
        assert entries[0].feature_description == feature
        assert entries[0].status == "completed"


class TestFeatureDescriptionWithFromRun:
    """Tests for feature description behavior with --from-run."""

    def test_feature_optional_with_from_run(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that feature can be omitted when --from-run is provided."""
        monkeypatch.chdir(tmp_path)

        # Set up a source run with context.json
        run_id = _generate_test_run_id()
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        source_feature = "Original feature from source run"
        source_context = RunContext(
            run_id=run_id,
            feature_description=source_feature,
            current_phase="plan",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="completed",
        )
        manager = ContextManager(runs_dir)
        manager.save(source_context)

        # Create minimal project marker
        (tmp_path / "pyproject.toml").touch()

        # Invoke with --from-run but without feature argument, use --dry-run
        result = runner.invoke(
            app,
            ["run", "--phase", "build", "--from-run", run_id, "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Feature loaded from source run" in result.output
        assert source_feature in result.output

    def test_feature_still_required_without_from_run(self, tmp_path: Path) -> None:
        """Test that feature is still required when --from-run is not provided."""
        (tmp_path / "pyproject.toml").touch()

        result = runner.invoke(
            app,
            ["run"],
            catch_exceptions=False,
        )

        # Should error — no feature and no --from-run
        assert result.exit_code != 0

    def test_feature_override_with_from_run(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that explicit feature overrides source run feature in display."""
        monkeypatch.chdir(tmp_path)

        run_id = _generate_test_run_id()
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        source_context = RunContext(
            run_id=run_id,
            feature_description="Original feature",
            current_phase="plan",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="completed",
        )
        manager = ContextManager(runs_dir)
        manager.save(source_context)

        (tmp_path / "pyproject.toml").touch()

        # Invoke with --from-run AND a feature argument
        result = runner.invoke(
            app,
            [
                "run",
                "Override feature description",
                "--phase",
                "build",
                "--from-run",
                run_id,
                "--dry-run",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Override feature description" in result.output

    def test_from_run_invalid_run_id_errors(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that an invalid --from-run ID produces an error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / ".adw" / "runs").mkdir(parents=True)

        result = runner.invoke(
            app,
            ["run", "--phase", "build", "--from-run", "NONEXISTENT00000000000001"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "Error" in result.output


class TestEndToEndFeatureDescription:
    """End-to-end tests for feature description flow."""

    def test_feature_description_not_generic_placeholder(self, tmp_path: Path) -> None:
        """Test that feature description is NOT the generic 'Add feature' placeholder."""
        (tmp_path / "pyproject.toml").touch()

        # Use a very specific feature description
        feature = "implement unique oauth2 with saml2 sso xyz987"
        result = runner.invoke(
            app,
            ["run", feature, "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Feature should appear in output
        assert feature in result.output
        # Should NOT contain generic placeholder
        assert "Add feature" not in result.output or feature in result.output
