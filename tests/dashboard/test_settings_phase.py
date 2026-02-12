"""Tests for the phase config editor endpoints."""

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
    }
    (adw_dir / "project.yaml").write_text(yaml.dump(config, sort_keys=False))
    return tmp_path


@pytest.fixture()
def phase_client(project_dir: Path) -> Generator[TestClient]:
    """Client configured for phase settings tests."""
    app = create_dashboard_app()
    mock_reg = _make_mock_registry([(str(project_dir), "test-app")])
    mock_idx = _make_mock_index_manager()
    app.dependency_overrides[get_project_registry] = lambda: mock_reg
    app.dependency_overrides[get_index_manager] = lambda: mock_idx
    app.dependency_overrides[validate_csrf] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── GET /partials/settings-phase/{phase} ──────────────────────────


class TestPhasePartialRoute:
    """Tests for GET /partials/settings-phase/{phase}."""

    @pytest.mark.parametrize("phase", ["plan", "build", "validate", "document", "ship"])
    def test_valid_phase_returns_200(
        self, phase_client: TestClient, project_dir: Path, phase: str
    ) -> None:
        resp = phase_client.get(
            f"/partials/settings-phase/{phase}",
            params={"project": "test-app"},
        )
        assert resp.status_code == 200
        assert "enabled" in resp.text.lower()

    def test_invalid_phase_returns_400(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        resp = phase_client.get(
            "/partials/settings-phase/invalid",
            params={"project": "test-app"},
        )
        assert resp.status_code == 400

    def test_defaults_when_no_config_file(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """When no config.yaml exists for the phase, defaults are shown."""
        resp = phase_client.get(
            "/partials/settings-phase/plan",
            params={"project": "test-app"},
        )
        assert resp.status_code == 200
        # Should show default timeout for plan (900)
        assert "900" in resp.text
        # Should indicate using defaults
        assert "defaults" in resp.text.lower()

    def test_loaded_values_from_config(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """When config.yaml exists, values are loaded from it."""
        phase_dir = project_dir / ".adw" / "commands" / "plan"
        phase_dir.mkdir(parents=True)
        config = {
            "enabled": True,
            "timeout_seconds": 1200,
            "llm": {"model": "haiku"},
            "input_files": {"prd": "docs/prd.md"},
        }
        (phase_dir / "config.yaml").write_text(yaml.dump(config, sort_keys=False))

        resp = phase_client.get(
            "/partials/settings-phase/plan",
            params={"project": "test-app"},
        )
        assert resp.status_code == 200
        assert "1200" in resp.text
        assert "haiku" in resp.text

    def test_document_phase_shows_doc_mappings(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Document phase shows doc_mappings section."""
        resp = phase_client.get(
            "/partials/settings-phase/document",
            params={"project": "test-app"},
        )
        assert resp.status_code == 200
        assert "doc_mappings" in resp.text or "source_pattern" in resp.text

    def test_ship_phase_shows_ship_fields(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Ship phase shows commands and bypass_ci fields."""
        resp = phase_client.get(
            "/partials/settings-phase/ship",
            params={"project": "test-app"},
        )
        assert resp.status_code == 200
        assert "version_bump" in resp.text
        assert "publish" in resp.text
        assert "bypass_ci" in resp.text


# ── Phases tab sub-tab navigation ─────────────────────────────────


class TestPhasesTabNavigation:
    """Tests for the phases tab rendering sub-tab navigation."""

    def test_phases_tab_shows_sub_tabs(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """When phases tab is active, sub-tabs for all 5 phases are shown."""
        resp = phase_client.get(
            "/partials/settings-content",
            params={"project": "test-app", "tab": "phases"},
        )
        assert resp.status_code == 200
        for phase_name in ["Plan", "Build", "Validate", "Document", "Ship"]:
            assert phase_name in resp.text
        assert "phase-content" in resp.text
        assert "hx-trigger" in resp.text


# ── POST /settings/phase/{phase}/save ─────────────────────────────


class TestPhaseSaveEndpoint:
    """Tests for POST /settings/phase/{phase}/save."""

    def test_save_creates_directory_and_file(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Saving creates .adw/commands/{phase}/ and config.yaml."""
        resp = phase_client.post(
            "/settings/phase/plan/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "900",
                "llm_model": "opus",
            },
        )
        assert resp.status_code == 200
        config_path = project_dir / ".adw" / "commands" / "plan" / "config.yaml"
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert data["enabled"] is True
        assert data["timeout_seconds"] == 900

    def test_save_invalid_phase_returns_400(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        resp = phase_client.post(
            "/settings/phase/invalid/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "300",
                "llm_model": "opus",
            },
        )
        assert resp.status_code == 400

    def test_save_disabled_phase(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """enabled=false is persisted correctly."""
        resp = phase_client.post(
            "/settings/phase/build/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "false",
                "timeout_seconds": "1800",
                "llm_model": "sonnet",
            },
        )
        assert resp.status_code == 200
        config_path = project_dir / ".adw" / "commands" / "build" / "config.yaml"
        data = yaml.safe_load(config_path.read_text())
        assert data["enabled"] is False

    def test_save_document_phase_doc_mappings(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Document phase saves doc_mappings correctly."""
        resp = phase_client.post(
            "/settings/phase/document/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "900",
                "llm_model": "haiku",
                "doc_mappings_source.0": "src/**/*.py",
                "doc_mappings_dir.0": "docs/api",
                "doc_mappings_source.1": "tests/**/*.py",
                "doc_mappings_dir.1": "docs/tests",
            },
        )
        assert resp.status_code == 200
        config_path = project_dir / ".adw" / "commands" / "document" / "config.yaml"
        data = yaml.safe_load(config_path.read_text())
        assert len(data["doc_mappings"]) == 2
        assert data["doc_mappings"][0]["source_pattern"] == "src/**/*.py"
        assert data["doc_mappings"][0]["docs_dir"] == "docs/api"

    def test_save_ship_phase_commands(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Ship phase saves commands and bypass_ci correctly."""
        resp = phase_client.post(
            "/settings/phase/ship/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "1200",
                "llm_model": "sonnet",
                "version_bump": "npm version patch",
                "publish": "npm publish",
                "bypass_ci": "true",
            },
        )
        assert resp.status_code == 200
        config_path = project_dir / ".adw" / "commands" / "ship" / "config.yaml"
        data = yaml.safe_load(config_path.read_text())
        assert data["commands"]["version_bump"] == "npm version patch"
        assert data["commands"]["publish"] == "npm publish"
        assert data["bypass_ci"] is True

    def test_save_input_files(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Input files key-value pairs are saved correctly."""
        resp = phase_client.post(
            "/settings/phase/plan/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "900",
                "llm_model": "opus",
                "input_files_key.0": "prd",
                "input_files_val.0": "docs/prd.md",
                "input_files_key.1": "arch",
                "input_files_val.1": "docs/architecture.md",
            },
        )
        assert resp.status_code == 200
        config_path = project_dir / ".adw" / "commands" / "plan" / "config.yaml"
        data = yaml.safe_load(config_path.read_text())
        assert data["input_files"]["prd"] == "docs/prd.md"
        assert data["input_files"]["arch"] == "docs/architecture.md"

    def test_save_returns_success_toast(
        self, phase_client: TestClient, project_dir: Path
    ) -> None:
        """Save returns a success toast OOB swap."""
        resp = phase_client.post(
            "/settings/phase/plan/save",
            data={
                "csrf_token": "test",
                "_project": "test-app",
                "enabled": "true",
                "timeout_seconds": "900",
                "llm_model": "opus",
            },
        )
        assert resp.status_code == 200
        assert "alert-success" in resp.text or "saved" in resp.text.lower()
