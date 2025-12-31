"""Tests for ResolvedCommand model (Task 2).

Verifies the ResolvedCommand Pydantic model with correct fields and validation.
"""

from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError


class TestResolvedCommandModel:
    """Test the ResolvedCommand Pydantic model."""

    def test_resolved_command_importable(self) -> None:
        """ResolvedCommand should be importable from adw.models."""
        from adw.models import ResolvedCommand

        assert ResolvedCommand is not None

    def test_resolved_command_required_fields(self, tmp_path: Path) -> None:
        """ResolvedCommand should have required fields: name, path, tier."""
        from adw.models import ResolvedCommand

        # Create minimal command directory with prompt.md
        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")

        cmd = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="project",
        )

        assert cmd.name == "plan"
        assert cmd.path == command_dir
        assert cmd.tier == "project"

    def test_resolved_command_optional_fields_default_false(
        self, tmp_path: Path
    ) -> None:
        """Optional fields should default to False."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")

        cmd = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="bundled",
        )

        assert cmd.has_schema is False
        assert cmd.has_pre_hook is False
        assert cmd.has_post_hook is False

    def test_resolved_command_tier_literal(self, tmp_path: Path) -> None:
        """Tier should only accept project, user, or bundled."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")

        # Valid tiers
        for tier in ("project", "user", "bundled"):
            cmd = ResolvedCommand(name="plan", path=command_dir, tier=tier)  # type: ignore
            assert cmd.tier == tier

    def test_resolved_command_invalid_tier_rejected(self, tmp_path: Path) -> None:
        """Invalid tier values should be rejected."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")

        with pytest.raises(ValidationError):
            ResolvedCommand(
                name="plan",
                path=command_dir,
                tier="invalid",  # type: ignore
            )

    def test_resolved_command_detects_schema(self, tmp_path: Path) -> None:
        """ResolvedCommand should detect schema.json presence."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")
        (command_dir / "schema.json").write_text("{}")

        cmd = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="project",
            has_schema=True,
        )

        assert cmd.has_schema is True

    def test_resolved_command_detects_hooks(self, tmp_path: Path) -> None:
        """ResolvedCommand should detect hook presence."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")
        (command_dir / "pre.sh").write_text("#!/bin/bash")
        (command_dir / "post.sh").write_text("#!/bin/bash")

        cmd = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="project",
            has_pre_hook=True,
            has_post_hook=True,
        )

        assert cmd.has_pre_hook is True
        assert cmd.has_post_hook is True

    def test_resolved_command_path_must_be_path_object(self, tmp_path: Path) -> None:
        """Path should be a Path object, not a string."""
        from adw.models import ResolvedCommand

        command_dir = tmp_path / "plan"
        command_dir.mkdir()
        (command_dir / "prompt.md").write_text("# Plan Phase")

        # Should accept Path
        cmd = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="project",
        )
        assert isinstance(cmd.path, Path)

        # Should coerce string to Path
        cmd2 = ResolvedCommand(
            name="plan",
            path=str(command_dir),  # type: ignore
            tier="project",
        )
        assert isinstance(cmd2.path, Path)
