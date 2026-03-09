"""Tests for the settings save endpoint (POST /settings/save)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    validate_csrf,
)
from adw.dashboard.mutations import (
    _SECTION_FIELD_MAP,
    _collect_indexed_fields,
    _collect_mapping_fields,
    _deep_set,
    _parse_form_value,
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
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory with a valid project.yaml."""
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
def save_client(project_dir: Path) -> Generator[TestClient]:
    """Client configured for settings save tests."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([(str(project_dir), "test-app")])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    # Bypass CSRF validation for testing
    app.dependency_overrides[validate_csrf] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _csrf_token() -> str:
    """Generate a valid CSRF token for form data."""
    mock_request = MagicMock()
    mock_request.state = MagicMock()
    return generate_csrf_token(mock_request)


# ── Unit tests for helper functions ───────────────────────────────


class TestParseFormValue:
    """Tests for _parse_form_value."""

    def test_bool_true(self) -> None:
        assert _parse_form_value("skip_hooks", "true") is True

    def test_bool_false(self) -> None:
        assert _parse_form_value("skip_hooks", "false") is False

    def test_bool_on(self) -> None:
        assert _parse_form_value("skip_hooks", "on") is True

    def test_int_field(self) -> None:
        assert _parse_form_value("max_retries", "5") == 5

    def test_int_port(self) -> None:
        assert _parse_form_value("backend_start", "8080") == 8080

    def test_float_field(self) -> None:
        assert _parse_form_value("base_delay_seconds", "1.5") == 1.5

    def test_float_multiplier(self) -> None:
        assert _parse_form_value("multiplier", "2.5") == 2.5

    def test_string_field(self) -> None:
        assert _parse_form_value("branch_prefix", "feature/") == "feature/"

    def test_empty_string_returns_none(self) -> None:
        assert _parse_form_value("test_command", "") is None

    def test_invalid_int_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_form_value("max_retries", "abc")

    def test_invalid_float_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_form_value("base_delay_seconds", "abc")


class TestDeepSet:
    """Tests for _deep_set."""

    def test_single_key(self) -> None:
        d: dict = {}
        _deep_set(d, ["language"], "python")
        assert d == {"language": "python"}

    def test_nested_keys(self) -> None:
        d: dict = {}
        _deep_set(d, ["git", "branch_prefix"], "feature/")
        assert d == {"git": {"branch_prefix": "feature/"}}

    def test_triple_nested(self) -> None:
        d: dict = {}
        _deep_set(d, ["llm", "retry", "max_retries"], 5)
        assert d == {"llm": {"retry": {"max_retries": 5}}}

    def test_preserves_existing(self) -> None:
        d: dict = {"git": {"skip_hooks": False}}
        _deep_set(d, ["git", "branch_prefix"], "feat/")
        assert d == {"git": {"skip_hooks": False, "branch_prefix": "feat/"}}


class TestSectionFieldMap:
    """Tests for _SECTION_FIELD_MAP coverage."""

    def test_project_fields(self) -> None:
        assert "language" in _SECTION_FIELD_MAP["project"]
        assert "platform" in _SECTION_FIELD_MAP["project"]
        assert "test_command" in _SECTION_FIELD_MAP["project"]
        assert "build_command" in _SECTION_FIELD_MAP["project"]

    def test_git_fields(self) -> None:
        assert "branch_prefix" in _SECTION_FIELD_MAP["git"]
        assert "skip_hooks" in _SECTION_FIELD_MAP["git"]
        assert "base_branch" in _SECTION_FIELD_MAP["git"]

    def test_worktree_fields(self) -> None:
        assert "backend_start" in _SECTION_FIELD_MAP["worktree"]
        assert "frontend_start" in _SECTION_FIELD_MAP["worktree"]

    def test_llm_fields(self) -> None:
        assert "max_retries" in _SECTION_FIELD_MAP["llm"]
        assert "base_delay_seconds" in _SECTION_FIELD_MAP["llm"]
        assert "max_delay_seconds" in _SECTION_FIELD_MAP["llm"]
        assert "multiplier" in _SECTION_FIELD_MAP["llm"]


# ── Integration tests for POST /settings/save ────────────────────


class TestSaveSettingsBasics:
    """Tests for saving Basics section fields."""

    def test_save_language(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving language updates project.yaml."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "javascript",
                "platform": "cli",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text

        # Verify file was updated
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["language"] == "javascript"

    def test_save_platform(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving platform updates project.yaml."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "python",
                "platform": "web",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["platform"] == "web"

    def test_save_commands(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving test/build commands updates project.yaml."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "python",
                "platform": "cli",
                "test_command": "pytest -v",
                "build_command": "python -m build",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["test_command"] == "pytest -v"
        assert config["build_command"] == "python -m build"


class TestSaveSettingsGit:
    """Tests for saving Git section fields."""

    def test_save_branch_prefix(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving branch_prefix updates the git section."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "git",
                "_project": "test-app",
                "branch_prefix": "feat/",
                "skip_hooks": "false",
                "base_branch": "main",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["git"]["branch_prefix"] == "feat/"

    def test_save_skip_hooks_checked(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving skip_hooks=true toggles the boolean on."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "git",
                "_project": "test-app",
                "branch_prefix": "feature/",
                "skip_hooks": "true",
                "base_branch": "main",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["git"]["skip_hooks"] is True

    def test_save_base_branch(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving base_branch updates the git section."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "git",
                "_project": "test-app",
                "branch_prefix": "feature/",
                "skip_hooks": "false",
                "base_branch": "develop",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["git"]["base_branch"] == "develop"


class TestSaveSettingsPorts:
    """Tests for saving Ports section fields."""

    def test_save_port_range(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving port fields updates worktree.port_range."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "worktree",
                "_project": "test-app",
                "backend_start": "8080",
                "frontend_start": "8180",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["worktree"]["port_range"]["backend_start"] == 8080
        assert config["worktree"]["port_range"]["frontend_start"] == 8180


class TestSaveSettingsLLMRetry:
    """Tests for saving LLM Retry section fields."""

    def test_save_retry_fields(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving retry fields updates llm.retry."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "llm",
                "_project": "test-app",
                "max_retries": "5",
                "base_delay_seconds": "2.0",
                "max_delay_seconds": "120.0",
                "multiplier": "3.0",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["llm"]["retry"]["max_retries"] == 5
        assert config["llm"]["retry"]["base_delay_seconds"] == 2.0
        assert config["llm"]["retry"]["max_delay_seconds"] == 120.0
        assert config["llm"]["retry"]["multiplier"] == 3.0


class TestSaveSettingsValidation:
    """Tests for validation failures."""

    def test_csrf_failure(self, project_dir: Path) -> None:
        """Missing CSRF token returns 403."""
        app = create_dashboard_app()
        mock_reg = _make_mock_registry([(str(project_dir), "test-app")])
        mock_idx = _make_mock_index_manager()
        app.dependency_overrides[get_project_registry] = lambda: mock_reg
        app.dependency_overrides[get_index_manager] = lambda: mock_idx
        # Do NOT override validate_csrf — it should reject
        client = TestClient(app)

        response = client.post(
            "/settings/save",
            data={
                "_section": "project",
                "_project": "test-app",
                "language": "python",
            },
        )
        assert response.status_code == 403
        app.dependency_overrides.clear()

    def test_pydantic_validation_failure(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Invalid values rejected by Pydantic validation."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "llm",
                "_project": "test-app",
                "max_retries": "0",  # gt=0 constraint fails
                "base_delay_seconds": "1.0",
                "max_delay_seconds": "60.0",
                "multiplier": "2.0",
            },
        )
        assert response.status_code == 200
        assert "Validation failed" in response.text or "alert-error" in response.text

    def test_invalid_section_returns_error(
        self, save_client: TestClient
    ) -> None:
        """Invalid section name returns error toast."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "nonexistent",
                "_project": "test-app",
            },
        )
        assert response.status_code == 200
        assert "Invalid section" in response.text

    def test_project_not_found_returns_error(
        self, save_client: TestClient
    ) -> None:
        """Unknown project returns error toast."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "nonexistent-project",
                "language": "python",
            },
        )
        assert response.status_code == 200
        assert "Project not found" in response.text


class TestSaveSettingsFileCreation:
    """Tests for file creation when no config exists."""

    def test_creates_adw_dir_and_file(self, tmp_path: Path) -> None:
        """Save creates .adw/ directory and project.yaml when they don't exist (FR66)."""
        # Bare project dir — NO .adw/ directory at all
        app = create_dashboard_app()
        mock_reg = _make_mock_registry([(str(tmp_path), "new-app")])
        mock_idx = _make_mock_index_manager()
        app.dependency_overrides[get_project_registry] = lambda: mock_reg
        app.dependency_overrides[get_index_manager] = lambda: mock_idx
        app.dependency_overrides[validate_csrf] = lambda: None
        client = TestClient(app)

        # The save endpoint seeds required 'name' from display name and
        # 'language' defaults to 'python' when missing, so saving from
        # scratch should work.
        response = client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "new-app",
                "language": "go",
                "platform": "api",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text

        # Verify .adw/ directory and file were created
        config_path = tmp_path / ".adw" / "project.yaml"
        assert config_path.exists()
        config = yaml.safe_load(config_path.read_text())
        assert config["name"] == "new-app"
        assert config["language"] == "go"
        assert config["platform"] == "api"
        app.dependency_overrides.clear()


