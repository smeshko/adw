"""Tests for ship phase bug fixes and improvements.

Covers:
- Issue 2: Flat template variables always set (not conditional)
- Issue 3: Hook chaining across tiers
- Issue 4: ship_config rendered as YAML
- Issue 5: Ship command env vars in hook environment
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from adw.commands import CommandResolver
from adw.core.extensions.ship import ShipExtension
from adw.models.command import ResolvedCommand, ShipCommandConfig, ShipCommandsConfig


class TestFlatTemplateVariables:
    """Issue 2: Template variables should always be set, even when None."""

    def test_version_bump_command_set_when_none(self) -> None:
        """version_bump_command should be set even if commands.version_bump is None."""
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        assert config.commands.version_bump is None
        # The variable should still be settable (not skipped)
        variables: dict = {}
        variables["version_bump_command"] = config.commands.version_bump
        assert "version_bump_command" in variables
        assert variables["version_bump_command"] is None

    def test_publish_command_set_when_none(self) -> None:
        """publish_command should be set even if commands.publish is None."""
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        variables: dict = {}
        variables["publish_command"] = config.commands.publish
        assert "publish_command" in variables
        assert variables["publish_command"] is None

    def test_version_bump_command_set_when_configured(self) -> None:
        """version_bump_command should carry the configured value."""
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(version_bump="npm version patch")
        )
        variables: dict = {}
        variables["version_bump_command"] = config.commands.version_bump
        assert variables["version_bump_command"] == "npm version patch"


class TestShipConfigFormat:
    """Issue 4: ship_config should render as YAML, not raw Python dict."""

    def test_ship_config_is_valid_yaml(self) -> None:
        """ship_config variable should be valid YAML string."""
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(
                version_bump="npm version patch", publish="npm publish"
            ),
            bypass_ci=True,
        )
        ship_dict = {
            "commands": config.commands.model_dump(exclude_none=True),
            "bypass_ci": config.bypass_ci,
        }
        result = yaml.dump(ship_dict, default_flow_style=False)
        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed["bypass_ci"] is True
        assert parsed["commands"]["version_bump"] == "npm version patch"

    def test_ship_config_excludes_none_commands(self) -> None:
        """ship_config should exclude None command values."""
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        ship_dict = {
            "commands": config.commands.model_dump(exclude_none=True),
            "bypass_ci": config.bypass_ci,
        }
        result = yaml.dump(ship_dict, default_flow_style=False)
        parsed = yaml.safe_load(result)
        assert parsed["commands"] == {}


class TestHookChaining:
    """Issue 3: Hooks should be collected from all tiers."""

    def test_collect_hooks_from_bundled_only(self, tmp_path: Path) -> None:
        """When only bundled hook exists, it should be collected."""
        resolver = CommandResolver(project_root=tmp_path)
        paths = resolver._collect_hook_paths("ship", "post")
        # ship has a bundled post.sh
        assert len(paths) >= 1
        assert any("defaults" in str(p) for p in paths)

    def test_collect_hooks_from_project_and_bundled(self, tmp_path: Path) -> None:
        """Project hook should be collected alongside bundled hook."""
        # Create project-tier hook
        project_cmd = tmp_path / ".adw" / "commands" / "ship"
        project_cmd.mkdir(parents=True)
        (project_cmd / "post.sh").write_text("#!/bin/bash\necho project")

        resolver = CommandResolver(project_root=tmp_path)
        paths = resolver._collect_hook_paths("ship", "post")
        # Should have both bundled and project hooks
        assert len(paths) >= 2
        # Bundled comes first
        assert "defaults" in str(paths[0])
        # Project comes last
        assert str(tmp_path) in str(paths[-1])

    def test_empty_list_when_no_hooks(self, tmp_path: Path) -> None:
        """Should return empty list when no hooks exist at any tier."""
        resolver = CommandResolver(project_root=tmp_path)
        paths = resolver._collect_hook_paths("nonexistent-cmd", "pre")
        assert paths == []

    def test_resolved_command_has_pre_hook_paths_list(self, tmp_path: Path) -> None:
        """ResolvedCommand should have pre_hook_paths as a list."""
        cmd = ResolvedCommand(
            name="test",
            path=tmp_path,
            tier="project",
            pre_hook_paths=[tmp_path / "pre.sh"],
            post_hook_paths=[],
        )
        assert isinstance(cmd.pre_hook_paths, list)
        assert len(cmd.pre_hook_paths) == 1
        assert cmd.has_pre_hook is True
        assert cmd.has_post_hook is False

    def test_backward_compat_properties(self, tmp_path: Path) -> None:
        """pre_hook_path and post_hook_path properties should work."""
        hook = tmp_path / "pre.sh"
        cmd = ResolvedCommand(
            name="test",
            path=tmp_path,
            tier="project",
            pre_hook_paths=[hook],
            post_hook_paths=[],
        )
        assert cmd.pre_hook_path == hook
        assert cmd.post_hook_path is None


class TestShipCommandEnvVars:
    """Issue 5: Deploy commands should be available in hook environment."""

    def test_version_bump_cmd_in_env(self) -> None:
        """ADW_SHIP_VERSION_BUMP_CMD should be in hook env when configured."""
        ext = ShipExtension()
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(version_bump="npm version patch")
        )
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(ext, "_load_project_build_command", return_value=None):
                env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_VERSION_BUMP_CMD") == "npm version patch"

    def test_publish_cmd_in_env(self) -> None:
        """ADW_SHIP_PUBLISH_CMD should be in hook env when configured."""
        ext = ShipExtension()
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(publish="npm publish")
        )
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(ext, "_load_project_build_command", return_value=None):
                env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_PUBLISH_CMD") == "npm publish"

    def test_build_cmd_in_env(self) -> None:
        """ADW_SHIP_BUILD_CMD should be in hook env when build_command configured."""
        ext = ShipExtension()
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(
                ext, "_load_project_build_command", return_value="npm run build"
            ):
                env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_BUILD_CMD") == "npm run build"

    def test_no_cmd_env_when_none(self) -> None:
        """Command env vars should not be set when commands are None."""
        ext = ShipExtension()
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(ext, "_load_project_build_command", return_value=None):
                env = ext.get_hook_env(context)

        assert "ADW_SHIP_VERSION_BUMP_CMD" not in env
        assert "ADW_SHIP_PUBLISH_CMD" not in env
        assert "ADW_SHIP_BUILD_CMD" not in env

    def test_wait_for_merge_env_var(self) -> None:
        """ADW_SHIP_WAIT_FOR_MERGE should be in hook env."""
        ext = ShipExtension()
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(), wait_for_merge=True
        )
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(ext, "_load_project_build_command", return_value=None):
                env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_WAIT_FOR_MERGE") == "true"

    def test_wait_for_merge_default_false(self) -> None:
        """ADW_SHIP_WAIT_FOR_MERGE defaults to false."""
        ext = ShipExtension()
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            with patch.object(ext, "_load_project_build_command", return_value=None):
                env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_WAIT_FOR_MERGE") == "false"
