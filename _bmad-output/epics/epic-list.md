# Epic List

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 1 | Project Scaffolding & Test Infrastructure | Establish project foundation with Pydantic models, exception hierarchy, and MockExecutor for test enablement | P0 | P0 (models, exceptions) |
| 2 | Command Resolution & Templates | Enable command/prompt resolution with three-tier hierarchy and template variable substitution | P1 | P1 (template.py) |
| 3 | Hook & Phase Execution | Execute shell hooks and LLM calls within phases with streaming, retry, timeout, and **security guardrails** | P1 | P1/P2 (executor, hooks) |
| 4 | State Persistence & Context Management | Persist run state with atomic writes, snapshots, and artifact storage for resumability | P1 | P1 (context_manager, ASR-5) |
| 5 | Pipeline Orchestration | Coordinate phase execution in order, manage transitions, and handle artifacts | P2 | P2 (orchestrator) |
| 6 | Run Management & Recovery | Enable users to start, resume, abort, and monitor runs through CLI commands | P2 | E2E (cli/) |
| **12** | **Worktree Isolation** | **Enable concurrent workflow execution via git worktrees with port allocation** | **P2 (MVP)** | **Integration** |
| **15** | **Validation Loop** | **Iterative review→fix cycle with issue triage (FIX/DISMISS/DEFER)** | **P2 (MVP)** | **Integration** |
| 7 | Observability & Logging | Provide multi-tier logging, state inspection, **workflow index**, and debugging capabilities | P3 | Integration |
| 8 | Evidence Gathering | Capture platform-appropriate evidence during Verify phase | P3 | Integration |
| 9 | Git Integration & Documentation | Support git workflows and generate PR-ready documentation | P4 | Integration |

---

## Post-MVP Epics

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 10 | Cross-Project Dashboard | Aggregate runs across projects with analytics, token tracking, and dashboard views | Post-MVP | Integration |
| 11 | Task Manager Integration | Enable runs from Linear/Jira/GitHub Issues with auto-fetch, **status comments, label management, and issue closing** | Post-MVP | Integration |
| **13** | **Ship Phase & Deployment** | **Automate PR approval, merge, and project-specific deployment hooks** | **Post-MVP** | **Integration** |
| **14** | **Webhook Infrastructure** | **Generic webhook server with Linear provider first, GitHub later** | **Post-MVP** | **Integration** |

---

## Course Correction Summary (2026-01-03)

The following changes were made based on gap analysis comparing adw-final to adw-sdk:

### New MVP Epics
- **Epic 12: Worktree Isolation** — Concurrent workflow execution via git worktrees (6 stories)
- **Epic 15: Validation Loop** — Iterative review→fix cycle with triage (7 stories)

### New Post-MVP Epics
- **Epic 13: Ship Phase & Deployment** — PR approval, merge, deployment hooks (6 stories)
- **Epic 14: Webhook Infrastructure** — Event-driven workflow triggers (7 stories)

### Extended Epics
- **Epic 3** — Added security hooks (3 new stories: 3.X, 3.Y, 3.Z)
- **Epic 7** — Added workflow execution index (Story 7.0, pulled to MVP)
- **Epic 11** — Extended with full task lifecycle (5 new stories: 11.6-11.10)

### Architecture Updates
- Added model configuration per phase
- Updated pipeline flow for validation loop

---