class TestSaveSettingsPreservation:
    """Tests for preserving existing config from other sections."""

    def test_save_one_section_preserves_others(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving one section doesn't clobber values from other sections."""
        # Save git section
        save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "git",
                "_project": "test-app",
                "branch_prefix": "hotfix/",
                "skip_hooks": "false",
                "base_branch": "main",
            },
        )

        # Verify other sections are preserved
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        # Project section preserved
        assert config["name"] == "test-app"
        assert config["language"] == "python"
        # LLM section preserved
        assert config["llm"]["retry"]["max_retries"] == 3
        # Worktree section preserved
        assert config["worktree"]["port_range"]["backend_start"] == 9100
        # Git section updated
        assert config["git"]["branch_prefix"] == "hotfix/"


class TestSaveSettingsToast:
    """Tests for toast response HTML."""

    def test_success_toast_present(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Success response includes success toast."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "python",
                "platform": "cli",
            },
        )
        assert response.status_code == 200
        assert "alert-success" in response.text
        assert "Settings saved successfully" in response.text
        assert "toast-container" in response.text
        assert "hx-swap-oob" in response.text

    def test_error_toast_on_validation_failure(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Error toast appears on validation failure."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "llm",
                "_project": "test-app",
                "max_retries": "-1",
                "base_delay_seconds": "1.0",
                "max_delay_seconds": "60.0",
                "multiplier": "2.0",
            },
        )
        assert response.status_code == 200
        assert "alert-error" in response.text


