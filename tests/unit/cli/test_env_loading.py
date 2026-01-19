"""Unit tests for .env file loading in CLI bootstrap.

Tests for the _load_env_file() function that loads environment variables
from .adw/.env files (ISS-028).
"""

import os
from pathlib import Path

import pytest


class TestLoadEnvFile:
    """Tests for _load_env_file() function."""

    def test_loads_env_from_adw_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables are loaded from .adw/.env when file exists."""
        # Create .adw/.env with test variable
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        env_file = adw_dir / ".env"
        env_file.write_text("TEST_LINEAR_KEY=test_value_123\n")

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Ensure env var is not set before loading
        monkeypatch.delenv("TEST_LINEAR_KEY", raising=False)

        # Import and call the function
        from adw.cli.app import _load_env_file

        _load_env_file()

        # Verify env var was loaded
        assert os.environ.get("TEST_LINEAR_KEY") == "test_value_123"

    def test_silently_does_nothing_if_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No error raised when .adw/.env does not exist."""
        # Change to tmp directory (no .adw/.env file)
        monkeypatch.chdir(tmp_path)

        # Should not raise any exception
        from adw.cli.app import _load_env_file

        _load_env_file()  # Should complete without error

    def test_does_not_overwrite_existing_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Existing environment variables are not overwritten by .env file."""
        # Set env var before loading
        monkeypatch.setenv("EXISTING_VAR", "original_value")

        # Create .adw/.env with same variable
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        env_file = adw_dir / ".env"
        env_file.write_text("EXISTING_VAR=new_value\n")

        monkeypatch.chdir(tmp_path)

        from adw.cli.app import _load_env_file

        _load_env_file()

        # Original value should be preserved (dotenv default behavior)
        assert os.environ.get("EXISTING_VAR") == "original_value"

    def test_loads_multiple_variables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple environment variables are loaded from .env file."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        env_file = adw_dir / ".env"
        env_file.write_text(
            "LINEAR_API_KEY=lin_api_test\nLINEAR_TEAM_ID=team-uuid-456\n"
        )

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        monkeypatch.delenv("LINEAR_TEAM_ID", raising=False)

        from adw.cli.app import _load_env_file

        _load_env_file()

        assert os.environ.get("LINEAR_API_KEY") == "lin_api_test"
        assert os.environ.get("LINEAR_TEAM_ID") == "team-uuid-456"
