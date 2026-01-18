# Architecture Summary

## Project: ADW SDK (adw)

**Generated:** 2026-01-18
**Version:** 0.1.12
**Architecture Pattern:** Layered Architecture (CLI + SDK + Webhook Server)

---

## Executive Summary

The ADW SDK (Agentic Development Workflow) is a Python-based command-line SDK that orchestrates agentic development workflows by integrating with LLM tools (Claude Code CLI) to automate software development tasks. The system provides:

- **CLI Interface:** Command-line tool for running, managing, and monitoring workflow executions
- **Webhook Server:** FastAPI-based server for triggering workflows from external events (GitHub, Linear)
- **Orchestration Engine:** Phase-based execution pipeline with state management and recovery
- **Git Integration:** Worktree isolation, branch management, and PR creation

---

## Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Language** | Python | 3.13 |
| **CLI Framework** | Typer | >=0.21.0 |
| **Web Framework** | FastAPI | >=0.115.0 |
| **Web Server** | Uvicorn | >=0.32.0 |
| **Data Validation** | Pydantic | >=2.12.5 |
| **HTTP Client** | HTTPX | >=0.28.1 |
| **Build Tool** | Hatchling | - |
| **Package Manager** | uv | - |
| **Terminal UI** | Rich | >=14.2.0 |
| **Testing** | pytest | >=9.0.2 |
| **Type Checking** | mypy | >=1.19.1 |
| **Linting** | ruff | >=0.14.10 |

---

## Architecture Layers

### 1. Presentation Layer (CLI + Webhook)

```
┌─────────────────────────────────────────────────────┐
│                  Presentation Layer                  │
├─────────────────────────┬───────────────────────────┤
│      CLI (Typer)        │    Webhook (FastAPI)      │
│  ├── run               │    ├── /health           │
│  ├── resume            │    └── /webhook/{provider}│
│  ├── status            │                           │
│  ├── list              │   Providers:              │
│  ├── abort             │    ├── GitHub            │
│  ├── init              │    └── Linear            │
│  ├── logs              │                           │
│  ├── pr                │                           │
│  ├── webhook           │                           │
│  └── cleanup           │                           │
└─────────────────────────┴───────────────────────────┘
```

### 2. Domain Layer (Core)

```
┌─────────────────────────────────────────────────────┐
│                    Domain Layer                      │
├─────────────────────────────────────────────────────┤
│  Orchestrator                                        │
│  ├── Phase Pipeline (plan → build → validate → doc) │
│  ├── Context Management                             │
│  ├── State Snapshots                                │
│  └── Interruption Handling                          │
├─────────────────────────────────────────────────────┤
│  Commands                                            │
│  ├── YAML-based command definitions                 │
│  ├── Template rendering                             │
│  └── Variable substitution                          │
├─────────────────────────────────────────────────────┤
│  Validation                                          │
│  ├── Issue detection                                │
│  ├── Fix iteration loop                             │
│  └── Report generation                              │
└─────────────────────────────────────────────────────┘
```

### 3. Infrastructure Layer

```
┌─────────────────────────────────────────────────────┐
│                Infrastructure Layer                  │
├───────────────────┬─────────────────────────────────┤
│    Executors      │    Task Managers                │
│  ├── Claude Code  │  ├── Linear                    │
│  └── Mock         │  ├── GitHub                    │
│                   │  └── Null                       │
├───────────────────┼─────────────────────────────────┤
│    Git Hooks      │    Logging                      │
│  ├── Branch       │  ├── Console                   │
│  ├── Commit       │  ├── File                      │
│  └── Diff         │  ├── LLM Capture               │
│                   │  └── Redaction                 │
├───────────────────┼─────────────────────────────────┤
│    Worktree       │    Security                     │
│  ├── Manager      │  ├── Interceptor               │
│  ├── Ports        │  ├── Patterns                  │
│  └── Branches     │  └── Audit Logging             │
└───────────────────┴─────────────────────────────────┘
```

