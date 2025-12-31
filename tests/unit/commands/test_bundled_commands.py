"""Tests for bundled default commands (Task 6).

Verifies that bundled commands are accessible and resolvable.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from adw.commands import CommandResolver


class TestBundledCommands:
    """Test bundled default commands."""

    @pytest.fixture
    def isolated_resolver(self, tmp_path: Path) -> CommandResolver:
        """Create a resolver with no project/user commands."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
        return resolver

    def test_bundled_plan_exists(self) -> None:
        """Bundled plan command should exist."""
        # Test by checking the file exists directly
        from importlib.resources import files

        plan_path = files("adw") / "defaults" / "commands" / "plan"
        # Check it exists (will raise if not)
        assert (Path(str(plan_path)) / "prompt.md").exists()

    def test_bundled_build_exists(self) -> None:
        """Bundled build command should exist."""
        from importlib.resources import files

        build_path = files("adw") / "defaults" / "commands" / "build"
        assert (Path(str(build_path)) / "prompt.md").exists()

    def test_bundled_verify_exists(self) -> None:
        """Bundled verify command should exist."""
        from importlib.resources import files

        verify_path = files("adw") / "defaults" / "commands" / "verify"
        assert (Path(str(verify_path)) / "prompt.md").exists()

    def test_bundled_validate_exists(self) -> None:
        """Bundled validate command should exist."""
        from importlib.resources import files

        validate_path = files("adw") / "defaults" / "commands" / "validate"
        assert (Path(str(validate_path)) / "prompt.md").exists()

    def test_bundled_document_exists(self) -> None:
        """Bundled document command should exist."""
        from importlib.resources import files

        document_path = files("adw") / "defaults" / "commands" / "document"
        assert (Path(str(document_path)) / "prompt.md").exists()

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