class TestSaveSettingsAtomicWrite:
    """Tests for atomic write behavior."""

    def test_file_is_complete_after_save(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """The saved file is a complete, parseable YAML."""
        save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "rust",
                "platform": "cli",
            },
        )
        config_path = project_dir / ".adw" / "project.yaml"
        # File should be valid YAML
        config = yaml.safe_load(config_path.read_text())
        assert isinstance(config, dict)
        assert config["language"] == "rust"

    def test_no_tmp_file_remains(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """No .tmp file should remain after a successful save."""
        save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "project",
                "_project": "test-app",
                "language": "python",
                "platform": "cli",
            },
        )
        adw_dir = project_dir / ".adw"
        tmp_files = list(adw_dir.glob("*.tmp"))
        assert len(tmp_files) == 0


# ── Context builder extension tests ──────────────────────────────


class TestBuildSettingsContextExtended:
    """Tests for the extended build_settings_context with ports and retry."""

    def test_worktree_section_includes_port_settings(self) -> None:
        """Worktree section should include backend_start and frontend_start."""
        from adw.config.registry import ConfigRegistry
        from adw.dashboard.routes import build_settings_context
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        registry = ConfigRegistry()
        result = build_settings_context(config, registry)

        worktree_names = [s["name"] for s in result.get("worktree", [])]
        assert "backend_start" in worktree_names
        assert "frontend_start" in worktree_names

    def test_llm_section_includes_retry_settings(self) -> None:
        """LLM section should include retry settings."""
        from adw.config.registry import ConfigRegistry
        from adw.dashboard.routes import build_settings_context
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        registry = ConfigRegistry()
        result = build_settings_context(config, registry)

        llm_names = [s["name"] for s in result.get("llm", [])]
        assert "max_retries" in llm_names
        assert "base_delay_seconds" in llm_names
        assert "max_delay_seconds" in llm_names
        assert "multiplier" in llm_names

    def test_port_values_resolved_from_config(self) -> None:
        """Port field values should resolve from config.worktree.port_range."""
        from adw.config.registry import ConfigRegistry
        from adw.dashboard.routes import build_settings_context
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        registry = ConfigRegistry()
        result = build_settings_context(config, registry)

        backend = next(
            s for s in result["worktree"] if s["name"] == "backend_start"
        )
        assert backend["current_value"] == 9100  # default

    def test_retry_values_resolved_from_config(self) -> None:
        """Retry field values should resolve from config.llm.retry."""
        from adw.config.registry import ConfigRegistry
        from adw.dashboard.routes import build_settings_context
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        registry = ConfigRegistry()
        result = build_settings_context(config, registry)

        max_retries = next(
            s for s in result["llm"] if s["name"] == "max_retries"
        )
        assert max_retries["current_value"] == 3  # default


