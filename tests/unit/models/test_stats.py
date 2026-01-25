"""Unit tests for statistics models.

Tests for TokenUsage, ProjectStatistics, and GlobalStatistics models.
"""

import pytest
from datetime import datetime, UTC


class TestTokenUsage:
    """Tests for TokenUsage model."""

    def test_total_tokens_property(self) -> None:
        """total_tokens returns sum of input and output."""
        from adw.models.stats import TokenUsage

        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_default_values(self) -> None:
        """Default values are zero."""
        from adw.models.stats import TokenUsage

        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_model_serialization(self) -> None:
        """Model can be serialized to dict and JSON."""
        from adw.models.stats import TokenUsage

        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        data = usage.model_dump()

        assert data["input_tokens"] == 1000
        assert data["output_tokens"] == 500
        # total_tokens is a property, not a field, so it won't be in dump
        assert "total_tokens" not in data

    def test_model_validation(self) -> None:
        """Model validates input types."""
        from adw.models.stats import TokenUsage

        # Should convert string to int
        usage = TokenUsage(input_tokens="100", output_tokens="50")  # type: ignore
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50


class TestProjectStatistics:
    """Tests for ProjectStatistics model."""

    def test_required_fields(self) -> None:
        """Required fields must be provided."""
        from adw.models.stats import ProjectStatistics

        stats = ProjectStatistics(name="my-project", path="/path/to/project")
        assert stats.name == "my-project"
        assert stats.path == "/path/to/project"

    def test_default_values(self) -> None:
        """Default values are properly initialized."""
        from adw.models.stats import ProjectStatistics, TokenUsage

        stats = ProjectStatistics(name="test", path="/test")
        assert stats.total_runs == 0
        assert stats.completed_runs == 0
        assert stats.failed_runs == 0
        assert stats.success_rate == 0.0
        assert stats.average_duration_ms == 0
        assert stats.estimated_cost == 0.0
        assert isinstance(stats.tokens, TokenUsage)
        assert stats.tokens.total_tokens == 0

    def test_with_values(self) -> None:
        """Can set all fields with values."""
        from adw.models.stats import ProjectStatistics, TokenUsage

        stats = ProjectStatistics(
            name="my-api",
            path="/Users/dev/my-api",
            total_runs=100,
            completed_runs=95,
            failed_runs=5,
            success_rate=0.95,
            average_duration_ms=120000,
            tokens=TokenUsage(input_tokens=1_000_000, output_tokens=100_000),
            estimated_cost=18.50,
        )

        assert stats.total_runs == 100
        assert stats.completed_runs == 95
        assert stats.failed_runs == 5
        assert stats.success_rate == 0.95
        assert stats.average_duration_ms == 120000
        assert stats.tokens.total_tokens == 1_100_000
        assert stats.estimated_cost == 18.50


class TestGlobalStatistics:
    """Tests for GlobalStatistics model."""

    def test_generated_at_required(self) -> None:
        """generated_at is a required field."""
        from adw.models.stats import GlobalStatistics

        now = datetime.now(UTC)
        stats = GlobalStatistics(generated_at=now)
        assert stats.generated_at == now

    def test_default_values(self) -> None:
        """Default values are properly initialized."""
        from adw.models.stats import GlobalStatistics, TokenUsage

        now = datetime.now(UTC)
        stats = GlobalStatistics(generated_at=now)

        assert stats.total_runs == 0
        assert stats.runs_this_week == 0
        assert stats.runs_today == 0
        assert stats.completed_runs == 0
        assert stats.failed_runs == 0
        assert stats.success_rate == 0.0
        assert stats.average_duration_ms == 0
        assert isinstance(stats.tokens, TokenUsage)
        assert stats.estimated_cost == 0.0
        assert stats.projects == []

    def test_includes_projects_list(self) -> None:
        """GlobalStatistics includes list of ProjectStatistics."""
        from adw.models.stats import GlobalStatistics, ProjectStatistics

        now = datetime.now(UTC)
        project1 = ProjectStatistics(
            name="project-a",
            path="/path/a",
            total_runs=50,
        )
        project2 = ProjectStatistics(
            name="project-b",
            path="/path/b",
            total_runs=30,
        )

        stats = GlobalStatistics(
            generated_at=now,
            total_runs=80,
            projects=[project1, project2],
        )

        assert len(stats.projects) == 2
        assert stats.projects[0].name == "project-a"
        assert stats.projects[1].name == "project-b"

    def test_full_statistics(self) -> None:
        """Can populate all statistics fields."""
        from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage

        now = datetime.now(UTC)
        stats = GlobalStatistics(
            generated_at=now,
            total_runs=1247,
            runs_this_week=89,
            runs_today=12,
            completed_runs=1175,
            failed_runs=72,
            success_rate=0.943,
            average_duration_ms=263000,
            tokens=TokenUsage(input_tokens=2_400_000, output_tokens=148_000),
            estimated_cost=47.82,
            projects=[
                ProjectStatistics(
                    name="adw-final",
                    path="/path/to/adw",
                    total_runs=423,
                    success_rate=0.962,
                )
            ],
        )

        assert stats.total_runs == 1247
        assert stats.runs_this_week == 89
        assert stats.runs_today == 12
        assert stats.completed_runs == 1175
        assert stats.failed_runs == 72
        assert stats.success_rate == 0.943
        assert stats.average_duration_ms == 263000
        assert stats.tokens.total_tokens == 2_548_000
        assert stats.estimated_cost == 47.82
        assert len(stats.projects) == 1

    def test_json_serialization(self) -> None:
        """GlobalStatistics can be serialized to JSON."""
        from adw.models.stats import GlobalStatistics, TokenUsage
        import json

        now = datetime.now(UTC)
        stats = GlobalStatistics(
            generated_at=now,
            total_runs=100,
            tokens=TokenUsage(input_tokens=1000, output_tokens=500),
        )

        json_str = stats.model_dump_json()
        data = json.loads(json_str)

        assert data["total_runs"] == 100
        assert data["tokens"]["input_tokens"] == 1000
        assert data["tokens"]["output_tokens"] == 500
        assert "generated_at" in data


class TestModelExports:
    """Tests that models are properly exported from the package."""

    def test_models_exported_from_stats(self) -> None:
        """Models can be imported from adw.models.stats."""
        from adw.models.stats import (
            GlobalStatistics,
            ProjectStatistics,
            TokenUsage,
        )

        assert TokenUsage is not None
        assert ProjectStatistics is not None
        assert GlobalStatistics is not None

    def test_models_exported_from_models_package(self) -> None:
        """Models can be imported from adw.models."""
        from adw.models import (
            GlobalStatistics,
            ProjectStatistics,
            TokenUsage,
        )

        assert TokenUsage is not None
        assert ProjectStatistics is not None
        assert GlobalStatistics is not None
