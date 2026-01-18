# Source Tree Analysis

## Project: ADW SDK (adw)

**Generated:** 2026-01-18
**Architecture:** Layered Architecture (CLI + SDK + Webhook Server)
**Language:** Python 3.13

---

## Project Root Structure

```
adw-final/
├── .adw/                          # ADW project configuration
│   └── project.yaml               # Main project config ★ ENTRY POINT
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI pipeline (lint, typecheck, test)
├── docs/                          # Project documentation
│   ├── arch-*.md                  # Architecture documentation
│   ├── architecture/              # Deep-dive architecture docs
│   │   ├── adrs/                  # Architecture Decision Records
│   │   └── deep-dive/             # Component deep-dives
│   ├── development/               # Development docs
│   │   └── tech-debt/             # Technical debt tracking
│   └── testing/                   # Test documentation
├── src/                           # Source code root
│   └── adw/                       # Main package ★
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── _bmad/                         # BMAD methodology files
├── _bmad-output/                  # Planning artifacts
│   ├── epics/                     # Epic definitions
│   └── implementation-artifacts/  # Story implementations
├── pyproject.toml                 # Project manifest ★ ENTRY POINT
├── uv.lock                        # Dependency lock file
└── README.md                      # Project readme
```

---

## Source Package Structure (`src/adw/`)

```
src/adw/
├── __init__.py                    # Package init, version export
├── __main__.py                    # Module entry point ★ ENTRY POINT
├── exceptions.py                  # Custom exception hierarchy (26KB)
│
├── cli/                           # CLI Layer ★ PRIMARY INTERFACE
│   ├── __init__.py                # Typer app definition ★ ENTRY POINT
│   ├── run.py                     # `adw run` command
│   ├── resume.py                  # `adw resume` command
│   ├── status.py                  # `adw status` command
│   ├── list.py                    # `adw list` command
│   ├── abort.py                   # `adw abort` command
│   ├── init.py                    # `adw init` command
│   ├── pr.py                      # `adw pr` command
│   ├── webhook.py                 # `adw webhook` command
│   ├── cleanup.py                 # `adw cleanup` command
│   ├── dry_run.py                 # Dry run simulation
│   ├── validators.py              # CLI input validation
│   ├── run_display.py             # Run output formatting
│   ├── list_display.py            # List output formatting
│   └── status_display.py          # Status output formatting
│
├── core/                          # Core Domain Layer
│   ├── __init__.py                # Core exports
│   ├── orchestrator.py            # Main orchestration engine ★ CORE
│   ├── context_manager.py         # Run context management
│   ├── snapshot_manager.py        # State snapshot handling
│   ├── run_directory.py           # Run directory structure
│   ├── run_lookup.py              # Run ID resolution
│   ├── artifact_manager.py        # Artifact persistence
│   ├── index_manager.py           # Run index management
│   ├── resume_manager.py          # Resume logic
│   ├── interruption.py            # Interruption handling
│   └── constants.py               # Core constants
│
├── models/                        # Data Models Layer
│   ├── __init__.py                # Model exports (3KB)
│   ├── config.py                  # Configuration models (23KB)
│   ├── context.py                 # Context models (12KB)
│   ├── webhook.py                 # Webhook models (30KB)
│   ├── command.py                 # Command models (9KB)
│   ├── logging.py                 # Logging models (17KB)
│   ├── phase.py                   # Phase models (5KB)
│   ├── security.py                # Security models (5KB)
│   ├── pr.py                      # PR models (7KB)
│   ├── llm.py                     # LLM models (2KB)
│   ├── hook.py                    # Hook models (2KB)
│   ├── task.py                    # Task models (2KB)
│   ├── index.py                   # Index models (4KB)
│   ├── artifacts.py               # Artifact models (2KB)
│   ├── worktree.py                # Worktree models (2KB)
│   └── resume.py                  # Resume models (3KB)
│
├── executors/                     # LLM Execution Layer
│   ├── __init__.py                # Executor exports
│   ├── base.py                    # Base executor protocol
│   ├── claude_code.py             # Claude Code CLI executor ★ LLM INTEGRATION
│   ├── mock.py                    # Mock executor for testing
│   └── retry.py                   # Retry logic with backoff
│
├── webhook/                       # Webhook Server Layer ★ API
│   ├── __init__.py                # Webhook exports
│   ├── server.py                  # FastAPI application setup
│   ├── routes.py                  # API route handlers ★ API ENDPOINTS
│   ├── config.py                  # Webhook configuration
│   ├── middleware.py              # Request logging middleware
│   ├── security.py                # Signature verification
│   ├── mapping.py                 # Event-to-run mapping
│   ├── runner.py                  # Run triggering
│   └── providers/                 # Webhook providers
│       ├── __init__.py            # Provider exports
│       ├── base.py                # Base provider protocol
│       ├── registry.py            # Provider registry
│       ├── loader.py              # Dynamic provider loading
│       ├── github.py              # GitHub provider ★ INTEGRATION
│       └── linear.py              # Linear provider ★ INTEGRATION
│
├── commands/                      # Command Resolution Layer
│   ├── __init__.py                # Command exports
│   ├── loader.py                  # Command loading from YAML
│   └── validator.py               # Command validation
│
├── config/                        # Configuration Layer
│   ├── __init__.py                # Config exports
│   ├── loader.py                  # YAML config loading
│   ├── detector.py                # Project type detection
│   └── initializer.py             # Project initialization
│
├── hooks/                         # Git/Shell Hooks Layer
│   ├── __init__.py                # Hook exports
│   ├── runner.py                  # Hook execution engine
│   ├── git_branch.py              # Branch creation hooks
│   ├── git_commit.py              # Commit hooks
│   ├── git_diff.py                # Diff capture hooks
│   └── environment.py             # Environment setup
│
├── logging/                       # Logging Infrastructure
│   ├── __init__.py                # Logging exports
│   ├── manager.py                 # Log manager
│   ├── console.py                 # Console output
│   ├── file.py                    # File logging
│   ├── stream.py                  # Stream handling
│   ├── handler.py                 # Custom handlers
│   ├── llm_capture.py             # LLM interaction capture
│   └── redactor.py                # Secret redaction
│
├── security/                      # Security Layer
│   ├── __init__.py                # Security exports
│   ├── interceptor.py             # Command interceptor ★ SECURITY
│   ├── patterns.py                # Dangerous command patterns
│   ├── defaults.py                # Default security rules
│   ├── override.py                # Security overrides
│   ├── suggestions.py             # Safe alternatives
│   └── tool_logger.py             # Security audit logging
│
├── validation/                    # Validation Layer
│   ├── __init__.py                # Validation exports
│   ├── config.py                  # Validation configuration
│   ├── models.py                  # Validation models
│   ├── state_manager.py           # Validation state
│   ├── report.py                  # Validation reporting
│   └── validators/                # Custom validators
│
├── task_managers/                 # External Task Integration
│   ├── __init__.py                # Task manager exports
│   ├── base.py                    # Base task manager protocol
│   ├── factory.py                 # Task manager factory
│   ├── resolver.py                # Task ID resolution
│   ├── sync.py                    # State synchronization
│   ├── comments.py                # Comment handling
│   ├── null.py                    # Null implementation
│   ├── linear.py                  # Linear integration ★ INTEGRATION
│   ├── linear_client.py           # Linear API client
│   └── github_client.py           # GitHub API client
│
├── worktree/                      # Git Worktree Management
│   ├── __init__.py                # Worktree exports
│   ├── manager.py                 # Worktree lifecycle
│   ├── branch.py                  # Branch management
│   └── ports.py                   # Port allocation
│
├── utils/                         # Utility Functions
│   ├── __init__.py                # Utility exports
│   ├── ulid.py                    # ULID generation
│   └── diff.py                    # Diff utilities
│
├── defaults/                      # Default Commands
│   └── commands/                  # Bundled command templates
│       ├── build/
│       │   └── dev-story/         # Story implementation command
│       ├── document/              # Documentation commands
│       ├── plan/
│       │   └── create-story/      # Story creation command
│       └── validate/
│           └── code-review-loop/  # Code review command
│
└── evidence/                      # Evidence Collection
    └── (evidence capture utilities)
```