class TestResolveConfigValueExtended:
    """Tests for extended _resolve_config_value with nested fields."""

    def test_port_range_field(self) -> None:
        """Resolve backend_start from worktree section."""
        from adw.dashboard.routes import _resolve_config_value
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        assert _resolve_config_value(config, "worktree", "backend_start") == 9100

    def test_retry_field(self) -> None:
        """Resolve max_retries from llm section."""
        from adw.dashboard.routes import _resolve_config_value
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        assert _resolve_config_value(config, "llm", "max_retries") == 3

    def test_retry_multiplier(self) -> None:
        """Resolve multiplier from llm section."""
        from adw.dashboard.routes import _resolve_config_value
        from adw.models.config import ProjectConfig

        config = ProjectConfig(name="test", language="python")
        assert _resolve_config_value(config, "llm", "multiplier") == 2.0


# ── Helper function tests for complex field parsing ───────────────


class TestCollectIndexedFields:
    """Tests for _collect_indexed_fields."""

    def test_collects_sequential_fields(self) -> None:
        form = {"blocked_env_files.0": ".env", "blocked_env_files.1": ".secret"}
        result = _collect_indexed_fields(form, "blocked_env_files")
        assert result == [".env", ".secret"]

    def test_filters_empty_strings(self) -> None:
        form = {"blocked_env_files.0": ".env", "blocked_env_files.1": "  "}
        result = _collect_indexed_fields(form, "blocked_env_files")
        assert result == [".env"]

    def test_returns_empty_list_when_none(self) -> None:
        form = {"other_field": "value"}
        result = _collect_indexed_fields(form, "blocked_env_files")
        assert result == []

    def test_sorts_by_index(self) -> None:
        form = {"items.2": "c", "items.0": "a", "items.1": "b"}
        result = _collect_indexed_fields(form, "items")
        assert result == ["a", "b", "c"]

    def test_ignores_non_numeric_suffixes(self) -> None:
        form = {"items.0": "a", "items.plan": "b"}
        result = _collect_indexed_fields(form, "items")
        assert result == ["a"]


class TestCollectMappingFields:
    """Tests for _collect_mapping_fields."""

    def test_collects_mapping(self) -> None:
        form = {"state_mapping.plan": "Todo", "state_mapping.build": "Doing"}
        result = _collect_mapping_fields(form, "state_mapping")
        assert result == {"plan": "Todo", "build": "Doing"}

    def test_returns_empty_dict_when_none(self) -> None:
        form = {"other": "value"}
        result = _collect_mapping_fields(form, "state_mapping")
        assert result == {}

    def test_strips_whitespace(self) -> None:
        form = {"state_mapping.plan": "  In Progress  "}
        result = _collect_mapping_fields(form, "state_mapping")
        assert result == {"plan": "In Progress"}


# ── Section field map extension tests ─────────────────────────────


