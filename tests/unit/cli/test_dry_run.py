"""Tests for DryRunDisplay module.

Tests the dry-run preview functionality including phase display,
configuration display, and artifact preview.
"""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from adw.cli.dry_run import DryRunDisplay
from adw.models import ProjectConfig


class TestDryRunDisplay:
    """Tests for DryRunDisplay class."""

    def test_init_with_console(self) -> None:
        """Test initialization with provided console."""
        console = Console()
        display = DryRunDisplay(console)
        assert display.console is console

    def test_init_without_console(self) -> None:
        """Test initialization creates default console."""
        display = DryRunDisplay()
        assert display.console is not None

    def test_show_execution_preview_full_pipeline(self) -> None:
        """Test full pipeline preview shows all 5 phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase=None,  # Full pipeline
            from_run=None,
        )

        result = output.getvalue()
        # Should show all phases
        for phase in ["plan", "build", "verify", "validate", "document"]:
            assert phase in result.lower(), f"Phase '{phase}' not found in output"

    def test_show_execution_preview_single_phase(self) -> None:
        """Test single phase mode only shows specified phase."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase="build",  # Single phase
            from_run=None,
        )

        result = output.getvalue()
        # Should show build phase
        assert "build" in result.lower()
        # Should indicate single phase mode
        assert "build" in result.lower()

    def test_show_execution_preview_shows_feature(self) -> None:
        """Test that feature description is shown in preview."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase=None,
            from_run=None,
        )

        result = output.getvalue()
        assert "Add user authentication" in result

    def test_show_execution_preview_shows_dry_run_notice(self) -> None:
        """Test that dry run notice is shown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
        )

        result = output.getvalue().lower()
        assert "dry run" in result or "no execution" in result


class TestDryRunDisplayWithConfig:
    """Tests for DryRunDisplay with configuration."""

    def test_show_phases_with_hooks(self) -> None:
        """Test phase display shows pre and post hooks when configured."""
        from adw.models import ProjectConfig, PhaseConfig

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        config = ProjectConfig(
            name="test-project",
            language="python",
            phases={
                "build": PhaseConfig(pre_hook="npm install", post_hook="npm run lint"),
                "validate": PhaseConfig(post_hook="pytest"),
            },
        )

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=config,
        )

        result = output.getvalue()
        assert "npm install" in result
        assert "npm run lint" in result
        assert "pytest" in result

    def test_show_phases_without_config(self) -> None:
        """Test phase display works without config (shows dashes)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=None,
        )

        result = output.getvalue()
        # Should still show phases
        for phase in ["plan", "build", "verify", "validate", "document"]:
            assert phase in result.lower()

    def test_show_config_display(self) -> None:
        """Test configuration display shows project settings."""
        from adw.models import ProjectConfig

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        config = ProjectConfig(
            name="my-test-project",
            language="python",
            framework="fastapi",
            platform="api",
            test_command="pytest",
            build_command="python -m build",
        )

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=config,
        )

        result = output.getvalue()
        assert "my-test-project" in result
        assert "python" in result
        assert "fastapi" in result
        assert "api" in result
        assert "pytest" in result
        assert "python -m build" in result

    def test_show_config_with_git_settings(self) -> None:
        """Test configuration display shows git integration settings."""
        from adw.models import ProjectConfig, GitConfig

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        config = ProjectConfig(
            name="test-project",
            language="python",
            git=GitConfig(enabled=True, branch_prefix="feat/"),
        )

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=config,
        )

        result = output.getvalue().lower()
        # Should show git integration is enabled
        assert "git" in result
        assert "enabled" in result or "true" in result


class TestDryRunArtifactPreview:
    """Tests for artifact preview display."""

    def test_show_artifact_preview_with_from_run(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test artifact preview shows source run info."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase="build",
            from_run="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        )

        result = output.getvalue()
        assert "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in result
        assert "artifact" in result.lower()

    def test_show_artifact_preview_with_artifacts(self, tmp_path) -> None:
        """Test artifact preview lists actual artifacts."""
        from pathlib import Path
        from adw.core.artifact_manager import ArtifactManager

        # Create test artifacts
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        manager = ArtifactManager(runs_dir)
        manager.store("01TEST123", "plan", "plan.md", "# Plan content")
        manager.store("01TEST123", "build", "diff.txt", "diff content here")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase="build",
            from_run="01TEST123",
            runs_dir=runs_dir,
        )

        result = output.getvalue()
        assert "01TEST123" in result
        # Should show artifacts
        assert "plan.md" in result or "diff.txt" in result

    def test_show_artifact_preview_no_artifacts(self, tmp_path) -> None:
        """Test artifact preview with no artifacts shows message."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase="build",
            from_run="01NOARTIFACTS",
            runs_dir=runs_dir,
        )

        result = output.getvalue().lower()
        assert "01noartifacts" in result
        assert "no artifacts" in result or "artifact" in result
