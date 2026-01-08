"""Tests for TaskInfo model.

Per ADR-001: Tests focus on validation logic and required fields,
not Pydantic serialization.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from adw.models.task import TaskInfo


class TestTaskInfo:
    """Tests for TaskInfo model validation."""

    def test_minimal_required_fields(self) -> None:
        """TaskInfo requires only id, identifier, and title."""
        task = TaskInfo(
            id="RULE-123",
            identifier="RULE-123",
            title="Test Task",
        )
        assert task.id == "RULE-123"
        assert task.identifier == "RULE-123"
        assert task.title == "Test Task"
        assert task.description is None
        assert task.status is None
        assert task.priority is None
        assert task.labels == []
        assert task.assignee is None
        assert task.parent_id is None
        assert task.parent_title is None
        assert task.custom_fields == {}

    def test_all_fields_populated(self) -> None:
        """TaskInfo accepts all optional fields."""
        task = TaskInfo(
            id="RULE-123",
            identifier="RULE-123",
            title="Implement feature",
            description="Add new feature to the system",
            status="In Progress",
            priority=2,
            labels=["feature", "backend"],
            assignee="developer@example.com",
            parent_id="RULE-100",
            parent_title="Epic: Authentication",
            custom_fields={"estimate": 5, "sprint": "2026-Q1"},
        )
        assert task.description == "Add new feature to the system"
        assert task.status == "In Progress"
        assert task.priority == 2
        assert task.labels == ["feature", "backend"]
        assert task.assignee == "developer@example.com"
        assert task.parent_id == "RULE-100"
        assert task.parent_title == "Epic: Authentication"
        assert task.custom_fields == {"estimate": 5, "sprint": "2026-Q1"}

    def test_priority_validation_min(self) -> None:
        """Priority must be >= 1."""
        with pytest.raises(PydanticValidationError) as exc_info:
            TaskInfo(
                id="RULE-123",
                identifier="RULE-123",
                title="Test",
                priority=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_priority_validation_max(self) -> None:
        """Priority must be <= 4."""
        with pytest.raises(PydanticValidationError) as exc_info:
            TaskInfo(
                id="RULE-123",
                identifier="RULE-123",
                title="Test",
                priority=5,
            )
        assert "less than or equal to 4" in str(exc_info.value)
