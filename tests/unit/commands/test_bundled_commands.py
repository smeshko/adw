"""Tests for bundled default commands.

Verifies that bundled commands resolve, and that each bundled phase ships a
valid config.yaml, a prompt.md and well-formed instructions.xml files.
"""

import xml.etree.ElementTree as ET
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from adw.commands import CommandResolver
from adw.commands.loader import get_config_class
from adw.core.constants import PHASE_SEQUENCE


class TestBundledCommands:
    """Test bundled default commands."""

    def test_resolve_bundled_plan(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled plan command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("plan")

        assert result.name == "plan"
        assert result.tier == "bundled"

    def test_resolve_bundled_build(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled build command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("build")

        assert result.name == "build"
        assert result.tier == "bundled"

    def test_resolve_bundled_ship(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled ship command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("ship")

        assert result.name == "ship"
        assert result.tier == "bundled"


@pytest.mark.parametrize("phase", PHASE_SEQUENCE)
def test_bundled_phase_files_are_well_formed(phase: str) -> None:
    """A bundled phase's config validates, its prompt exists and its XML parses."""
    phase_dir = Path(str(files("adw") / "defaults" / "commands" / phase))

    data = yaml.safe_load((phase_dir / "config.yaml").read_text()) or {}
    get_config_class(phase).model_validate(data)

    assert (phase_dir / "prompt.md").exists()

    instructions = sorted(phase_dir.rglob("instructions.xml"))
    assert instructions, f"no instructions.xml under {phase_dir}"
    for path in instructions:
        ET.parse(path)
