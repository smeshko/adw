# Story 1.5: Set Up pytest Infrastructure and Fixtures

Status: ready-for-dev
Linear Issue: not-configured
Epic: 1 - Project Scaffolding & Test Infrastructure
Created: 2025-12-31

---

## Story

As a developer,
I want pytest configured with coverage, async support, and shared fixtures,
so that I can write and run tests following the 60/30/10 pyramid.

## Acceptance Criteria

**Given** pyproject.toml
**When** I inspect pytest configuration
**Then** it specifies:
  - testpaths = ["tests"]
  - asyncio_mode = "auto"
  - addopts includes --cov=adw --cov-fail-under=80

**Given** tests/conftest.py
**When** I import fixtures
**Then** these fixtures are available:
  - `tmp_adw_dir`: Creates isolated `.adw/` in tmp_path
  - `mock_executor`: Returns a fresh MockExecutor
  - `sample_run_context`: Returns a valid RunContext with test data
  - `sample_project_config`: Returns a valid ProjectConfig

**Given** I run `uv run pytest tests/unit/`
**When** tests execute
**Then** they run in isolation with no shared state
**And** coverage report is generated

**Given** tests/fixtures/ directory
**When** I inspect its contents
**Then** it contains subdirectories: runs/, configs/, llm/ for JSON/YAML test data

## Tasks / Subtasks

### Task 1: Configure pytest in pyproject.toml
- [x] Add [tool.pytest.ini_options] section
- [x] Set testpaths = ["tests"]
- [x] Set asyncio_mode = "auto"
- [x] Add addopts with coverage configuration
- [x] Set python_files, python_classes, python_functions patterns

### Task 2: Create conftest.py with Core Fixtures
- [x] Create tests/conftest.py
- [x] Add tmp_adw_dir fixture using tmp_path
- [x] Add mock_executor fixture returning MockExecutor
- [x] Add sample_run_context fixture with valid test data
- [x] Add sample_project_config fixture

### Task 3: Create Test Data Fixtures Directory
- [x] Create tests/fixtures/ directory
- [x] Create tests/fixtures/runs/ for sample run data
- [x] Create tests/fixtures/configs/ for sample configs
- [x] Create tests/fixtures/llm/ for sample LLM responses

### Task 4: Add Sample Test Data Files
- [x] Create tests/fixtures/configs/minimal.yaml
- [x] Create tests/fixtures/configs/full.yaml
- [x] Create tests/fixtures/runs/completed_run/ sample

### Task 5: Verify Test Infrastructure
- [x] Run `uv run pytest --collect-only` to verify collection
- [x] Run `uv run pytest tests/unit/` to verify execution
- [x] Verify coverage report is generated
- [x] Verify 80% coverage threshold is enforced

### Task 6: Add CI Configuration
- [x] Update .github/workflows/ci.yml with test step
- [x] Add ruff check step
- [x] Add mypy check step
- [x] Add pytest with coverage step

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Test pyramid: 60% unit, 30% integration, 10% E2E
- Coverage requirement: >80% (NFR22)
- Test structure mirrors source structure
- MockExecutor for LLM testing

**Test Organization:**
```
tests/
├── conftest.py           # Shared fixtures
├── fixtures/             # Test data
│   ├── runs/
│   ├── configs/
│   └── llm/
├── unit/                 # Unit tests (60%)
│   └── (mirrors src/)
└── integration/          # Integration tests (30%)
```

### Architecture Compliance

**pytest Configuration in pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=adw",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

**Coverage Configuration:**
```toml
[tool.coverage.run]
source = ["src/adw"]
branch = true
omit = ["*/tests/*", "*/__main__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

### Library & Framework Requirements

**Fixture Implementations:**
```python
# tests/conftest.py
import pytest
from pathlib import Path
from datetime import datetime
from ulid import ULID

from adw.executors import MockExecutor
from adw.models import RunContext, ProjectConfig

@pytest.fixture
def tmp_adw_dir(tmp_path: Path) -> Path:
    """Create an isolated .adw/ directory for testing.

    Returns path to the .adw/ directory.
    """
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()

    # Create required subdirectories
    (adw_dir / "runs").mkdir()
    (adw_dir / "commands").mkdir()

    return adw_dir

@pytest.fixture
def mock_executor() -> MockExecutor:
    """Provide a fresh MockExecutor for each test."""
    return MockExecutor()

@pytest.fixture
def sample_run_context() -> RunContext:
    """Provide a valid RunContext with test data."""
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
    """Provide a valid ProjectConfig with test data."""
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
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_config_yaml(fixtures_path: Path) -> str:
    """Load sample config YAML."""
    config_file = fixtures_path / "configs" / "minimal.yaml"
    return config_file.read_text()
```

### File Structure Requirements

**Files to Create:**

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── fixtures/
│   ├── configs/
│   │   ├── minimal.yaml     # Minimal valid config
│   │   └── full.yaml        # Full config with all options
│   ├── runs/
│   │   └── completed_run/
│   │       ├── context.json
│   │       └── artifacts/
│   └── llm/
│       ├── success_response.json
│       └── tool_calls_response.json
├── unit/
│   ├── __init__.py
│   ├── cli/
│   │   └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── executors/
│   │   └── __init__.py
│   └── models/
│       └── __init__.py
└── integration/
    └── __init__.py
```

