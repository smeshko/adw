"""Tests for changed-count tab labels, is_changed flags, and indicator behaviour."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from adw.config.registry import ConfigRegistry
from adw.dashboard.dependencies import (
    get_index_manager,
    get_project_registry,
)
from adw.dashboard.routes import (
    build_complex_settings_context,
    build_settings_context,
    compute_changed_counts,
)
from adw.dashboard.server import create_dashboard_app

# ── Helpers ───────────────────────────────────────────────────────


def _make_mock_registry(projects: list[tuple[str, str]]) -> MagicMock:
    """Create a mock ProjectRegistryManager."""
    registry = MagicMock()
    mock_projects = []
    for path, name in projects:
        p = MagicMock()
        p.path = path
        p.name = name
        mock_projects.append(p)
    registry.get_all.return_value = mock_projects
    return registry


def _make_mock_index_manager() -> MagicMock:
    """Create a mock IndexManager."""
    mgr = MagicMock()
    mgr.get_recent_runs.return_value = []
    return mgr


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def default_project_dir(tmp_path: Path) -> Path:
    """Project directory with all-default configuration."""
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    config = {
        "name": "test-app",
        "language": "python",
        "platform": "cli",
        "test_command": "pytest",
        "git": {
            "branch_prefix": "feature/",
            "skip_hooks": False,
            "base_branch": "main",
        },
        "worktree": {
            "enabled": True,
            "base_dir": "trees",
            "port_range": {
                "backend_start": 9100,
                "frontend_start": 9200,
            },
            "max_concurrent": 15,
        },
        "llm": {
            "path": "claude",
            "timeout_seconds": 300,
            "retry": {
                "max_retries": 3,
                "base_delay_seconds": 1.0,
                "max_delay_seconds": 60.0,
                "multiplier": 2.0,
            },
        },
    }
    (adw_dir / "project.yaml").write_text(yaml.dump(config, sort_keys=False))
    return tmp_path


@pytest.fixture()
def changed_project_dir(tmp_path: Path) -> Path:
    """Project directory with non-default values in git section."""
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    config = {
        "name": "test-app",
        "language": "python",
        "platform": "cli",
        "test_command": "pytest",
        "git": {
            "branch_prefix": "feat/",  # Changed from default "feature/"
            "skip_hooks": True,  # Changed from default False
            "base_branch": "main",
        },
        "worktree": {
            "enabled": True,
            "base_dir": "trees",
            "port_range": {
                "backend_start": 9100,
                "frontend_start": 9200,
            },
            "max_concurrent": 15,
        },
        "llm": {
            "path": "claude",
            "timeout_seconds": 300,
            "retry": {
                "max_retries": 3,
                "base_delay_seconds": 1.0,
                "max_delay_seconds": 60.0,
                "multiplier": 2.0,
            },
        },
        "task_manager": {
            "type": "linear",
            "team_key": "ADW",
        },
    }
    (adw_dir / "project.yaml").write_text(yaml.dump(config, sort_keys=False))
    return tmp_path


@pytest.fixture()
def default_client(default_project_dir: Path) -> Generator[TestClient]:
    """Client with all-default project config."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([(str(default_project_dir), "test-app")])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def changed_client(changed_project_dir: Path) -> Generator[TestClient]:
    """Client with non-default values (git, task_manager, security)."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([(str(changed_project_dir), "test-app")])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Unit tests: compute_changed_counts ────────────────────────────


class TestComputeChangedCounts:
    """Tests for the compute_changed_counts helper."""

    def test_empty_sections(self) -> None:
        """No settings → all counts are 0."""
        tm_ctx = {
            "type": "none",
            "team_key": "",
            "sync_comments": False,
            "auto_close": False,
            "labels_enabled": True,
            "label_prefix": "adw:",
        }
        sec_ctx: dict[str, list[str]] = {
            "blocked_commands": [],
            "blocked_env_files": [],
        }
        result = compute_changed_counts({}, tm_ctx, sec_ctx)
        assert result["task_manager"] == 0
        assert result["security"] == 0

    def test_sections_with_changed_fields(self) -> None:
        """Fields marked is_changed should be counted."""
        sections = {
            "git": [
                {"name": "branch_prefix", "is_changed": True},
                {"name": "skip_hooks", "is_changed": False},
                {"name": "base_branch", "is_changed": True},
            ],
            "project": [
                {"name": "language", "is_changed": False},
            ],
        }
        tm_ctx = {
            "type": "none",
            "team_key": "",
            "sync_comments": False,
            "auto_close": False,
            "labels_enabled": True,
            "label_prefix": "adw:",
        }
        sec_ctx: dict[str, list[str]] = {
            "blocked_commands": [],
            "blocked_env_files": [],
        }
        result = compute_changed_counts(sections, tm_ctx, sec_ctx)
        assert result["git"] == 2
        assert result["project"] == 0

    def test_task_manager_changed(self) -> None:
        """Task manager fields differing from defaults are counted."""
        tm_ctx = {
            "type": "linear",  # differs from "none"
            "team_key": "ADW",  # differs from ""
            "sync_comments": False,
            "auto_close": False,
            "labels_enabled": True,
            "label_prefix": "adw:",
        }
        sec_ctx: dict[str, list[str]] = {
            "blocked_commands": [],
            "blocked_env_files": [],
        }
        result = compute_changed_counts({}, tm_ctx, sec_ctx)
        assert result["task_manager"] == 2

    def test_security_changed(self) -> None:
        """Non-empty blocked lists count as changed."""
        tm_ctx = {
            "type": "none",
            "team_key": "",
            "sync_comments": False,
            "auto_close": False,
            "labels_enabled": True,
            "label_prefix": "adw:",
        }
        sec_ctx = {
            "blocked_commands": ["rm -rf /"],
            "blocked_env_files": [".env"],
        }
        result = compute_changed_counts({}, tm_ctx, sec_ctx)
        assert result["security"] == 2

    def test_security_one_list_changed(self) -> None:
        """Only one non-empty list → count is 1."""
        tm_ctx = {
            "type": "none",
            "team_key": "",
            "sync_comments": False,
            "auto_close": False,
            "labels_enabled": True,
            "label_prefix": "adw:",
        }
        sec_ctx = {
            "blocked_commands": ["rm -rf /"],
            "blocked_env_files": [],
        }
        result = compute_changed_counts({}, tm_ctx, sec_ctx)
        assert result["security"] == 1


# ── Unit tests: build_settings_context is_changed flags ───────────


class TestIsChangedFlags:
    """Verify that build_settings_context sets is_changed correctly."""

    def test_default_config_no_changed(self) -> None:
        """With default values, no field should be marked changed."""
        from adw.config.loader import ConfigLoader

        # Use a real loader with defaults
        mock_config = MagicMock()
        mock_config.name = "test-app"
        mock_config.language = "python"
        mock_config.framework = None
        mock_config.platform = "cli"
        mock_config.test_command = "pytest"
        mock_config.build_command = None

        mock_config.git = MagicMock()
        mock_config.git.branch_prefix = "feature/"
        mock_config.git.skip_hooks = False
        mock_config.git.base_branch = "main"

        registry = ConfigRegistry()
        result = build_settings_context(mock_config, registry)

        # Git section: branch_prefix="feature/" is the default → not changed
        git_settings = result.get("git", [])
        branch_prefix = next(
            (s for s in git_settings if s["name"] == "branch_prefix"), None
        )
        if branch_prefix:
            assert branch_prefix["is_changed"] is False

    def test_changed_branch_prefix(self) -> None:
        """Non-default branch_prefix should be marked changed."""
        mock_config = MagicMock()
        mock_config.name = "test-app"
        mock_config.language = "python"
        mock_config.framework = None
        mock_config.platform = "cli"
        mock_config.test_command = "pytest"
        mock_config.build_command = None

        mock_config.git = MagicMock()
        mock_config.git.branch_prefix = "feat/"  # Non-default
        mock_config.git.skip_hooks = False
        mock_config.git.base_branch = "main"

        registry = ConfigRegistry()
        result = build_settings_context(mock_config, registry)

        git_settings = result.get("git", [])
        branch_prefix = next(
            (s for s in git_settings if s["name"] == "branch_prefix"), None
        )
        if branch_prefix:
            assert branch_prefix["is_changed"] is True

    def test_none_config_no_changed(self) -> None:
        """With no config, no field should be marked changed."""
        registry = ConfigRegistry()
        result = build_settings_context(None, registry)

        for section_settings in result.values():
            for setting in section_settings:
                assert setting["is_changed"] is False


# ── Integration tests: changed-count tab badges in HTML ──────────


class TestTabBadgesInHTML:
    """Test that rendered HTML contains changed-count badges."""

    def test_git_badge_count_matches_changed(
        self, default_client: TestClient
    ) -> None:
        """Git tab badge count reflects actual changed fields.

        Even with 'default' config, base_branch='main' differs from
        the registry default of None, so 1 changed field is expected.
        """
        import re

        resp = default_client.get(
            "/settings?project=test-app",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        html = resp.text
        # base_branch is "main" vs default None → 1 changed field
        git_tab = re.search(r'>Git(?:\s*<span[^>]*>(\d+)</span>)?</a>', html)
        assert git_tab is not None
        assert git_tab.group(1) == "1"

    def test_badges_when_changed(
        self, changed_client: TestClient
    ) -> None:
        """With non-default config, tabs should show count badges."""
        resp = changed_client.get(
            "/settings?project=test-app",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        html = resp.text
        # Git section has branch_prefix changed → badge should exist
        assert 'badge badge-sm badge-ghost' in html

    def test_git_tab_shows_count(
        self, changed_client: TestClient
    ) -> None:
        """Git tab should show the number of changed fields."""
        resp = changed_client.get(
            "/settings?project=test-app",
            headers={"HX-Request": "true"},
        )
        html = resp.text
        # The badge should be inside the Git tab link
        assert "Git" in html
        # branch_prefix and skip_hooks are changed → expect count
        assert 'badge badge-sm badge-ghost' in html


# ── Integration tests: indicators and reset buttons in HTML ──────


class TestIndicatorsInHTML:
    """Test that rendered HTML contains indicator dots and reset buttons."""

    def test_accent_dot_present_when_changed(
        self, changed_client: TestClient
    ) -> None:
        """Changed field should show accent dot (not hidden)."""
        resp = changed_client.get(
            "/partials/settings-content?tab=git&project=test-app",
        )
        assert resp.status_code == 200
        html = resp.text
        # branch_prefix is changed → dot should NOT have 'hidden' class
        assert 'id="dot-branch_prefix"' in html
        # The dot for branch_prefix should not be hidden
        assert 'id="dot-branch_prefix" title="Modified from default"></span>' in html

    def test_accent_dot_hidden_when_default(
        self, default_client: TestClient
    ) -> None:
        """Default field should have hidden accent dot."""
        resp = default_client.get(
            "/partials/settings-content?tab=git&project=test-app",
        )
        assert resp.status_code == 200
        html = resp.text
        # branch_prefix is at default → dot should be hidden
        assert 'hidden" id="dot-branch_prefix"' in html

    def test_reset_button_present(
        self, changed_client: TestClient
    ) -> None:
        """Changed field should have a visible reset button."""
        resp = changed_client.get(
            "/partials/settings-content?tab=git&project=test-app",
        )
        assert resp.status_code == 200
        html = resp.text
        assert 'id="reset-branch_prefix"' in html

    def test_reset_button_hidden_when_default(
        self, default_client: TestClient
    ) -> None:
        """Default field should have a hidden reset button."""
        resp = default_client.get(
            "/partials/settings-content?tab=git&project=test-app",
        )
        assert resp.status_code == 200
        html = resp.text
        assert 'hidden" id="reset-branch_prefix"' in html

    def test_default_hint_always_shown(
        self, default_client: TestClient
    ) -> None:
        """Default hint should be shown even when value matches default."""
        resp = default_client.get(
            "/partials/settings-content?tab=git&project=test-app",
        )
        assert resp.status_code == 200
        html = resp.text
        assert "Default: feature/" in html


# ── Integration tests: task_manager and security changed counts ──


class TestComplexSectionCounts:
    """Test changed counts for task_manager and security sections."""

    def test_task_manager_type_changed(self) -> None:
        """task_manager.type != 'none' means changed."""
        mock_config = MagicMock()
        mock_config.task_manager = MagicMock()
        mock_config.task_manager.type = "linear"
        mock_config.task_manager.team_key = ""
        mock_config.task_manager.sync_comments = False
        mock_config.task_manager.auto_close = False
        mock_config.task_manager.state_mapping = None
        mock_config.task_manager.labels = None
        mock_config.security = None

        complex_ctx = build_complex_settings_context(mock_config)
        counts = compute_changed_counts(
            {},
            complex_ctx["task_manager_context"],
            complex_ctx["security_context"],
        )
        assert counts["task_manager"] >= 1

    def test_security_blocked_commands_changed(self) -> None:
        """Non-empty blocked_commands means security is changed."""
        mock_config = MagicMock()
        mock_config.task_manager = None
        mock_config.security = MagicMock()
        bp = MagicMock()
        bp.pattern = "rm -rf /"
        mock_config.security.blocked_patterns = [bp]
        mock_config.security.blocked_env_files = []

        complex_ctx = build_complex_settings_context(mock_config)
        counts = compute_changed_counts(
            {},
            complex_ctx["task_manager_context"],
            complex_ctx["security_context"],
        )
        assert counts["security"] == 1

    def test_all_defaults_zero_counts(self) -> None:
        """When no config loaded, all complex section counts should be 0."""
        complex_ctx = build_complex_settings_context(None)
        counts = compute_changed_counts(
            {},
            complex_ctx["task_manager_context"],
            complex_ctx["security_context"],
        )
        assert counts["task_manager"] == 0
        assert counts["security"] == 0
