"""Shared pytest fixtures for ADW tests.

This module provides common fixtures for testing ADW components:
- tmp_adw_dir: Creates isolated .adw/ directory for testing
- mock_executor: Returns a fresh MockExecutor instance
- sample_run_context: Returns a valid RunContext with test data
- sample_project_config: Returns a valid ProjectConfig
- fixtures_path: Returns path to test fixtures directory
- isolated_global_index: Redirects global index to temp directory (autouse)
"""

from datetime import datetime
from pathlib import Path

import pytest
from ulid import ULID

from adw.executors.mock import MockExecutor
from adw.models import ProjectConfig, RunContext


@pytest.fixture(autouse=True, scope="function")
def isolated_global_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Automatically isolate the global index for each test.

    This fixture runs automatically for every test (autouse=True) and
    redirects the global index from ~/.adw/index.jsonl to a temporary
    location. This prevents test runs from polluting the user's actual
    global index file.

    The ADW_TEST_INDEX_PATH environment variable is set to a temporary
    path, which the IndexManager will use instead of the default location.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.
        monkeypatch: Pytest's monkeypatch fixture for environment manipulation.

    Returns:
        Path to the isolated test index file.

    Note:
        This fixture is automatically applied to all tests. Individual tests
        that need to test the real index behavior can use monkeypatch to
        temporarily unset the environment variable.
    """
    test_index_path = tmp_path / ".adw" / "test-index.jsonl"
    test_index_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ADW_TEST_INDEX_PATH", str(test_index_path))
    return test_index_path


@pytest.fixture
def tmp_adw_dir(tmp_path: Path) -> Path:
    """Create an isolated .adw/ directory for testing.

    Creates the standard ADW directory structure in a temporary location.
    This ensures tests don't interfere with each other or with any real
    ADW installation.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Returns:
        Path to the created .adw/ directory.

    Example:
        >>> def test_something(tmp_adw_dir):
        ...     runs_dir = tmp_adw_dir / "runs"
        ...     assert runs_dir.exists()
    """
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()

    # Create required subdirectories
    (adw_dir / "runs").mkdir()
    (adw_dir / "commands").mkdir()

    return adw_dir


@pytest.fixture
def mock_executor() -> MockExecutor:
    """Provide a fresh MockExecutor for each test.

    Returns a new MockExecutor instance with no configured responses
    or failures. Use the executor's configuration methods to set up
    expected behavior.

    Returns:
        A fresh MockExecutor instance.

    Example:
        >>> def test_llm_call(mock_executor):
        ...     mock_executor.configure_responses([{"content": "Hello"}])
        ...     result = mock_executor.execute("Say hello")
        ...     assert result.content == "Hello"
    """
    return MockExecutor()


@pytest.fixture
def sample_run_context() -> RunContext:
    """Provide a valid RunContext with test data.

    Creates a RunContext instance with realistic test data that
    can be used in tests requiring run context information.

    Returns:
        A valid RunContext instance.

    Example:
        >>> def test_run_context(sample_run_context):
        ...     assert sample_run_context.status == "running"
        ...     assert len(sample_run_context.run_id) == 26
    """
    return RunContext(
        run_id=str(ULID()),
        feature_description="Add user authentication",
        current_phase="plan",
        phase_history=[],
        started_at=datetime.now(),
        artifacts={},
    )


@pytest.fixture
def sample_project_config() -> ProjectConfig:
    """Provide a valid ProjectConfig with test data.

    Creates a ProjectConfig instance with common test values
    that can be used in tests requiring project configuration.

    Returns:
        A valid ProjectConfig instance.

    Example:
        >>> def test_project_config(sample_project_config):
        ...     assert sample_project_config.name == "test-project"
        ...     assert sample_project_config.language == "python"
    """
    return ProjectConfig(
        name="test-project",
        language="python",
        framework="fastapi",
        platform="backend",
        test_command="pytest",
        build_command=None,
    )


@pytest.fixture
def fixtures_path() -> Path:
    """Return path to test fixtures directory.

    Provides the path to the tests/fixtures/ directory where
    sample data files are stored.

    Returns:
        Path to the fixtures directory.

    Example:
        >>> def test_load_config(fixtures_path):
        ...     config_file = fixtures_path / "configs" / "minimal.yaml"
        ...     assert config_file.exists()
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config_yaml(fixtures_path: Path) -> str:
    """Load sample config YAML content.

    Reads the minimal.yaml config file from fixtures and returns
    its content as a string.

    Args:
        fixtures_path: Path to fixtures directory (injected by pytest).

    Returns:
        YAML content as a string.

    Example:
        >>> def test_config_parsing(sample_config_yaml):
        ...     config = ProjectConfig.from_yaml(sample_config_yaml)
        ...     assert config.name == "test-project"
    """
    config_file = fixtures_path / "configs" / "minimal.yaml"
    return config_file.read_text()
