# Epic List

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 1 | Project Scaffolding & Test Infrastructure | Establish project foundation with Pydantic models, exception hierarchy, and MockExecutor for test enablement | P0 | P0 (models, exceptions) |
| 2 | Command Resolution & Templates | Enable command/prompt resolution with three-tier hierarchy and template variable substitution | P1 | P1 (template.py) |
| 3 | Hook & Phase Execution | Execute shell hooks and LLM calls within phases with streaming, retry, and timeout support | P1 | P1/P2 (executor, hooks) |
| 4 | State Persistence & Context Management | Persist run state with atomic writes, snapshots, and artifact storage for resumability | P1 | P1 (context_manager, ASR-5) |
| 5 | Pipeline Orchestration | Coordinate phase execution in order, manage transitions, and handle artifacts | P2 | P2 (orchestrator) |
| 6 | Run Management & Recovery | Enable users to start, resume, abort, and monitor runs through CLI commands | P2 | E2E (cli/) |
| 7 | Observability & Logging | Provide multi-tier logging, state inspection, and debugging capabilities | P3 | Integration |
| 8 | Evidence Gathering | Capture platform-appropriate evidence during Verify phase | P3 | Integration |
| 9 | Git Integration & Documentation | Support git workflows and generate PR-ready documentation | P4 | Integration |

---

## Post-MVP Epics

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 10 | Cross-Project Dashboard | Aggregate runs across projects with analytics, token tracking, and dashboard views | Post-MVP | Integration |

---