**Sample Fixture Files:**

**tests/fixtures/configs/minimal.yaml:**
```yaml
name: test-project
language: python
```

**tests/fixtures/configs/full.yaml:**
```yaml
name: test-project
language: python
framework: fastapi
platform: backend
test_command: pytest
build_command: uv build

llm:
  claude_code:
    path: /usr/local/bin/claude
    timeout_seconds: 300
    max_retries: 3
```

**tests/fixtures/llm/success_response.json:**
```json
{
  "success": true,
  "content": "Here is the generated code...",
  "tool_calls": [],
  "tokens_used": 150,
  "duration_ms": 2500
}
```

### Testing Requirements

**Test the Fixtures Themselves:**

```python
# tests/unit/test_fixtures.py
def test_tmp_adw_dir_fixture(tmp_adw_dir):
    """tmp_adw_dir creates proper structure."""
    assert tmp_adw_dir.exists()
    assert tmp_adw_dir.name == ".adw"
    assert (tmp_adw_dir / "runs").exists()
    assert (tmp_adw_dir / "commands").exists()

# Note: mock_executor fixture is not tested directly as MockExecutor
# is test infrastructure. It will be validated through actual usage.

def test_sample_run_context_fixture(sample_run_context):
    """sample_run_context returns valid RunContext."""
    from adw.models import RunContext
    assert isinstance(sample_run_context, RunContext)
    assert len(sample_run_context.run_id) == 26  # ULID length

def test_sample_project_config_fixture(sample_project_config):
    """sample_project_config returns valid ProjectConfig."""
    from adw.models import ProjectConfig
    assert isinstance(sample_project_config, ProjectConfig)
    assert sample_project_config.name == "test-project"
```

---

## Previous Story Intelligence

**Depends on All Previous Stories:**
- Story 1.1: Project structure with tests/ directory
- Story 1.2: RunContext, ProjectConfig models for fixtures
- Story 1.3: Exceptions (not directly, but useful for test scenarios)
- Story 1.4: MockExecutor for mock_executor fixture

**This is the Final Story in Epic 1:**
- Completes the test infrastructure foundation
- Enables all subsequent epics to write proper tests
- Establishes coverage requirements

---

## Git Intelligence

**Expected Prior Commits:**
- Story 1.1: Project scaffolding
- Story 1.2: Pydantic models
- Story 1.3: Exception hierarchy
- Story 1.4: MockExecutor

**Recommended Commit Pattern:**
```
feat(tests): set up pytest infrastructure and fixtures

- Configure pytest in pyproject.toml with coverage
- Add conftest.py with core fixtures
- Create fixture data directories (runs/, configs/, llm/)
- Add sample config YAML files
- Add sample run context JSON
- Verify test collection and execution
```

---

## Latest Technical Information

**pytest-asyncio Auto Mode:**
- asyncio_mode = "auto" automatically handles async tests
- No need for @pytest.mark.asyncio on every test
- Use when testing async code

**Coverage Best Practices:**
- Use branch coverage (branch = true)
- Exclude type checking blocks
- Set minimum threshold (80%)
- Generate term-missing report for visibility

**pytest Markers:**
- `@pytest.mark.slow` for long-running tests
- `@pytest.mark.integration` for integration tests
- Use `-m "not slow"` to skip slow tests locally

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Test files mirror source structure
- Use MockExecutor for LLM tests
- Coverage requirement: >80%

---

## Dev Notes

### Test Pyramid Strategy

| Layer | Percentage | Location | Characteristics |
|-------|------------|----------|-----------------|
| Unit | 60% | tests/unit/ | Fast, isolated, mock dependencies |
| Integration | 30% | tests/integration/ | Multiple components, real files |
| E2E | 10% | tests/e2e/ | Full CLI execution (future) |

### Fixture Design Principles

1. **Isolation:** Each test gets fresh fixtures
2. **Composability:** Fixtures can depend on other fixtures
3. **Realistic Data:** Sample data reflects real usage
4. **Convenience:** Common patterns available via fixtures

### CI Pipeline Integration

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Run linter
        run: uv run ruff check src/

      - name: Run type checker
        run: uv run mypy src/

      - name: Run tests
        run: uv run pytest --cov=adw --cov-fail-under=80
```

### References

- [Source: _bmad-output/architecture.md#Test-Organization]
- [Source: _bmad-output/architecture.md#Development-Workflow-Integration]
- [Source: _bmad-output/prd.md#NFR22]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Completion Notes List

(To be filled by dev agent after implementation)

### File List

(To be filled by dev agent after implementation)

---

## Dependencies

- **Depends On:** Story 1.1, Story 1.2, Story 1.3, Story 1.4
- **Blocks:** None
- **Can Parallel With:** None

### Dependency Rationale
- Story 1.1: Requires project structure with tests/ directory and pyproject.toml
- Story 1.2: RunContext, ProjectConfig models needed for sample fixtures
- Story 1.3: Exception types useful for test error scenarios
- Story 1.4: MockExecutor needed for mock_executor fixture
