"""Task models for external task management integration.

This module defines models for representing tasks from external
task management systems (Linear, Jira, GitHub Issues, etc.).
"""

from typing import Any

from pydantic import BaseModel, Field


class TaskInfo(BaseModel):
    """Information about a task from an external task management system.

    This model provides a unified representation of tasks regardless of
    the source system (Linear, Jira, GitHub Issues, etc.).

    Example:
        >>> task = TaskInfo(
        ...     id="RULE-123",
        ...     identifier="RULE-123",
        ...     title="Implement user authentication",
        ...     description="Add OAuth2 support for user login",
        ...     status="In Progress",
        ...     priority=2,
        ...     labels=["feature", "auth"],
        ...     assignee="developer@example.com",
        ... )
    """

    id: str = Field(description="Task ID (e.g., 'RULE-123')")
    identifier: str = Field(description="Full identifier from system")
    title: str = Field(description="Task title/summary")
    description: str | None = Field(default=None, description="Task description/body")
    status: str | None = Field(
        default=None, description="Current status in external system"
    )
    priority: int | None = Field(
        default=None,
        description="Priority (1-4 or system-specific)",
        ge=1,
        le=4,
    )
    labels: list[str] = Field(default_factory=list, description="Task labels/tags")
    assignee: str | None = Field(default=None, description="Assignee name or email")
    parent_id: str | None = Field(default=None, description="Parent issue ID if exists")
    parent_title: str | None = Field(default=None, description="Parent issue title")
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description="Custom fields from system"
    )

    model_config = {"extra": "forbid"}
