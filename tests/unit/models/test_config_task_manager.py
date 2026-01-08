"""Tests for TaskManagerConfig and TaskManagerLabelsConfig.

Per ADR-001: Tests focus on validation logic and required fields.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from adw.models.config import (
    ProjectConfig,
    TaskManagerConfig,
    TaskManagerLabelsConfig,
)


class TestTaskManagerLabelsConfig:
    """Tests for TaskManagerLabelsConfig."""

    def test_default_values(self) -> None:
        """Default values are sensible."""
        config = TaskManagerLabelsConfig()
        assert config.enabled is True
        assert config.prefix == "adw:"


class TestTaskManagerConfig:
    """Tests for TaskManagerConfig validation."""

    def test_default_values(self) -> None:
        """Default values are sensible."""
        config = TaskManagerConfig()
        assert config.type == "none"
        assert config.team_key is None
        assert config.sync_comments is False
        assert config.comment_on_failure_only is False
        assert config.auto_close is False
        assert config.include_labels is True
        assert config.include_parent is True
        assert config.labels.enabled is True
        assert config.labels.prefix == "adw:"

    def test_default_state_mapping(self) -> None:
        """Default state mapping is provided."""
        config = TaskManagerConfig()
        assert config.state_mapping == {
            "pending": "Todo",
            "running": "In Progress",
            "completed": "Done",
            "failed": "In Progress",
        }

    def test_custom_state_mapping(self) -> None:
        """Custom state mapping can be provided."""
        config = TaskManagerConfig(
            state_mapping={
                "pending": "Backlog",
                "running": "In Dev",
                "completed": "Done",
                "failed": "Blocked",
            }
        )
        assert config.state_mapping["pending"] == "Backlog"
        assert config.state_mapping["failed"] == "Blocked"

    def test_labels_nested_config(self) -> None:
        """Labels config can be customized."""
        config = TaskManagerConfig(
            labels=TaskManagerLabelsConfig(enabled=False, prefix="workflow:")
        )
        assert config.labels.enabled is False
        assert config.labels.prefix == "workflow:"

    def test_invalid_type_raises_validation_error(self) -> None:
        """Invalid task manager type raises ValidationError.

        Per AC: Given invalid task_manager value, When config is loaded,
        Then ConfigError raised with available options.
        """
        with pytest.raises(PydanticValidationError) as exc_info:
            TaskManagerConfig(type="invalid_type")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "type" in str(errors[0]["loc"])
        assert "'none'" in errors[0]["msg"]
        assert "'linear'" in errors[0]["msg"]


class TestProjectConfigTaskManager:
    """Tests for task_manager field in ProjectConfig."""

    def test_project_config_has_task_manager_field(self) -> None:
        """ProjectConfig includes task_manager field."""
        config = ProjectConfig(name="test", language="python")
        assert hasattr(config, "task_manager")
        assert isinstance(config.task_manager, TaskManagerConfig)

    def test_project_config_task_manager_defaults(self) -> None:
        """ProjectConfig task_manager has sensible defaults."""
        config = ProjectConfig(name="test", language="python")
        assert config.task_manager.type == "none"

    def test_project_config_yaml_with_task_manager(self) -> None:
        """TaskManager config can be loaded from YAML."""
        yaml_content = """
name: test-project
language: python
task_manager:
  type: linear
  team_key: RULE
  state_mapping:
    pending: "Backlog"
    running: "In Progress"
    completed: "Done"
    failed: "Blocked"
  sync_comments: true
  labels:
    enabled: true
    prefix: "ci:"
  auto_close: true
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.task_manager.type == "linear"
        assert config.task_manager.team_key == "RULE"
        assert config.task_manager.state_mapping["pending"] == "Backlog"
        assert config.task_manager.sync_comments is True
        assert config.task_manager.labels.prefix == "ci:"
        assert config.task_manager.auto_close is True
