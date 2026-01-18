# ADW SDK - Documentation Index

**Project:** ADW (Agentic Development Workflow)
**Version:** 0.1.12
**Generated:** 2026-01-18

---

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Repository Type** | Monolith |
| **Primary Language** | Python 3.13 |
| **Framework** | FastAPI + Typer |
| **Architecture** | Layered Architecture |
| **Project Type** | Backend + CLI |

---

## Quick Reference

### Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.13 |
| CLI | Typer |
| Web | FastAPI |
| Validation | Pydantic v2 |
| HTTP | HTTPX |
| Testing | pytest |
| Build | hatchling |
| Package | uv |

### Entry Points

| Entry Point | Location |
|-------------|----------|
| CLI Command | `adw` → `adw.cli:app` |
| Module | `python -m adw` |
| Webhook Server | `adw webhook` |
| Orchestrator | `src/adw/core/orchestrator.py` |

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/adw/cli/` | CLI commands |
| `src/adw/core/` | Core orchestration |
| `src/adw/models/` | Data models (60+) |
| `src/adw/webhook/` | FastAPI server |
| `src/adw/executors/` | LLM integration |

---

## Generated Documentation

### Core Documentation

| Document | Description | Status |
|----------|-------------|--------|
| [Project Overview](project-overview.md) | Executive summary and metrics | ✓ |
| [Architecture Summary](architecture-summary.md) | System architecture overview | ✓ |
| [Development Guide](development-guide.md) | Setup and development commands | ✓ |
| [Source Tree Analysis](source-tree-analysis.md) | Annotated directory structure | ✓ |

### Technical Reference

| Document | Description | Status |
|----------|-------------|--------|
| [API Contracts](api-contracts-root.md) | Webhook API documentation | ✓ |
| [Data Models](data-models-root.md) | Pydantic model reference | ✓ |

### State

| File | Description |
|------|-------------|
| [Scan Report](project-scan-report.json) | Workflow execution state |

---

## Planning Artifacts

### Product Planning

| Document | Description | Status |
|----------|-------------|--------|
| [Product Brief](analysis/product-brief-adw-sdk-2025-12-30.md) | Initial product brief | ✓ |
| [PRD](prd.md) | Product Requirements Document | ✓ |
| [UX Design](ux-design-specification.md) | CLI UX specification | ✓ |

### Technical Planning

| Document | Description | Status |
|----------|-------------|--------|
| [Architecture](architecture.md) | Detailed architecture spec | ✓ |
| [Test Design](test-design-system.md) | Testing strategy | ✓ |
| [Implementation Readiness](implementation-readiness-report.md) | Pre-implementation validation | ✓ |
| [Project Context](project-context.md) | Context for AI agents | ✓ |

### Implementation

| Document | Description | Status |
|----------|-------------|--------|
| [Epics Index](epics/index.md) | Epic navigation | ✓ |
| [Epic List](epics/epic-list.md) | Complete epic list | ✓ |
| [Epic Overview](epics/overview.md) | Epic summary | ✓ |
| [Implementation Artifacts](implementation-artifacts/) | Story implementations | 90+ files |

---

## Existing Documentation

### Architecture Docs (`docs/`)

| Document | Description |
|----------|-------------|
| [High-Level Architecture](../docs/arch-high-level.md) | System overview |
| [Entry Point](../docs/arch-entry-point.md) | CLI entry documentation |
| [Command System](../docs/arch-command-system.md) | Command resolution |
| [Orchestrator](../docs/arch-orchestrator.md) | Orchestration engine |
| [Phase Pipeline](../docs/arch-phase-pipeline.md) | Phase execution |
| [LLM Executor](../docs/arch-llm-executor.md) | LLM integration |
| [Logging](../docs/arch-logging.md) | Logging infrastructure |

### Deep Dives (`docs/architecture/deep-dive/`)

| Document | Description |
|----------|-------------|
| [Orchestrator](../docs/architecture/deep-dive/orchestrator.md) | Orchestrator deep-dive |
| [Phase Runner](../docs/architecture/deep-dive/phase-runner.md) | Phase execution |
| [Plan Phase](../docs/architecture/deep-dive/plan-phase.md) | Plan phase details |
| [Build Phase](../docs/architecture/deep-dive/build-phase.md) | Build phase details |

### ADRs (`docs/architecture/adrs/`)

| Document | Description |
|----------|-------------|
| [ADR-001](../docs/architecture/adrs/ADR-001-test-reduction-strategy.md) | Test reduction strategy |

### Technical Debt (`docs/development/tech-debt/`)

| Document | Description |
|----------|-------------|
| [Orchestrator Phase Runner](../docs/development/tech-debt/orchestrator-phase-runner.md) | Refactoring notes |
| [Phase Runner Aliases](../docs/development/tech-debt/phase-runner-aliases.md) | Alias cleanup |
| [Resume Logic](../docs/development/tech-debt/resume-logic-centralization.md) | Centralization plan |

### Testing (`docs/testing/`)

| Document | Description |
|----------|-------------|
| [Test Reduction Plan](../docs/testing/TEST_REDUCTION_PLAN.md) | Test optimization |

### Other

| Document | Description |
|----------|-------------|
| [Conditional Docs](../docs/CONDITIONAL_DOCS.md) | Conditional documentation guide |
| [Templates](../docs/templates.md) | Template documentation |
| [Validation Analysis](../docs/analysis/validation-phase-redesign.md) | Validation phase analysis |

---

## Getting Started

### Quick Start

```bash
# Install dependencies
uv sync

# Run a workflow
adw run "Implement feature X"

# Check status
adw status

# List recent runs
adw list
```

### Development

```bash
# Run tests
uv run pytest

# Type check
uv run mypy src/adw

# Lint
uv run ruff check src/
```

### Webhook Server

```bash
# Start webhook server
adw webhook

# Server runs at http://0.0.0.0:8000
# Health check: GET /health
# Webhook: POST /webhook/{provider}
```

---

## Navigation by Role

### For Developers

1. Start with [Development Guide](development-guide.md)
2. Review [Source Tree](source-tree-analysis.md)
3. Understand [Architecture Summary](architecture-summary.md)

### For AI Agents

1. Load [Project Context](project-context.md)
2. Reference [Architecture](architecture.md) for decisions
3. Follow [Epics](epics/index.md) for implementation

### For Integrators

1. Review [API Contracts](api-contracts-root.md)
2. Check [Data Models](data-models-root.md)
3. See webhook providers in `src/adw/webhook/providers/`

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Documentation Files | 7 generated |
| Planning Artifacts | 8 files |
| Epics | 16 |
| Stories | 90+ |
| Source Modules | 14 |
| Test Coverage | 80%+ |
| Pydantic Models | 60+ |
| CLI Commands | 10 |
| API Endpoints | 2 |

---

*Index generated by document-project workflow v2.0.0*