class TestSectionFieldMapTaskManager:
    """Tests for task_manager entries in _SECTION_FIELD_MAP."""

    def test_task_manager_section_exists(self) -> None:
        assert "task_manager" in _SECTION_FIELD_MAP

    def test_task_manager_type_field(self) -> None:
        assert _SECTION_FIELD_MAP["task_manager"]["type"] == ["task_manager", "type"]

    def test_task_manager_team_key_field(self) -> None:
        assert _SECTION_FIELD_MAP["task_manager"]["team_key"] == [
            "task_manager",
            "team_key",
        ]

    def test_task_manager_boolean_fields(self) -> None:
        assert _SECTION_FIELD_MAP["task_manager"]["sync_comments"] == [
            "task_manager",
            "sync_comments",
        ]
        assert _SECTION_FIELD_MAP["task_manager"]["auto_close"] == [
            "task_manager",
            "auto_close",
        ]

    def test_task_manager_labels_fields(self) -> None:
        assert _SECTION_FIELD_MAP["task_manager"]["labels_enabled"] == [
            "task_manager",
            "labels",
            "enabled",
        ]
        assert _SECTION_FIELD_MAP["task_manager"]["label_prefix"] == [
            "task_manager",
            "labels",
            "prefix",
        ]


class TestSectionFieldMapSecurity:
    """Tests for security entry in _SECTION_FIELD_MAP."""

    def test_security_section_exists(self) -> None:
        assert "security" in _SECTION_FIELD_MAP

    def test_security_has_empty_field_map(self) -> None:
        """Security uses complex field parsing, not scalar field map."""
        assert _SECTION_FIELD_MAP["security"] == {}


class TestBoolFieldsExtended:
    """Tests for extended _BOOL_FIELDS set."""

    def test_sync_comments_is_bool(self) -> None:
        assert _parse_form_value("sync_comments", "true") is True
        assert _parse_form_value("sync_comments", "false") is False

    def test_auto_close_is_bool(self) -> None:
        assert _parse_form_value("auto_close", "true") is True

    def test_labels_enabled_is_bool(self) -> None:
        assert _parse_form_value("labels_enabled", "on") is True


# ── Integration tests for Task Manager save ───────────────────────


