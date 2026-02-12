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
