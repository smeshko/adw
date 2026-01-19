"""Shared pytest fixtures for ADW tests.

This module provides common fixtures for testing ADW components:
- tmp_adw_dir: Creates isolated .adw/ directory for testing
- mock_executor: Returns a fresh MockExecutor instance
- sample_run_context: Returns a valid RunContext with test data
- sample_project_config: Returns a valid ProjectConfig
- fixtures_path: Returns path to test fixtures directory
- isolated_global_index: Redirects global index to temp directory (autouse)
- git_repo: Creates isolated git repository with worktree cleanup (ISS-024)

IMPORTANT: ADW_MOCK_EXECUTOR is set at module load time to ensure all tests
(including subprocess-based integration tests) use MockExecutor instead of
hitting the real Claude API.
"""

import os
import shutil
import subprocess
from collections.abc import Generator

# Force mock executor for ALL tests - prevents hitting real Claude API
# This MUST be set before any test imports or runs
os.environ["ADW_MOCK_EXECUTOR"] = "1"

# Set dummy Linear credentials for tests that trigger task manager initialization
# This prevents ConfigError when running CLI commands that load project config
# with task_manager.type: linear (the real project config uses Linear)
os.environ.setdefault("LINEAR_API_KEY", "test-linear-api-key-for-tests")
os.environ.setdefault("LINEAR_TEAM_ID", "test-team-id-for-tests")

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
    # Use a separate directory for test index to avoid interfering with
    # tests that check for presence/absence of .adw/ directory
    test_index_dir = tmp_path / ".adw-test-index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    test_index_path = test_index_dir / "index.jsonl"
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


@pytest.fixture
def git_repo(tmp_path: Path) -> Generator[Path]:
    """Create an isolated git repository for testing with automatic cleanup.

    This fixture creates a temporary git repository with an initial commit,
    then cleans up any worktrees and branches created during the test.

    The fixture tracks worktrees created by tests and ensures they are
    properly removed during teardown, even if the test fails. This prevents
    orphaned worktrees from accumulating after test runs (ISS-024).

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Yields:
        Path to the created git repository.

    Example:
        >>> def test_worktree_creation(git_repo):
        ...     from adw.worktree.manager import WorktreeManager
        ...     manager = WorktreeManager(project_root=git_repo)
        ...     worktree = manager.create_worktree("test-run-id")
        ...     assert worktree.exists()
        ...     # Worktree is automatically cleaned up after test
    """
    # Initialize git repository
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit (required for worktree creation)
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repository")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    try:
        yield tmp_path
    finally:
        # Cleanup: Remove all worktrees and their branches
        _cleanup_worktrees(tmp_path)


def _cleanup_worktrees(repo_path: Path) -> None:
    """Clean up all worktrees and associated branches in a git repository.

    This helper function removes all git worktrees in the trees/ directory
    and deletes their associated adw/* branches.

    Args:
        repo_path: Path to the git repository root.
    """
    trees_dir = repo_path / "trees"
    if not trees_dir.exists():
        return

    # Get list of all worktrees before cleanup
    worktree_result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    # Parse worktree paths from porcelain output
    worktree_paths: list[str] = []
    for line in worktree_result.stdout.splitlines():
        if line.startswith("worktree "):
            path = line[9:]  # Remove "worktree " prefix
            # Skip the main worktree (repo_path itself)
            if Path(path) != repo_path:
                worktree_paths.append(path)

    # Remove each worktree with force flag
    for worktree_path in worktree_paths:
        subprocess.run(
            ["git", "worktree", "remove", worktree_path, "--force"],
            cwd=repo_path,
            capture_output=True,
        )

    # Clean up any remaining directories in trees/
    for item in trees_dir.iterdir():
        if item.is_dir() and item.name != ".locks" and item.name != ".gitignore":
            # Force remove directory if it still exists
            shutil.rmtree(item, ignore_errors=True)

    # Delete all adw/* branches
    branch_result = subprocess.run(
        ["git", "branch", "--list", "adw/*"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    for line in branch_result.stdout.splitlines():
        branch_name = line.strip().lstrip("* ")
        if branch_name:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=repo_path,
                capture_output=True,
            )


# NOTE: Session-scoped cleanup_orphaned_worktrees was removed (ISS-024 review).
# The git_repo fixture already cleans up worktrees via yield/finally.
# A session-scoped cleanup that scans the real project's trees/ directory
# is dangerous because it would delete legitimate developer worktrees
# (ADW production also creates ULID-named worktrees in trees/).
# Tests use tmp_path so they don't create orphans in the real project.
