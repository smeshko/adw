# Agentic Development System - High-Level Architecture

## Overview

An agentic system for automating feature development through a phased pipeline. The system is designed around the following principles:

- **Phase-based workflow**: Plan → Build → Validate → Document → Ship
- **Pluggable commands**: Each phase has configurable prompts and scripts that users can override
- **Determinism first**: Anything that can be done in scripts should be done in scripts; LLM handles autonomous reasoning
- **Multiple entry points**: CLI, webhooks (Linear, GitHub), extensible triggers
- **Full observability**: Extensive logging and state management for debugging

---

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Entry Points                             │
├─────────────┬─────────────┬─────────────┬──────────────────────┤
│    CLI      │   Webhook   │   GitHub    │       Linear         │
│  (direct)   │   Server    │   Action    │      Webhook         │
└──────┬──────┴──────┬──────┴──────┬──────┴──────────┬───────────┘
       │             │             │                 │
       └─────────────┴─────────────┴─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator Core                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Context   │  │   Command   │  │    Phase Runner         │  │
│  │   Manager   │  │   Resolver  │  │  (deterministic logic)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase Pipeline                                │
│                                                                  │
│   ┌──────┐    ┌───────┐    ┌──────────┐    ┌─────┐    ┌──────┐ │
│   │ Plan │───▶│ Build │───▶│ Validate │───▶│ Doc │───▶│ Ship │ │
│   └──────┘    └───────┘    └──────────┘    └─────┘    └──────┘ │
│       │           │             │             │           │     │
│       ▼           ▼             ▼             ▼           ▼     │
│   [artifact]  [artifact]   [artifact]    [artifact]  [artifact]│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Command Layer                                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Resolution Order:                                           ││
│  │  1. ~/.config/agent/commands/     (user overrides)          ││
│  │  2. ./.agent/commands/            (project overrides)       ││
│  │  3. /defaults/commands/           (built-in defaults)       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LLM Executor                                │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │  Claude Code  │  │    Aider      │  │   Custom CLI Tool   │  │
│  └───────────────┘  └───────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Principles

### 1. Separation of Concerns: Scripts vs LLM

| Scripts Handle (Deterministic) | LLM Handles (Autonomous) |
|-------------------------------|--------------------------|
| Git operations | Planning & reasoning |
| File system operations | Code generation |
| Running tests/linters | Code review decisions |
| Deploying | Documentation writing |
| Parsing webhook payloads | Interpreting requirements |
| State management | Error recovery decisions |

### 2. Phase Artifacts & Context Accumulation

Each phase produces artifacts that feed into subsequent phases:

```
plan.md → changes.patch → test_results.json → docs.md → deploy_record.json
```

This creates an audit trail and allows resumption from any point.

### 3. Command Structure

Each command is a directory containing:

```
commands/
  plan/
    prompt.md          # The prompt template (supports variables)
    pre.sh             # Optional: runs before LLM
    post.sh            # Optional: runs after LLM
    config.yaml        # Phase-specific config
```

---

## Design Recommendations

### Determinism Boosters

- Use structured output schemas where possible (force LLM to output JSON matching a schema)
- Seed random values if the LLM tool supports it
- Cache intermediate results aggressively
- Version your prompts alongside your code

### Extensibility Ideas

- Plugin system for custom phases (not just plan→ship, but maybe `security-review` or `perf-test`)
- Middleware hooks between phases for custom logic
- Event system that plugins can subscribe to

### Resilience

- Checkpoint after each phase so you can resume
- Dry-run mode that shows what *would* happen
- Human-in-the-loop gates for critical phases (like `ship`)

### Webhook Design

- Map external events to phases intelligently:
  - Linear issue created → trigger `plan`
  - PR opened → trigger `validate`
- Queue system for handling concurrent triggers

---

## Directory Structure

```
.agent/
  project.yaml              # Project configuration
  CONVENTIONS.md            # Coding conventions for LLM
  commands/                 # Project-specific command overrides
    plan/
    build/
    validate/
  runs/                     # Execution history
    run_abc123/
      context.json
      artifacts/
      logs/

~/.config/agent/
  config.yaml               # Global configuration
  commands/                 # User-level command overrides
```

---

## Integration Points

### CLI

```bash
agent run "Add user authentication"           # Full pipeline
agent run --phase plan "Add user auth"        # Single phase
agent resume run_abc123                        # Resume from failure
agent status run_abc123                        # Check run status
```

### Webhooks

- HTTP server that accepts POST requests
- Normalizes payloads from different sources (Linear, GitHub, etc.)
- Maps events to appropriate phases
- Returns run ID for tracking

### GitHub Actions

- Can trigger on PR events, issue creation, etc.
- Uses CLI under the hood
- Reports status back to GitHub