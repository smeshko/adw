"""Tests for the read-only settings page and its context builder."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

from adw.core.constants import PHASE_SEQUENCE
from adw.dashboard.dependencies import get_index_manager, get_project_registry
from adw.dashboard.server import create_dashboard_app
from adw.dashboard.settings import settings_context

PROJECT_YAML = """\
# ADW Project Configuration
name: proj
language: python
platform: cli
test_command: python -m pytest tests/ -x -q
build_command: python -m build

git:
  branch_prefix: feature/
  base_branch: staging

task_manager:
  type: linear
  team_key: ADW
  sync_comments: true
#   labels:
#     prefix: "adw:"
"""

PHASE_FILES = {
    "plan": "enabled: false\n",
    "build": "enabled: true\ntimeout_seconds: 1800  # removed in #159\n",
    "validate": 'lint_command: "ruff check ."\n',
    "ship": "commands:\n  version_bump: ./update.sh  # bump\n",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A project shaped like this repo's .adw: comments, a stale phase key."""
    root = tmp_path / "proj"
    _write(root / ".adw" / "project.yaml", PROJECT_YAML)
    for phase, text in PHASE_FILES.items():
        _write(root / ".adw" / "commands" / phase / "config.yaml", text)
    return root


def _user_command(phase: str, config: str) -> Path:
    """Install a user-tier command (prompt.md + config.yaml) under ~/.adw."""
    command_dir = Path.home() / ".adw" / "commands" / phase
    _write(command_dir / "prompt.md", "user prompt\n")
    _write(command_dir / "config.yaml", config)
    return command_dir / "config.yaml"


def _client(projects: list[tuple[Path, str]]) -> TestClient:
    app = create_dashboard_app()
    registry = MagicMock()
    registry.get_all.return_value = [
        SimpleNamespace(path=path, name=name) for path, name in projects
    ]
    index = MagicMock()
    index.get_recent_runs.return_value = []
    app.dependency_overrides[get_project_registry] = lambda: registry
    app.dependency_overrides[get_index_manager] = lambda: index
    return TestClient(app)


