"""Tests for the ship extension, ship config and hook chaining.

Covers:
- Hook chaining across tiers
- ship_config rendered as YAML
- Ship command env vars in hook environment
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from ulid import ULID

from adw.commands.resolver import CommandResolver
from adw.core.extensions.ship import ShipExtension
from adw.models import PhaseResult, RunContext
from adw.models.command import ResolvedCommand, ShipCommandConfig, ShipCommandsConfig
from adw.models.config import GitConfig


class TestShipConfigFormat:
    """ship_config should render as YAML, not raw Python dict."""

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
    """Hooks should be collected from all tiers."""

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

    def test_resolved_command_pre_hook_paths_is_list(self, tmp_path: Path) -> None:
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
        assert cmd.pre_hook_path is not None
        assert cmd.post_hook_path is None

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
    """Deploy commands should be available in hook environment."""

    def test_version_bump_cmd_in_env(self) -> None:
        """ADW_SHIP_VERSION_BUMP_CMD should be in hook env when configured."""
        ext = ShipExtension(GitConfig())
        config = ShipCommandConfig(
            commands=ShipCommandsConfig(version_bump="npm version patch")
        )
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_VERSION_BUMP_CMD") == "npm version patch"

    def test_publish_cmd_in_env(self) -> None:
        """ADW_SHIP_PUBLISH_CMD should be in hook env when configured."""
        ext = ShipExtension(GitConfig())
        config = ShipCommandConfig(commands=ShipCommandsConfig(publish="npm publish"))
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_PUBLISH_CMD") == "npm publish"

    def test_build_cmd_in_env(self) -> None:
        """ADW_SHIP_BUILD_CMD should be in hook env when build_command configured."""
        ext = ShipExtension(GitConfig(), build_command="npm run build")
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_BUILD_CMD") == "npm run build"

    def test_build_cmd_in_env_without_ship_config(self, tmp_path: Path) -> None:
        """ADW_SHIP_BUILD_CMD is exported when the project has no ship config (B3)."""
        ext = ShipExtension(
            GitConfig(), project_root=tmp_path, build_command="echo built"
        )

        env = ext.get_hook_env(MagicMock())

        assert env == {"ADW_SHIP_BUILD_CMD": "echo built"}

    def test_no_cmd_env_when_none(self) -> None:
        """Command env vars should not be set when commands are None."""
        ext = ShipExtension(GitConfig())
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert "ADW_SHIP_VERSION_BUMP_CMD" not in env
        assert "ADW_SHIP_PUBLISH_CMD" not in env
        assert "ADW_SHIP_BUILD_CMD" not in env

    def test_wait_for_merge_env_var(self) -> None:
        """ADW_SHIP_WAIT_FOR_MERGE should be in hook env."""
        ext = ShipExtension(GitConfig())
        config = ShipCommandConfig(commands=ShipCommandsConfig(), wait_for_merge=True)
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_WAIT_FOR_MERGE") == "true"

    def test_wait_for_merge_default_false(self) -> None:
        """ADW_SHIP_WAIT_FOR_MERGE defaults to false."""
        ext = ShipExtension(GitConfig())
        config = ShipCommandConfig(commands=ShipCommandsConfig())
        context = MagicMock()

        with patch.object(ext, "_load_ship_config", return_value=config):
            env = ext.get_hook_env(context)

        assert env.get("ADW_SHIP_WAIT_FOR_MERGE") == "false"


class TestShipPostMergeBaseBranch:
    """Post-merge checkout falls back to the configured base branch."""

    def test_empty_merge_record_base_uses_git_config(self, tmp_path: Path) -> None:
        """A blank base_branch in merge_record.json uses git_config.base_branch."""
        run_id = str(ULID())
        worktree = tmp_path / "trees" / run_id
        record_dir = worktree / ".adw" / "runs" / run_id / "artifacts" / "ship"
        record_dir.mkdir(parents=True)
        (record_dir / "merge_record.json").write_text(
            json.dumps({"merged": True, "base_branch": ""})
        )
        context = RunContext(
            run_id=run_id,
            feature_description="test",
            current_phase="ship",
            started_at=datetime.now(),
            use_worktree=True,
            worktree_path=worktree,
            branch_name="feature/test",
        )
        ext = ShipExtension(GitConfig(base_branch="develop"), project_root=tmp_path)

        with (
            patch("adw.worktree.manager.WorktreeManager"),
            patch("adw.core.extensions.ship.git") as mock_run,
        ):
            ext.on_complete(context, MagicMock(spec=PhaseResult))

        argvs = [c.args for c in mock_run.call_args_list]
        assert ("checkout", "develop") in argvs
        assert ("pull", "origin", "develop") in argvs
