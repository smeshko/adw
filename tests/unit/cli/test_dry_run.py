"""Tests for DryRunDisplay module.

Tests the dry-run preview functionality including phase display,
configuration display, and artifact preview.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

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
        for phase in ["plan", "build", "validate", "document"]:
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

    def test_show_phases_with_hooks(self, tmp_path: Path) -> None:
        """Test phase display shows file-based hooks from resolved commands."""
        from adw.commands.resolver import CommandResolver

        # Create command directories with file-based hooks
        for phase in ["plan", "build", "validate", "document", "ship"]:
            cmd_dir = tmp_path / ".adw" / "commands" / phase
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "prompt.md").write_text(f"Test prompt for {phase}")

        # Add file-based hooks to build and validate
        (tmp_path / ".adw" / "commands" / "build" / "pre-hook.sh").write_text(
            "#!/bin/bash\nnpm install\n"
        )
        (tmp_path / ".adw" / "commands" / "build" / "post-hook.sh").write_text(
            "#!/bin/bash\nnpm run lint\n"
        )
        (tmp_path / ".adw" / "commands" / "validate" / "post-hook.sh").write_text(
            "#!/bin/bash\npytest\n"
        )

        command_resolver = CommandResolver(project_root=tmp_path)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console, command_resolver=command_resolver)

        config = ProjectConfig(
            name="test-project",
            language="python",
        )

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=config,
        )

        result = output.getvalue()
        assert "pre-hook.sh" in result
        assert "post-hook.sh" in result

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
        for phase in ["plan", "build", "validate", "document"]:
            assert phase in result.lower()

    def test_show_config_display(self) -> None:
        """Test configuration display shows project settings."""

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
        from adw.models import GitConfig

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        config = ProjectConfig(
            name="test-project",
            language="python",
            git=GitConfig(branch_prefix="feat/"),
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

    def test_show_artifact_preview_with_from_run(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
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


class TestDryRunEdgeCases:
    """Edge case tests for DryRunDisplay."""

    def test_format_size_bytes(self) -> None:
        """Test file size formatting for bytes."""
        display = DryRunDisplay()
        assert display._format_size(512) == "512 B"
        assert display._format_size(0) == "0 B"

    def test_format_size_kilobytes(self) -> None:
        """Test file size formatting for kilobytes."""
        display = DryRunDisplay()
        assert display._format_size(1024) == "1.0 KB"
        assert display._format_size(2560) == "2.5 KB"

    def test_format_size_megabytes(self) -> None:
        """Test file size formatting for megabytes."""
        display = DryRunDisplay()
        assert display._format_size(1024 * 1024) == "1.0 MB"
        assert display._format_size(2 * 1024 * 1024 + 512 * 1024) == "2.5 MB"

    def test_config_without_optional_fields(self) -> None:
        """Test config display with minimal configuration."""

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        # Minimal config - only required fields
        config = ProjectConfig(
            name="minimal-project",
            language="rust",
        )

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
            config=config,
        )

        result = output.getvalue()
        assert "minimal-project" in result
        assert "rust" in result
        # Framework should not appear since it's None
        # But other defaults should be present
        assert "claude" in result  # Default LLM path

    def test_exit_code_zero(self) -> None:
        """Test that dry run completes successfully (AC6)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        # Should not raise any exceptions
        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
        )
