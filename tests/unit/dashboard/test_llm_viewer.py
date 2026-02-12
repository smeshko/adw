"""Tests for Story 2.3: LLM Interaction Viewer.

Covers LLM interaction summary in phase detail, prompt/response
content endpoints, and token display.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app
from adw.models.index import IndexEntry


def _make_index_entry(
    run_id: str = "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
    project_name: str = "my-project",
    feature_description: str = "Add user authentication",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    project_path: str = "/tmp/my-project",
    phases_completed: list[str] | None = None,
    phase_reached: str | None = "build",
) -> IndexEntry:
    """Create a test IndexEntry."""
    now = datetime.now(UTC)
    return IndexEntry(
        run_id=run_id,
        project_name=project_name,
        feature_description=feature_description,
        status=status,
        started_at=started_at or now - timedelta(minutes=10),
        completed_at=completed_at or now - timedelta(minutes=2),
        project_path=project_path,
        phases_completed=phases_completed or ["plan", "build"],
        phase_reached=phase_reached,
    )


def _mock_index_manager(
    entries: list[IndexEntry] | None = None,
) -> MagicMock:
    """Build a mock IndexManager."""
    mock = MagicMock()
    all_entries = entries or []

    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return [e for e in all_entries if e.status == "running"]
        limit = kwargs.get("limit", 10)
        return all_entries[:limit]

    mock.get_recent_runs.side_effect = get_recent_side_effect
    return mock


def _mock_project_registry(project_names: list[str] | None = None) -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    projects = []
    for name in (project_names or []):
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _make_client_with_mocks(
    entries: list[IndexEntry] | None = None,
    project_names: list[str] | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = _mock_index_manager(entries=entries or [])
    pr = _mock_project_registry(project_names or ["my-project"])
    sa = MagicMock()
    sa.get_global_stats.return_value = MagicMock(projects=[])

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa

    return TestClient(app)


# ── LLM Interaction Summary in Phase Detail ────────────────────────


class TestLLMInteractionSummary:
    """Tests for LLM interaction summary line in phase detail (FR25)."""

    def test_phase_detail_shows_llm_section(self) -> None:
        """Phase detail includes an LLM Interaction section."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            # Mock the LLM response file read
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = {
                    "input_tokens": 1250,
                    "output_tokens": 3400,
                }
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert response.status_code == 200
        assert "LLM Interaction" in response.text

    def test_phase_detail_shows_token_counts(self) -> None:
        """LLM summary shows input and output token counts."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = {
                    "input_tokens": 1250,
                    "output_tokens": 3400,
                }
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert "1,250" in response.text or "1250" in response.text
        assert "3,400" in response.text or "3400" in response.text

    def test_phase_detail_has_view_prompt_button(self) -> None:
        """LLM summary has a View button for the prompt."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = {
                    "input_tokens": 1250,
                    "output_tokens": 3400,
                }
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert f"/runs/{entry.run_id}/phases/plan/prompt" in response.text

    def test_phase_detail_has_view_response_button(self) -> None:
        """LLM summary has a View button for the response."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = {
                    "input_tokens": 1250,
                    "output_tokens": 3400,
                }
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert f"/runs/{entry.run_id}/phases/plan/response" in response.text

    def test_phase_detail_llm_uses_card_classes(self) -> None:
        """LLM section uses card card-compact bg-base-300 (UX §5.4.3)."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = {
                    "input_tokens": 1250,
                    "output_tokens": 3400,
                }
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        # Should have 3 card sections: hooks, llm, artifacts
        assert response.text.count("card card-compact bg-base-300") >= 3

    def test_phase_detail_no_llm_data_shows_fallback(self) -> None:
        """When no LLM data available, shows 'No LLM data' message."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert "No LLM data" in response.text


# ── LLM Prompt/Response Content Endpoints ─────────────────────────


class TestLLMPromptEndpoint:
    """Tests for GET /runs/{id}/phases/{phase}/prompt endpoint."""

    def test_prompt_returns_200(self) -> None:
        """Prompt endpoint returns 200 with content."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "System prompt: You are a helpful assistant..."
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/prompt",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_prompt_renders_in_pre_block(self) -> None:
        """Prompt content renders in a scrollable pre block."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "System prompt text"
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/prompt",
                headers={"HX-Request": "true"},
            )

        assert "<pre" in response.text
        assert "max-h-96" in response.text
        assert "overflow-y-auto" in response.text
        assert "font-mono" in response.text
        assert "text-xs" in response.text

    def test_prompt_shows_content(self) -> None:
        """Prompt endpoint shows the actual prompt text."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "You are a code generator"
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/prompt",
                headers={"HX-Request": "true"},
            )

        assert "You are a code generator" in response.text

    def test_prompt_not_found_returns_404(self) -> None:
        """Missing prompt returns 404."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/prompt",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 404

    def test_prompt_invalid_phase_returns_400(self) -> None:
        """Invalid phase returns 400."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/phases/badphase/prompt",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_prompt_run_not_found_returns_404(self) -> None:
        """Non-existent run returns 404."""
        client = _make_client_with_mocks(entries=[])
        response = client.get(
            "/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/phases/plan/prompt",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404


class TestLLMResponseEndpoint:
    """Tests for GET /runs/{id}/phases/{phase}/response endpoint."""

    def test_response_returns_200(self) -> None:
        """Response endpoint returns 200 with content."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "Here is the generated code..."
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/response",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_response_renders_in_pre_block(self) -> None:
        """Response content renders in a scrollable pre block."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "Generated output text"
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/response",
                headers={"HX-Request": "true"},
            )

        assert "<pre" in response.text
        assert "max-h-96" in response.text
        assert "font-mono" in response.text

    def test_response_shows_content(self) -> None:
        """Response endpoint shows the actual response text."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "The final generated code output"
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/response",
                headers={"HX-Request": "true"},
            )

        assert "The final generated code output" in response.text

    def test_response_not_found_returns_404(self) -> None:
        """Missing response returns 404."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/response",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 404