---

## Data Flow

### Run Execution Flow

```
User Request
     │
     ▼
┌──────────────────┐
│   CLI (Typer)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Config Loader  │  ← .adw/project.yaml
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Orchestrator   │  ← State Management
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Phase Pipeline  │
│  ┌────────────┐  │
│  │   Plan     │──┼─→ LLM Executor → Claude Code
│  └────────────┘  │
│  ┌────────────┐  │
│  │   Build    │──┼─→ LLM Executor → Claude Code
│  └────────────┘  │
│  ┌────────────┐  │
│  │  Validate  │──┼─→ LLM Executor → Claude Code
│  └────────────┘  │
│  ┌────────────┐  │
│  │  Document  │──┼─→ LLM Executor → Claude Code
│  └────────────┘  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Git Hooks      │  ← Commit, Branch, PR
└────────┬─────────┘
         │
         ▼
    Artifacts
```

### Webhook Trigger Flow

```
External Event (GitHub/Linear)
         │
         ▼
┌──────────────────┐
│  Webhook Server  │
│  (FastAPI)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Signature Verify │  ← Provider-specific
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Event Parser    │  ← Provider-specific
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Event Mapper    │  ← Mapping config
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Run Trigger     │  → CLI/Orchestrator
└──────────────────┘
```

---

## Key Design Decisions

### 1. Phase-Based Pipeline

The workflow is divided into distinct phases (plan, build, validate, document) with:
- Isolated execution per phase
- State snapshots between phases
- Independent retry and recovery
- Configurable phase enablement

### 2. Git Worktree Isolation

Concurrent runs are isolated using Git worktrees:
- Each run gets its own worktree
- Port allocation for parallel services
- Automatic cleanup on completion
- Artifact preservation options

### 3. Configuration-Driven

Behavior is controlled via YAML configuration:
- Project config: `.adw/project.yaml`
- Command definitions: YAML files with templates
- Webhook mappings: Event-to-run rules

### 4. Security First

Built-in security layer:
- Dangerous command pattern detection
- User override prompts for risky operations
- Secret redaction in logs
- Audit logging for tool calls

---

## Integration Points

| Integration | Protocol | Description |
|-------------|----------|-------------|
| Claude Code | CLI subprocess | LLM execution via Claude Code CLI |
| GitHub | REST API / Webhook | Issue/PR management, webhook triggers |
| Linear | GraphQL / Webhook | Issue management, webhook triggers |
| Git | CLI commands | Branch, commit, worktree operations |

---

## File Organization

```
src/adw/
├── cli/          # User interface layer
├── core/         # Domain logic
├── models/       # Data structures (60+ Pydantic models)
├── executors/    # LLM integration
├── webhook/      # External triggers
├── hooks/        # Git automation
├── security/     # Safety layer
├── validation/   # Quality checks
├── task_managers/# External task systems
├── worktree/     # Isolation management
└── logging/      # Observability
```

---

## Related Documentation

For detailed architecture information, see:

- **Planning Architecture:** `_bmad-output/architecture.md`
- **Deep Dives:** `docs/architecture/deep-dive/`
- **High-Level Overview:** `docs/arch-high-level.md`
- **Component Docs:** `docs/arch-*.md`
- **ADRs:** `docs/architecture/adrs/`

---

## Testing Strategy

| Test Type | Coverage | Location |
|-----------|----------|----------|
| Unit Tests | 80%+ | `tests/unit/` |
| Integration Tests | Core flows | `tests/integration/` |
| Type Checking | Strict | mypy |
| Linting | All code | ruff |

---

## Deployment Architecture

Currently designed for local development use:

- **CLI:** Installed via `pip install` or `uv sync`
- **Webhook Server:** Standalone FastAPI service on configurable port
- **No containerization:** (Dockerfile not present - local tool focus)
- **CI/CD:** GitHub Actions for lint, typecheck, test
