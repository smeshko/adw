# Epic List

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 1 | Project Scaffolding & Test Infrastructure | Establish project foundation with Pydantic models, exception hierarchy, and MockExecutor for test enablement | P0 | P0 (models, exceptions) |
| 2 | Command Resolution & Templates | Enable command/prompt resolution with three-tier hierarchy and template variable substitution | P1 | P1 (template.py) |
| 3 | Hook & Phase Execution | Execute shell hooks and LLM calls within phases with streaming, retry, timeout, and **security guardrails** | P1 | P1/P2 (executor, hooks) |
| 4 | State Persistence & Context Management | Persist run state with atomic writes, snapshots, and artifact storage for resumability | P1 | P1 (context_manager, ASR-5) |
| 5 | Pipeline Orchestration | Coordinate phase execution in order, manage transitions, and handle artifacts | P2 | P2 (orchestrator) |
| 6 | Run Management & Recovery | Enable users to start, resume, abort, and monitor runs through CLI commands | P2 | E2E (cli/) |
| 7 | Observability & Logging | Provide multi-tier logging, state inspection, **workflow index**, and debugging capabilities | P3 | Integration |
| 8 | Evidence Gathering | Capture platform-appropriate evidence during Verify phase | P3 | Integration |
| 9 | Git Integration & Documentation | Support git workflows and generate PR-ready documentation | P4 | Integration |

---

## Post-MVP Epics

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 10 | Worktree Isolation | Enable concurrent workflow execution via git worktrees with port allocation | Post-MVP | Integration |
| 11 | Validation Loop | Iterative review→fix cycle with issue triage (FIX/DISMISS/DEFER) | Post-MVP | Integration |
| 12 | Task Manager Integration | Enable runs from Linear/Jira/GitHub Issues with auto-fetch, status comments, label management, and issue closing | Post-MVP | Integration |
| 13 | Webhook Infrastructure | Generic webhook server with Linear provider first, GitHub later | Post-MVP | Integration |
| 14 | Interactive Init Wizard | Guided setup wizard for first-time users covering all configuration options | Post-MVP | Integration |
| 15 | Ship Phase & Deployment | Automate PR approval, merge, and project-specific deployment hooks | Post-MVP | Integration |
| 16 | Cross-Project Dashboard | Aggregate runs across projects with analytics, token tracking, and dashboard views | Post-MVP | Integration |
| 17 | Validation Simplification | Rework Epic 11 to single-call validation with LLM handling iteration | Post-MVP | Integration |

---

## Course Correction Summary (2026-01-18)

**Epic 14: Interactive Init Wizard** — New feature to guide first-time users through configuration:
- Guided vs minimal setup choice on `adw init`
- Covers: basics, git, ports, task manager, phases, LLM retry, security, webhooks
- 10 stories across 4 implementation waves
- Estimated effort: ~4 days

---

## Course Correction Summary (2026-01-08)

**Epic 17: Validation Simplification** (was Epic 16) — Created to rework Epic 11's over-engineered validation loop:
- SDK makes single executor call (~5 lines of code)
- LLM handles entire validate→fix→re-validate cycle in one prompt
- Remove triage system, loop controller, fix engine (~850 lines deleted)
- Simplify configuration from 13+ fields to 3 fields
- 4 stories to implement the simplification:
  - 17.1: Remove SDK Validation Loop (WAVE 1)
  - 17.2: Create Unified Validation Prompt (WAVE 1)
  - 17.3: Simplify Configuration (WAVE 2)
  - 17.4: Update Phase Result Model (WAVE 2)

See: `sprint-change-proposal-2026-01-08.md` for full rationale.

---

## Course Correction Summary (2026-01-03)

The following changes were made based on gap analysis comparing adw-final to adw-sdk:

### Post-MVP Epics (Renumbered 2026-01-18)
- **Epic 10: Worktree Isolation** — Concurrent workflow execution via git worktrees (6 stories)
- **Epic 11: Validation Loop** — Iterative review→fix cycle with triage (7 stories)
- **Epic 12: Task Manager Integration** — Extended with full task lifecycle
- **Epic 13: Webhook Infrastructure** — Event-driven workflow triggers (7 stories)
- **Epic 14: Interactive Init Wizard** — Guided setup wizard (10 stories) [NEW 2026-01-18]
- **Epic 15: Ship Phase & Deployment** — PR approval, merge, deployment hooks (6 stories) [was Epic 14]
- **Epic 16: Cross-Project Dashboard** — Analytics and dashboard views [was Epic 15]
- **Epic 17: Validation Simplification** — Single-call validation (4 stories) [was Epic 16]

### Extended Epics
- **Epic 3** — Added security hooks (3 new stories: 3.X, 3.Y, 3.Z)
- **Epic 7** — Added workflow execution index (Story 7.0, pulled to MVP)
- **Epic 12** — Extended with full task lifecycle (5 new stories: 12.6-12.10)

### Architecture Updates
- Added model configuration per phase
- Updated pipeline flow for validation loop

---
