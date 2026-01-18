# Project Overview

## ADW SDK (Agentic Development Workflow)

**Generated:** 2026-01-18
**Version:** 0.1.12
**Status:** Active Development

---

## Executive Summary

ADW (Agentic Development Workflow) is a Python-based SDK that orchestrates AI-assisted software development workflows. It provides a command-line interface and webhook server to automate development tasks by integrating with LLM tools like Claude Code CLI.

### Key Capabilities

- **Workflow Orchestration:** Phase-based pipeline (plan → build → validate → document)
- **LLM Integration:** Executes prompts via Claude Code CLI with retry and error handling
- **Git Automation:** Branch creation, commits, and PR generation
- **External Triggers:** Webhook server for GitHub and Linear event-driven workflows
- **Task Management:** Integration with Linear and GitHub for issue/PR synchronization
- **Isolation:** Git worktree support for concurrent parallel runs

---

## Technology Stack Summary

| Category | Technology |
|----------|------------|
| Language | Python 3.13 |
| CLI Framework | Typer |
| Web Framework | FastAPI |
| Data Validation | Pydantic v2 |
| HTTP Client | HTTPX |
| Terminal UI | Rich |
| Build Tool | Hatchling |
| Package Manager | uv |

---

## Architecture Classification

| Attribute | Value |
|-----------|-------|
| **Repository Type** | Monolith |
| **Project Type** | Backend + CLI |
| **Architecture Pattern** | Layered Architecture |
| **Primary Interface** | CLI (Typer) |
| **Secondary Interface** | Webhook API (FastAPI) |

---

## Repository Structure

```
adw-final/
├── src/adw/                # Main package (14 modules)
│   ├── cli/                # CLI commands
│   ├── core/               # Orchestration engine
│   ├── models/             # Pydantic models (60+)
│   ├── executors/          # LLM integration
│   ├── webhook/            # FastAPI server
│   └── ...                 # Supporting modules
├── tests/                  # Test suite (90+ files)
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Architecture documentation
├── _bmad-output/           # Planning artifacts
├── pyproject.toml          # Project manifest
└── .adw/project.yaml       # ADW configuration
```

---

## Key Features

### 1. Phase Pipeline
Configurable execution phases with independent enablement:
- **Plan:** Requirements analysis and task breakdown
- **Build:** Code implementation
- **Validate:** Code review and quality checks
- **Document:** Documentation generation

### 2. State Management
- Persistent run context with atomic writes
- State snapshots at phase boundaries
- Resume support for interrupted runs
- Artifact storage and retrieval

### 3. Security
- Dangerous command pattern detection
- User confirmation for risky operations
- Secret redaction in logs
- Tool call audit logging

### 4. External Integrations
- **Claude Code CLI:** LLM execution engine
- **GitHub:** Webhooks, Issues, PRs
- **Linear:** Webhooks, Issues

---

## Quick Start

```bash
# Install
uv sync

# Run a workflow
adw run "Implement feature X"

# Check status
adw status

# Start webhook server
adw webhook
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture Summary](architecture-summary.md) | System architecture overview |
| [Development Guide](development-guide.md) | Development setup and commands |
| [API Contracts](api-contracts-root.md) | Webhook API documentation |
| [Data Models](data-models-root.md) | Pydantic model reference |
| [Source Tree](source-tree-analysis.md) | Annotated directory structure |

### Planning Artifacts

| Document | Description |
|----------|-------------|
| [PRD](prd.md) | Product Requirements Document |
| [Architecture](architecture.md) | Detailed architecture specification |
| [UX Design](ux-design-specification.md) | CLI UX specification |
| [Test Design](test-design-system.md) | Testing strategy |
| [Epics](epics/index.md) | Implementation epics |

### Existing Documentation

| Location | Content |
|----------|---------|
| `docs/arch-*.md` | Component architecture docs |
| `docs/architecture/deep-dive/` | Deep-dive documentation |
| `docs/architecture/adrs/` | Architecture Decision Records |
| `docs/development/tech-debt/` | Technical debt tracking |

---

## Metrics

| Metric | Value |
|--------|-------|
| Source Files | ~100 Python files |
| Test Files | ~90 test files |
| Pydantic Models | 60+ |
| CLI Commands | 10 |
| API Endpoints | 2 |
| Epics | 16 |
| Implementation Stories | 90+ |
| Test Coverage | 80%+ |

---

## Contact

- **Project:** adw-sdk
- **Maintainer:** Ivo
