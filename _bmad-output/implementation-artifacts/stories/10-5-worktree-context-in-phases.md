# Story 10.5: Worktree Context in Phases

Status: Draft
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want phases to execute in the worktree context,
so that file operations happen in the isolated environment.

## Acceptance Criteria

**Given** a phase executes
**When** LLM is invoked
**Then** working directory is set to worktree path

**Given** hooks execute
**When** environment is set up
**Then** `ADW_WORKTREE_PATH` is available

**Given** template variables
**When** rendered
**Then** `{{worktree_path}}` resolves to absolute worktree path

**Given** artifact paths
**When** stored in context
**Then** they're relative to worktree root

## Tasks / Subtasks

- [ ] Update `PhaseRunner` to accept worktree context:
  - Add `worktree_path: Path | None` parameter
  - Change working directory before LLM invocation
  - Restore original directory after phase completes
- [ ] Extend hook environment with worktree variables:
  - `ADW_WORKTREE_PATH` - absolute path to worktree
  - `ADW_PROJECT_ROOT` - original project root
  - `ADW_PORTS_FILE` - path to `.ports.env`
- [ ] Add template variables for worktree:
  - `{{worktree_path}}` - absolute worktree path
  - `{{worktree_relative_path}}` - relative from project root
  - `{{ports_file}}` - path to `.ports.env`
- [ ] Update `RunContext` model:
  - Add `worktree_path: Path | None`
  - Add `using_worktree: bool`
  - Update `artifacts_dir` to point to worktree `.adw/`
- [ ] Implement path resolution utilities:
  - `resolve_in_worktree(path: str, context: RunContext) -> Path`
  - `make_relative_to_worktree(path: Path, context: RunContext) -> str`
- [ ] Update artifact storage:
  - Store paths relative to worktree root
  - Resolve to absolute when reading
- [ ] Source `.ports.env` in hook execution:
  - Auto-source before hook script runs
  - Make port variables available to hooks
- [ ] Write unit tests for context integration
- [ ] Write integration tests for phase execution in worktree

---

## Developer Context

### Technical Requirements

- Use `os.chdir()` with context manager for directory changes
- Ensure cleanup happens even on exceptions
- Handle nested phase execution (directory already changed)
- Template rendering must work with both worktree and non-worktree modes
- Path resolution must be consistent across all phases

### Architecture Compliance

- Modify `src/adw/core/phase_runner.py`
- Extend `src/adw/models/context.py` (RunContext)
- Update `src/adw/commands/template.py` for new variables
- Extend `src/adw/hooks/executor.py` for environment vars
- No breaking changes to existing non-worktree execution

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| os | stdlib | Directory change, environment |
| pathlib | stdlib | Path manipulation |
| contextlib | stdlib | Context manager for cwd change |

### File Structure Requirements

```
src/adw/
├── core/
│   └── phase_runner.py     # Modify for worktree context
├── models/
│   └── context.py          # Extend RunContext
├── commands/
│   └── template.py         # Add worktree variables
├── hooks/
│   └── executor.py         # Extend environment
└── worktree/
    └── context.py          # NEW - worktree context utilities
```

### Testing Requirements

- Unit tests:
  - Template variable resolution
  - Path relativity conversion
  - Environment variable injection
- Integration tests:
  - Full phase execution in worktree
  - Hook execution with worktree env
  - Artifact storage paths
- Test both worktree and non-worktree modes

---

## Dependencies

- **Depends On:** 10.2 (Directory Structure), 10.4 (Concurrent Management)
- **Blocks:** None (final story in epic)
- **Can Parallel With:** None

### Dependency Rationale
- 10.2: Needs directory structure defined for file operations
- 10.4: Needs concurrent management to determine worktree context

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Context managers for resources (cwd change)
- Full type annotations
- Immutable state updates (model_copy)
- Structured logging

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `ADW_WORKTREE_PATH` | Absolute worktree path | `/project/trees/01HQ.../` |
| `ADW_PROJECT_ROOT` | Original project root | `/project/` |
| `ADW_PORTS_FILE` | Path to ports env | `/project/trees/01HQ.../.ports.env` |
| `BACKEND_PORT` | Allocated backend port (from .ports.env) | `9101` |
| `FRONTEND_PORT` | Allocated frontend port (from .ports.env) | `9201` |

---

## Template Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{{worktree_path}}` | Absolute worktree path | `/project/trees/01HQ.../` |
| `{{worktree_relative_path}}` | Relative path | `trees/01HQ.../` |
| `{{ports_file}}` | Ports env file path | `trees/01HQ.../.ports.env` |
| `{{backend_port}}` | Backend port number | `9101` |
| `{{frontend_port}}` | Frontend port number | `9201` |

---

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