---

## Test Structure (`tests/`)

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/                          # Unit tests (~90 files)
│   ├── cli/                       # CLI command tests
│   ├── commands/                  # Command resolution tests
│   ├── config/                    # Configuration tests
│   ├── core/                      # Core logic tests
│   ├── executors/                 # Executor tests
│   ├── hooks/                     # Hook tests
│   ├── logging/                   # Logging tests
│   ├── models/                    # Model tests
│   ├── security/                  # Security tests
│   ├── task_managers/             # Task manager tests
│   ├── utils/                     # Utility tests
│   ├── validation/                # Validation tests
│   └── worktree/                  # Worktree tests
└── integration/                   # Integration tests
    ├── cli/                       # CLI integration tests
    ├── core/                      # Core integration tests
    └── worktree/                  # Worktree integration tests
```

---

## Entry Points Summary

| Entry Point | Location | Description |
|-------------|----------|-------------|
| CLI App | `src/adw/cli/__init__.py` | Typer application definition |
| Module Entry | `src/adw/__main__.py` | `python -m adw` entry |
| Package Script | `pyproject.toml` → `adw = "adw.cli:app"` | `adw` CLI command |
| Webhook Server | `src/adw/webhook/server.py` | FastAPI application |
| Orchestrator | `src/adw/core/orchestrator.py` | Main workflow engine |

---

## Integration Points

| Integration | Location | External System |
|-------------|----------|-----------------|
| Claude Code CLI | `executors/claude_code.py` | Anthropic Claude Code |
| GitHub Webhooks | `webhook/providers/github.py` | GitHub API |
| Linear Webhooks | `webhook/providers/linear.py` | Linear API |
| GitHub Tasks | `task_managers/github_client.py` | GitHub Issues/PRs |
| Linear Tasks | `task_managers/linear_client.py` | Linear Issues |

---

## Key File Sizes (by importance)

| File | Size | Purpose |
|------|------|---------|
| `models/webhook.py` | 30KB | Webhook data models |
| `exceptions.py` | 26KB | Exception hierarchy |
| `models/config.py` | 23KB | Configuration models |
| `models/logging.py` | 17KB | Logging models |
| `core/orchestrator.py` | ~15KB | Main orchestration |
| `models/context.py` | 12KB | Context models |
| `models/command.py` | 9KB | Command models |
