"""Tests for the settings page route and context building."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from adw.dashboard.dependencies import (
    get_index_manager,
    get_project_registry,
)
from adw.dashboard.routes import (
    _SETTINGS_TABS,
    _format_display_value,
    _humanize_field_name,
    _resolve_config_value,
    build_settings_context,
)
from adw.dashboard.server import create_dashboard_app

# ── Fixtures ───────────────────────────────────────────────────────


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


@pytest.fixture()
def empty_registry_client() -> Generator[TestClient]:
    """Client with no projects registered."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def populated_registry_client() -> Generator[TestClient]:
    """Client with projects registered."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([
        ("/projects/my-app", "my-app"),
        ("/projects/other", "other"),
    ])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_config() -> MagicMock:
    """Create a mock ProjectConfig."""
    config = MagicMock()
    config.name = "my-app"
    config.language = "python"
    config.framework = "fastapi"
    config.platform = "cli"
    config.test_command = "pytest"
    config.build_command = None
    config.git = MagicMock()
    config.git.branch_prefix = "feature/"
    config.git.skip_hooks = False
    config.git.base_branch = "main"
    config.llm = MagicMock()
    config.llm.path = "claude"
    config.llm.timeout_seconds = 300
    config.task_manager = MagicMock()
    config.task_manager.type = "linear"
    config.worktree = MagicMock()
    config.security = None
    return config


# ── Helper function tests ──────────────────────────────────────────


class TestHumanizeFieldName:
    """Tests for _humanize_field_name."""

    def test_single_word(self) -> None:
        assert _humanize_field_name("name") == "Name"

    def test_snake_case(self) -> None:
        assert _humanize_field_name("branch_prefix") == "Branch Prefix"

    def test_multiple_underscores(self) -> None:
        assert _humanize_field_name("max_delay_seconds") == "Max Delay Seconds"


class TestFormatDisplayValue:
    """Tests for _format_display_value."""

    def test_none(self) -> None:
        assert _format_display_value(None) == "\u2014"

    def test_string(self) -> None:
        assert _format_display_value("hello") == "hello"

    def test_bool_true(self) -> None:
        assert _format_display_value(True) == "true"

    def test_bool_false(self) -> None:
        assert _format_display_value(False) == "false"

    def test_number(self) -> None:
        assert _format_display_value(42) == "42"

    def test_empty_list(self) -> None:
        assert _format_display_value([]) == "[]"

    def test_list(self) -> None:
        assert _format_display_value(["a", "b"]) == "a, b"

    def test_empty_dict(self) -> None:
        assert _format_display_value({}) == "{}"

    def test_dict(self) -> None:
        assert _format_display_value({"k": "v"}) == "k: v"


class TestResolveConfigValue:
    """Tests for _resolve_config_value."""

    def test_project_section(self, mock_config: MagicMock) -> None:
        assert _resolve_config_value(mock_config, "project", "name") == "my-app"

    def test_git_section(self, mock_config: MagicMock) -> None:
        assert (
            _resolve_config_value(mock_config, "git", "branch_prefix") == "feature/"
        )

    def test_unknown_section(self, mock_config: MagicMock) -> None:
        assert _resolve_config_value(mock_config, "unknown", "field") is None

    def test_none_sub_config(self, mock_config: MagicMock) -> None:
        assert (
            _resolve_config_value(mock_config, "security", "blocked_patterns") is None
        )


# ── Context builder tests ──────────────────────────────────────────


class TestBuildSettingsContext:
    """Tests for build_settings_context."""

    def test_with_none_config(self) -> None:
        """Should return sections with settings even when no config loaded."""
        from adw.config.registry import ConfigRegistry

        registry = ConfigRegistry()
        result = build_settings_context(None, registry)

        assert isinstance(result, dict)
        assert "project" in result
        assert "git" in result
        assert len(result["project"]) > 0

    def test_with_config(self, mock_config: MagicMock) -> None:
        """Should resolve current values from config."""
        from adw.config.registry import ConfigRegistry

        registry = ConfigRegistry()
        result = build_settings_context(mock_config, registry)

        assert isinstance(result, dict)
        assert "project" in result

        # Find the 'name' setting
        name_setting = next(
            (s for s in result["project"] if s["name"] == "name"), None
        )
        assert name_setting is not None
        assert name_setting["current_value"] == "my-app"

    def test_settings_have_required_fields(self) -> None:
        """Each setting dict should have all required display fields."""
        from adw.config.registry import ConfigRegistry

        registry = ConfigRegistry()
        result = build_settings_context(None, registry)

        for _key, settings in result.items():
            for setting in settings:
                assert "name" in setting
                assert "label" in setting
                assert "display_value" in setting
                assert "display_default" in setting
                assert "description" in setting
                assert "type_hint" in setting
                assert "is_changed" in setting

    def test_phases_not_in_sections(self) -> None:
        """Phases tab should not be in the regular sections dict."""
        from adw.config.registry import ConfigRegistry

        registry = ConfigRegistry()
        result = build_settings_context(None, registry)
        assert "phases" not in result


# ── Route handler tests ──────────────────────────────────────────


class TestSettingsRoute:
    """Tests for GET /settings route."""

    def test_full_page_render(self, empty_registry_client: TestClient) -> None:
        """Without HX-Request header, returns full HTML page."""
        response = empty_registry_client.get("/settings")
        assert response.status_code == 200
        assert "Settings" in response.text
        assert "<!DOCTYPE html>" in response.text

    def test_htmx_partial_render(self, empty_registry_client: TestClient) -> None:
        """With HX-Request header, returns partial HTML."""
        response = empty_registry_client.get(
            "/settings", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "Settings" in response.text
        assert "<!DOCTYPE html>" not in response.text

    def test_no_projects_shows_empty_state(
        self, empty_registry_client: TestClient
    ) -> None:
        """When no projects registered, shows empty state message."""
        response = empty_registry_client.get(
            "/settings", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "No projects registered" in response.text

    def test_no_project_selected_shows_select_prompt(
        self, populated_registry_client: TestClient
    ) -> None:
        """Without project param, shows prompt to select a project."""
        response = populated_registry_client.get(
            "/settings", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "Select a project" in response.text

    def test_with_project_loads_config(
        self, populated_registry_client: TestClient
    ) -> None:
        """With project param, loads and displays config."""
        mock_cfg = MagicMock()
        mock_cfg.name = "my-app"
        mock_cfg.language = "python"
        mock_cfg.framework = None
        mock_cfg.platform = "cli"
        mock_cfg.test_command = "pytest"
        mock_cfg.build_command = None
        mock_cfg.git = MagicMock()
        mock_cfg.llm = MagicMock()
        mock_cfg.task_manager = MagicMock()
        mock_cfg.worktree = MagicMock()
        mock_cfg.security = None

        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_cfg
        mock_loader.has_project_config = True

        with patch(
            "adw.config.loader.ConfigLoader", return_value=mock_loader
        ):
            response = populated_registry_client.get(
                "/settings?project=my-app",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "Basics" in response.text

    def test_invalid_tab_defaults_to_project(
        self, empty_registry_client: TestClient
    ) -> None:
        """Invalid tab parameter defaults to 'project'."""
        response = empty_registry_client.get(
            "/settings?tab=nonexistent",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200

    def test_info_banner_present(self, empty_registry_client: TestClient) -> None:
        """Info banner about config changes is shown."""
        response = empty_registry_client.get(
            "/settings", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "Configuration changes take effect on the next ADW run" in response.text

    def test_project_selector_populated(
        self, populated_registry_client: TestClient
    ) -> None:
        """Project selector dropdown shows registered projects."""
        response = populated_registry_client.get(
            "/settings", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "my-app" in response.text
        assert "other" in response.text


class TestSettingsContentPartial:
    """Tests for GET /partials/settings-content."""

    def test_returns_content_fragment(
        self, empty_registry_client: TestClient
    ) -> None:
        """Returns HTML fragment for tab content."""
        response = empty_registry_client.get(
            "/partials/settings-content?tab=project"
        )
        assert response.status_code == 200

    def test_invalid_tab_defaults(
        self, empty_registry_client: TestClient
    ) -> None:
        """Invalid tab defaults to project."""
        response = empty_registry_client.get(
            "/partials/settings-content?tab=bogus"
        )
        assert response.status_code == 200


# ── Navigation & keyboard shortcut presence tests ──────────────────


class TestSettingsNavigation:
    """Tests verifying settings navigation integration in base.html."""

    def test_settings_link_in_nav(
        self, empty_registry_client: TestClient
    ) -> None:
        """Settings link appears in the navigation header."""
        response = empty_registry_client.get("/settings")
        assert response.status_code == 200
        assert 'data-page="settings"' in response.text
        assert 'hx-get="/settings"' in response.text

    def test_keyboard_shortcut_g_s_present(
        self, empty_registry_client: TestClient
    ) -> None:
        """The g+s keyboard shortcut is wired up in base.html."""
        response = empty_registry_client.get("/settings")
        assert response.status_code == 200
        assert "'s'" in response.text or '"s"' in response.text
        assert "settings" in response.text

    def test_settings_in_page_map(
        self, empty_registry_client: TestClient
    ) -> None:
        """Settings is registered in the pageMap for active nav tracking."""
        response = empty_registry_client.get("/settings")
        assert response.status_code == 200
        assert "'/settings': 'settings'" in response.text


class TestSettingsTabs:
    """Tests for the settings tab configuration."""

    def test_settings_tabs_defined(self) -> None:
        """All expected tabs are defined."""
        tab_keys = [t[0] for t in _SETTINGS_TABS]
        assert "project" in tab_keys
        assert "git" in tab_keys
        assert "llm" in tab_keys
        assert "task_manager" in tab_keys
        assert "security" in tab_keys
        assert "phases" in tab_keys

    def test_tabs_have_labels(self) -> None:
        """Each tab has a human-readable label."""
        for key, label in _SETTINGS_TABS:
            assert label, f"Tab {key} has no label"
            assert isinstance(label, str)
