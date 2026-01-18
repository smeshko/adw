# Development Guide

## Project: ADW SDK (adw)

**Generated:** 2026-01-18
**Language:** Python 3.13
**Package Manager:** uv

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.13+ | Specified in `.python-version` |
| uv | Latest | Modern Python package manager |
| Git | 2.x+ | For worktree features |

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd adw-final
```

### 2. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

### 3. Verify Installation

```bash
# Check CLI is working
uv run adw --help
uv run adw --version
```

---

## Development Commands

### Running the CLI

```bash
# Run any ADW command
uv run adw <command>

# Examples:
uv run adw run "Implement feature X"
uv run adw status
uv run adw list
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/unit/cli/test_run.py

# Run with verbose output
uv run pytest -v

# Run without coverage requirement
uv run pytest --no-cov
```

### Type Checking

```bash
# Run mypy type checking
uv run mypy src/adw
```

### Linting

```bash
# Run ruff linting
uv run ruff check src/

# Run ruff format check
uv run ruff format --check src/

# Auto-fix lint issues
uv run ruff check --fix src/

# Auto-format code
uv run ruff format src/
```

### Building

```bash
# Build the package
uv build
```

---

## Project Configuration

### Main Configuration (`.adw/project.yaml`)

The ADW SDK is configured via `.adw/project.yaml`:

```yaml
name: adw
language: python
framework: fastapi
platform: cli

# Build/Test commands
test_command: pytest
build_command: uv build

# LLM Configuration
llm:
  path: claude
  timeout_seconds: 300
  max_retries: 3

# Git integration
git:
  enabled: true
  branch_prefix: "feature/"
  auto_commit: true
  auto_create_pr: true

# Worktree isolation
worktree:
  enabled: true
  base_dir: "trees"
```

### pyproject.toml

Key sections in `pyproject.toml`:

```toml
[project]
name = "adw"
requires-python = ">=3.13"

[project.scripts]
adw = "adw.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=adw", "--cov-fail-under=80"]

[tool.mypy]
python_version = "3.13"
strict = true

[tool.ruff]
target-version = "py313"
line-length = 88
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADW_LOG_LEVEL` | Logging verbosity | `INFO` |
| `ADW_CONFIG_PATH` | Custom config path | `.adw/project.yaml` |
| `CLAUDE_PATH` | Path to Claude CLI | `claude` |

---

## Code Style Guidelines

### Python Style

- **Line Length:** 88 characters (enforced by ruff)
- **Formatting:** Black-compatible (via ruff format)
- **Import Order:** isort-compatible (via ruff)
- **Type Hints:** Required (enforced by mypy strict mode)

### Linting Rules

Enabled ruff rules:
- `E`: pycodestyle errors
- `F`: Pyflakes
- `I`: isort
- `N`: pep8-naming
- `W`: pycodestyle warnings
- `UP`: pyupgrade
- `B`: flake8-bugbear
- `C4`: flake8-comprehensions
- `SIM`: flake8-simplify

### Test Requirements

- **Coverage:** Minimum 80% (enforced by pytest-cov)
- **Async:** Use `pytest-asyncio` for async tests
- **Markers:** Use `@pytest.mark.slow` and `@pytest.mark.integration`

---

## Directory Structure

```
src/adw/                    # Main package
├── cli/                    # CLI commands (Typer)
├── core/                   # Core domain logic
├── models/                 # Pydantic models
├── executors/              # LLM executors
├── webhook/                # FastAPI webhook server
├── logging/                # Logging infrastructure
├── security/               # Security patterns
├── hooks/                  # Git/shell hooks
├── validation/             # Output validation
├── task_managers/          # External integrations
├── worktree/               # Git worktree management
├── commands/               # Command resolution
├── config/                 # Configuration loading
└── utils/                  # Utilities

tests/                      # Test suite
├── unit/                   # Unit tests
└── integration/            # Integration tests
```

---

## Adding New Features

### 1. Adding a CLI Command

1. Create command file in `src/adw/cli/`
2. Add to the Typer app in `src/adw/cli/__init__.py`
3. Add unit tests in `tests/unit/cli/`
4. Add integration tests if needed

### 2. Adding a Model

1. Create/update model in `src/adw/models/`
2. Export from `src/adw/models/__init__.py`
3. Add model tests in `tests/unit/models/`

### 3. Adding a Webhook Provider

1. Create provider in `src/adw/webhook/providers/`
2. Implement `WebhookProvider` protocol from `base.py`
3. Register in provider registry
4. Add corresponding webhook models

---

## Debugging

### Verbose Logging

```bash
# Enable verbose output
uv run adw --verbose run "feature"

# Enable debug logging
ADW_LOG_LEVEL=DEBUG uv run adw run "feature"
```

### Dry Run Mode

```bash
# Preview what would happen
uv run adw run --dry-run "feature"
```

### Inspecting Runs

```bash
# View run logs
uv run adw logs <run-id>

# Check run status
uv run adw status <run-id>
```

---

## CI/CD Pipeline

The project uses GitHub Actions (`.github/workflows/ci.yml`):

| Job | Description |
|-----|-------------|
| `lint` | ruff check + format check |
| `typecheck` | mypy type checking |
| `test` | pytest with 80% coverage |

All jobs run on:
- Push to `main` and `staging`
- Pull requests to `main` and `staging`