class TestSaveSettingsTaskManager:
    """Integration tests for saving Task Manager section."""

    def test_save_type_and_team_key(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving type and team_key updates task_manager section."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "task_manager",
                "_project": "test-app",
                "type": "linear",
                "team_key": "ADW",
                "sync_comments": "false",
                "auto_close": "false",
                "labels_enabled": "true",
                "label_prefix": "adw:",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text

        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["task_manager"]["type"] == "linear"
        assert config["task_manager"]["team_key"] == "ADW"

    def test_save_boolean_fields(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving boolean fields (sync_comments, auto_close, labels_enabled)."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "task_manager",
                "_project": "test-app",
                "type": "linear",
                "team_key": "TST",
                "sync_comments": "true",
                "auto_close": "true",
                "labels_enabled": "false",
                "label_prefix": "ci:",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["task_manager"]["sync_comments"] is True
        assert config["task_manager"]["auto_close"] is True
        assert config["task_manager"]["labels"]["enabled"] is False
        assert config["task_manager"]["labels"]["prefix"] == "ci:"

    def test_save_state_mapping(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving state_mapping updates the mapping dict."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "task_manager",
                "_project": "test-app",
                "type": "linear",
                "team_key": "ADW",
                "sync_comments": "false",
                "auto_close": "false",
                "labels_enabled": "true",
                "label_prefix": "adw:",
                "state_mapping.plan": "Todo",
                "state_mapping.build": "In Dev",
                "state_mapping.validate": "Review",
                "state_mapping.document": "Review",
                "state_mapping.ship": "Done",
                "state_mapping.failed": "Backlog",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        mapping = config["task_manager"]["state_mapping"]
        assert mapping["plan"] == "Todo"
        assert mapping["build"] == "In Dev"
        assert mapping["validate"] == "Review"
        assert mapping["ship"] == "Done"
        assert mapping["failed"] == "Backlog"

    def test_save_type_none(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving type=none is valid and preserves defaults."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "task_manager",
                "_project": "test-app",
                "type": "none",
                "sync_comments": "false",
                "auto_close": "false",
                "labels_enabled": "true",
                "label_prefix": "adw:",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["task_manager"]["type"] == "none"

    def test_save_preserves_other_sections(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving task_manager doesn't clobber git/llm/worktree sections."""
        save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "task_manager",
                "_project": "test-app",
                "type": "linear",
                "team_key": "ADW",
                "sync_comments": "false",
                "auto_close": "false",
                "labels_enabled": "true",
                "label_prefix": "adw:",
            },
        )
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        # Other sections preserved
        assert config["language"] == "python"
        assert config["git"]["branch_prefix"] == "feature/"
        assert config["llm"]["retry"]["max_retries"] == 3
        assert config["worktree"]["port_range"]["backend_start"] == 9100


# ── Integration tests for Security save ───────────────────────────


class TestSaveSettingsSecurity:
    """Integration tests for saving Security section."""

    def test_save_blocked_env_files(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving blocked_env_files updates security section."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "security",
                "_project": "test-app",
                "blocked_env_files.0": ".env",
                "blocked_env_files.1": "*.pem",
                "blocked_env_files.2": "*.key",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["security"]["blocked_env_files"] == [".env", "*.pem", "*.key"]

    def test_save_empty_lists(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving with no list items results in empty lists."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "security",
                "_project": "test-app",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["security"]["blocked_patterns"] == []
        assert config["security"]["blocked_env_files"] == []

    def test_save_blocked_commands(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving blocked_commands creates BlockedPattern-format entries."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "security",
                "_project": "test-app",
                "blocked_commands.0": r"rm\s+-rf\s+/",
                "blocked_commands.1": r"sudo\s+",
            },
        )
        assert response.status_code == 200
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        patterns = config["security"]["blocked_patterns"]
        assert len(patterns) == 2
        assert patterns[0]["pattern"] == r"rm\s+-rf\s+/"
        assert patterns[0]["severity"] == "warning"
        assert patterns[0]["category"] == "destructive"
        assert patterns[1]["pattern"] == r"sudo\s+"

    def test_save_preserves_other_sections(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Saving security doesn't clobber other sections."""
        save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "security",
                "_project": "test-app",
                "blocked_env_files.0": ".env",
            },
        )
        config = yaml.safe_load(
            (project_dir / ".adw" / "project.yaml").read_text()
        )
        assert config["language"] == "python"
        assert config["git"]["branch_prefix"] == "feature/"
        assert config["llm"]["retry"]["max_retries"] == 3


# ── Cross-field validation integration tests ──────────────────────


class TestSaveSettingsCrossFieldValidation:
    """Integration tests for cross-field validation via Pydantic."""

    def test_max_delay_less_than_base_delay_rejected(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Pydantic rejects max_delay_seconds < base_delay_seconds."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "llm",
                "_project": "test-app",
                "max_retries": "3",
                "base_delay_seconds": "10.0",
                "max_delay_seconds": "5.0",  # less than base
                "multiplier": "2.0",
            },
        )
        assert response.status_code == 200
        assert "Validation failed" in response.text or "alert-error" in response.text

    def test_valid_delay_values_accepted(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Valid delay values (max >= base) are accepted."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "llm",
                "_project": "test-app",
                "max_retries": "3",
                "base_delay_seconds": "5.0",
                "max_delay_seconds": "5.0",  # equal to base — valid
                "multiplier": "2.0",
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text

    def test_overlapping_ports_rejected(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Pydantic rejects overlapping backend/frontend port ranges."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "worktree",
                "_project": "test-app",
                "backend_start": "9100",
                "frontend_start": "9110",  # overlaps with 9100-9114
            },
        )
        assert response.status_code == 200
        assert "Validation failed" in response.text or "alert-error" in response.text

    def test_non_overlapping_ports_accepted(
        self, save_client: TestClient, project_dir: Path
    ) -> None:
        """Non-overlapping port ranges are accepted."""
        response = save_client.post(
            "/settings/save",
            data={
                "csrf_token": _csrf_token(),
                "_section": "worktree",
                "_project": "test-app",
                "backend_start": "9100",
                "frontend_start": "9200",  # no overlap
            },
        )
        assert response.status_code == 200
        assert "Settings saved successfully" in response.text
