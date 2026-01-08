"""Unit tests for LinearTaskManager.

Tests for the Linear task manager implementation.
"""

import os
from unittest.mock import patch

import pytest

from adw.exceptions import ConfigError
from adw.models.config import TaskManagerConfig
from adw.task_managers.linear import LinearTaskManager


class TestLinearTaskManagerInit:
    """Tests for LinearTaskManager initialization."""

    def test_init_with_valid_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LinearTaskManager initializes successfully with valid environment variables."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        assert manager.name == "linear"
        assert manager._config == config

    def test_init_missing_api_key_raises_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ConfigError when LINEAR_API_KEY is not set."""
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")

        with pytest.raises(ConfigError) as exc_info:
            LinearTaskManager(config)

        assert exc_info.value.code == "MISSING_LINEAR_API_KEY"
        assert "LINEAR_API_KEY" in exc_info.value.message

    def test_init_missing_team_id_raises_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ConfigError when LINEAR_TEAM_ID is not set."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.delenv("LINEAR_TEAM_ID", raising=False)

        config = TaskManagerConfig(type="linear", team_key="RULE")

        with pytest.raises(ConfigError) as exc_info:
            LinearTaskManager(config)

        assert exc_info.value.code == "MISSING_LINEAR_TEAM_ID"
        assert "LINEAR_TEAM_ID" in exc_info.value.message

    def test_name_property_returns_linear(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The name property returns 'linear'."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        assert manager.name == "linear"