def _values(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {row["name"]: row["lines"] for row in rows}


def _phase(ctx: dict[str, Any], name: str) -> dict[str, Any]:
    return next(p for p in ctx["phases"] if p["name"] == name)


def _digests(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ── settings_context ──────────────────────────────────────────────


class TestSettingsContext:
    def test_project_sections_show_file_values_and_defaults(
        self, project: Path
    ) -> None:
        ctx = settings_context(project, "git")

        sections = {key: _values(rows) for key, rows in ctx["sections"].items()}
        assert sections["project"]["name"] == ["proj"]
        assert sections["project"]["test_command"] == ["python -m pytest tests/ -x -q"]
        assert sections["git"]["base_branch"] == ["staging"]
        assert sections["git"]["skip_hooks"] == ["false"]
        assert sections["task_manager"]["team_key"] == ["ADW"]
        assert sections["task_manager"]["labels.prefix"] == ["adw:"]
        assert sections["task_manager"]["state_mapping"][0] == "plan: In Progress"
        assert sections["llm"]["retry.max_retries"] == ["3"]
        assert ctx["settings_tabs"][0] == ("project", "Basics")
        assert ctx["settings_tabs"][-1] == ("phases", "Phases")
        assert ctx["active_tab"] == "git"
        assert ctx["config_error"] is None
        assert ctx["has_project_file"] is True

    def test_phases_show_project_values_or_defaults(self, project: Path) -> None:
        ctx = settings_context(project, "phases")

        assert [p["name"] for p in ctx["phases"]] == list(PHASE_SEQUENCE)
        assert _values(_phase(ctx, "plan")["rows"])["enabled"] == ["false"]
        assert _values(_phase(ctx, "validate")["rows"])["lint_command"] == [
            "ruff check ."
        ]
        ship = _phase(ctx, "ship")
        assert _values(ship["rows"])["commands.version_bump"] == ["./update.sh"]
        assert _values(ship["rows"])["bypass_ci"] == ["true"]
        assert ("project", ".adw/commands/ship/config.yaml") in ship["sources"]
        document = _phase(ctx, "document")
        assert _values(document["rows"])["doc_mappings"] == ["—"]
        assert _values(document["rows"])["llm"] == ["—"]
        assert all(tier == "bundled" for tier, _ in document["sources"])

    def test_invalid_phase_file_reports_error_and_spares_other_phases(
        self, project: Path
    ) -> None:
        ctx = settings_context(project, "phases")

        build = _phase(ctx, "build")
        assert "timeout_seconds" in build["error"]
        assert build["rows"] == []
        assert all(
            _phase(ctx, name)["error"] is None
            for name in PHASE_SEQUENCE
            if name != "build"
        )

    def test_malformed_project_yaml_sets_config_error(self, project: Path) -> None:
        (project / ".adw" / "project.yaml").write_text("name: [unclosed\n")

        ctx = settings_context(project, "git")

        assert "CONFIG_PARSE_ERROR" in ctx["config_error"]
        assert ctx["sections"] == {}
        assert ctx["settings_tabs"] == [("phases", "Phases")]
        assert ctx["active_tab"] == "phases"
        assert len(ctx["phases"]) == len(PHASE_SEQUENCE)

    def test_missing_project_yaml_shows_detected_defaults(self, tmp_path: Path) -> None:
        root = tmp_path / "bare"
        root.mkdir()

        ctx = settings_context(root, "project")

        assert ctx["has_project_file"] is False
        assert ctx["config_error"] is None
        assert _values(ctx["sections"]["project"])["name"] == ["bare"]


class TestEffectivePhaseMerge:
    """The phase view merges tiers the way PhaseRunner does."""

    USER_CONFIG = "enabled: false\nllm:\n  model: haiku\ninput_files:\n  a: x.md\n"

    def test_user_tier_shows_through_without_project_file(self, project: Path) -> None:
        user_file = _user_command("document", self.USER_CONFIG)

        document = _phase(settings_context(project, "phases"), "document")

        values = _values(document["rows"])
        assert values["enabled"] == ["false"]
        assert values["llm.model"] == ["haiku"]
        assert values["input_files"] == ["a: x.md"]
        assert document["sources"] == [("user", str(user_file))]

    def test_project_file_overlays_user_tier(self, project: Path) -> None:
        _user_command("document", self.USER_CONFIG)
        _write(
            project / ".adw" / "commands" / "document" / "config.yaml",
            "input_files:\n  b: y.md\nllm:\n  model: opus\n",
        )

        values = _values(
            _phase(settings_context(project, "phases"), "document")["rows"]
        )

        assert values["input_files"] == ["a: x.md", "b: y.md"]
        assert values["llm.model"] == ["opus"]
        assert values["enabled"] == ["false"]

    def test_explicit_project_enabled_overrides_user_tier(self, project: Path) -> None:
        _user_command("document", "enabled: false\n")
        _write(
            project / ".adw" / "commands" / "document" / "config.yaml",
            "enabled: true\n",
        )

        values = _values(
            _phase(settings_context(project, "phases"), "document")["rows"]
        )

        assert values["enabled"] == ["true"]

    @pytest.mark.parametrize(
        ("phase", "text", "field", "default", "project_value"),
        [
            ("validate", "lint_command: {v}-lint\n", "lint_command", "—", "proj-lint"),
            (
                "document",
                "doc_mappings:\n  - source_pattern: {v}/**\n    docs_dir: {v}\n",
                "doc_mappings",
                "—",
                "source_pattern: proj/**, docs_dir: proj",
            ),
            (
                "ship",
                "commands:\n  version_bump: {v}-bump\n",
                "commands.version_bump",
                "—",
                "proj-bump",
            ),
            ("ship", "bypass_ci: {v}\n", "bypass_ci", "true", "false"),
        ],
        ids=["lint_command", "doc_mappings", "version_bump", "bypass_ci"],
    )
    def test_phase_specific_fields_come_from_project_file_only(
        self,
        tmp_path: Path,
        phase: str,
        text: str,
        field: str,
        default: str,
        project_value: str,
    ) -> None:
        root = tmp_path / "fresh"
        _write(root / ".adw" / "project.yaml", "name: fresh\nlanguage: python\n")
        user_value = "false" if field == "bypass_ci" else "user"
        _user_command(phase, text.format(v=user_value))

        before = _values(_phase(settings_context(root, "phases"), phase)["rows"])
        project_text = text.format(v="false" if field == "bypass_ci" else "proj")
        _write(root / ".adw" / "commands" / phase / "config.yaml", project_text)
        after = _values(_phase(settings_context(root, "phases"), phase)["rows"])

        assert before[field] == [default]
        assert after[field] == [project_value]


# ── Routes ─────────────────────────────────────────────────────────


class TestSettingsRoutes:
    def test_every_tab_renders_its_values_without_touching_config(
        self, project: Path
    ) -> None:
        client = _client([(project, "proj")])
        ctx = settings_context(project, "project")
        before = _digests(project / ".adw")

        for tab, _ in ctx["settings_tabs"]:
            if tab == "phases":
                expected = ["./update.sh", "ruff check .", "timeout_seconds"]
            else:
                rows = ctx["sections"][tab]
                expected = [row["name"] for row in rows]
                expected += [str(escape(row["lines"][0])) for row in rows]
            responses = {
                "page": client.get(f"/settings?project=proj&tab={tab}"),
                "htmx": client.get(
                    f"/settings?project=proj&tab={tab}",
                    headers={"HX-Request": "true"},
                ),
                "partial": client.get(
                    f"/partials/settings-content?project=proj&tab={tab}"
                ),
            }
            for mode, response in responses.items():
                assert response.status_code == 200, (tab, mode)
                missing = [text for text in expected if text not in response.text]
                assert not missing, (tab, mode, missing)
            assert "<!DOCTYPE html>" in responses["page"].text
            assert "<!DOCTYPE html>" not in responses["htmx"].text

        assert _digests(project / ".adw") == before

    def test_config_error_is_shown(self, project: Path) -> None:
        (project / ".adw" / "project.yaml").write_text("name: [unclosed\n")

        response = _client([(project, "proj")]).get("/settings?project=proj")

        assert response.status_code == 200
        assert "CONFIG_PARSE_ERROR" in response.text

    def test_invalid_tab_falls_back_to_basics(self, project: Path) -> None:
        response = _client([(project, "proj")]).get(
            "/partials/settings-content?project=proj&tab=bogus"
        )

        assert response.status_code == 200
        assert "python -m pytest tests/ -x -q" in response.text

    def test_unregistered_project_partial_returns_404(self, project: Path) -> None:
        response = _client([(project, "proj")]).get(
            "/partials/settings-content?project=ghost&tab=project"
        )

        assert response.status_code == 404

    def test_no_projects_shows_empty_state(self) -> None:
        response = _client([]).get("/settings", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert "No projects registered" in response.text

    def test_no_selection_lists_projects_and_prompts(self, project: Path) -> None:
        response = _client([(project, "proj")]).get("/settings")

        assert response.status_code == 200
        assert "Select a project" in response.text
        assert ">proj</option>" in response.text