# ── Helper Function Tests ──────────────────────────────────────────


class TestLoadLLMStats:
    """Tests for _load_llm_stats helper."""

    def test_returns_token_stats_from_response_file(self, tmp_path: Path) -> None:
        """Loads token stats from the LLM response JSON file."""
        from adw.dashboard.routes import _load_llm_stats

        # Create directory structure
        llm_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "llm"
        llm_dir.mkdir(parents=True)

        # Write response file
        response_data = {
            "timestamp": "2025-01-15T10:32:00+00:00",
            "phase": "plan",
            "stats": {
                "input_tokens": 1250,
                "output_tokens": 3400,
                "duration_ms": 8500,
            },
        }
        (llm_dir / "001_plan_response.json").write_text(json.dumps(response_data))

        runs_dir = tmp_path / "runs"
        result = _load_llm_stats(runs_dir, "01TESTRUNID0000000000000A", "plan")

        assert result is not None
        assert result["input_tokens"] == 1250
        assert result["output_tokens"] == 3400

    def test_returns_none_when_no_file(self, tmp_path: Path) -> None:
        """Returns None when no LLM response file exists."""
        from adw.dashboard.routes import _load_llm_stats

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        result = _load_llm_stats(runs_dir, "01TESTRUNID0000000000000A", "plan")
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path: Path) -> None:
        """Returns None when response file contains invalid JSON."""
        from adw.dashboard.routes import _load_llm_stats

        llm_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "llm"
        llm_dir.mkdir(parents=True)
        (llm_dir / "001_plan_response.json").write_text("not json")

        runs_dir = tmp_path / "runs"
        result = _load_llm_stats(runs_dir, "01TESTRUNID0000000000000A", "plan")
        assert result is None


class TestLoadLLMContent:
    """Tests for _load_llm_content helper."""

    def test_loads_response_content_from_artifact(self, tmp_path: Path) -> None:
        """Loads LLM response text from artifacts directory."""
        from adw.dashboard.routes import _load_llm_content

        artifacts_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "artifacts" / "plan"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "plan_output.md").write_text("Generated plan content")

        runs_dir = tmp_path / "runs"
        result = _load_llm_content(runs_dir, "01TESTRUNID0000000000000A", "plan", "response")
        assert result == "Generated plan content"

    def test_returns_none_when_no_artifact(self, tmp_path: Path) -> None:
        """Returns None when no artifact file exists."""
        from adw.dashboard.routes import _load_llm_content

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        result = _load_llm_content(runs_dir, "01TESTRUNID0000000000000A", "plan", "response")
        assert result is None

    def test_returns_none_for_prompt_when_no_file(self, tmp_path: Path) -> None:
        """Returns None for prompt when no prompt file exists."""
        from adw.dashboard.routes import _load_llm_content

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        result = _load_llm_content(runs_dir, "01TESTRUNID0000000000000A", "plan", "prompt")
        assert result is None
