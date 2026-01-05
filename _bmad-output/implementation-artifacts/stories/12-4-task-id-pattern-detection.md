# Story 12.4: Task ID Pattern Detection

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want adw to auto-detect when I provide a task ID vs a feature string,
So that I don't need special flags.

## Acceptance Criteria

**Given** input "RULE-123"
**When** Linear configured with team_key: RULE
**Then** recognized as Linear task ID

**Given** input "Add user authentication"
**When** any task manager configured
**Then** treated as literal feature string

**Given** input "PROJECT-456"
**When** Linear configured with team_key: RULE
**Then** not recognized, treated as feature string

**Given** ambiguous input
**When** could be task ID or feature
**Then** explicit flag `--task-id` available for override

**Given** `--no-task-manager` flag
**When** provided with any input
**Then** input treated as literal feature string, no task manager used

## Tasks / Subtasks

- [ ] **Task 1**: Implement pattern detection in CLI run command
  - [ ] Add `--task-id` flag to force task ID interpretation
  - [ ] Add `--no-task-manager` flag to disable task manager
  - [ ] Auto-detect using `task_manager.resolve_task_id(input)`

- [ ] **Task 2**: Update `adw run` command logic
  - [ ] If `--task-id` flag: force task fetch
  - [ ] If `--no-task-manager` flag: use input as feature string
  - [ ] Otherwise: try resolve_task_id, fallback to feature string

- [ ] **Task 3**: Implement Linear team_key pattern matching
  - [ ] Pattern: `{TEAM_KEY}-{NUMBER}` (e.g., RULE-123)
  - [ ] team_key from config (case insensitive match)
  - [ ] Return full identifier if match, None otherwise

- [ ] **Task 4**: Handle multiple team keys
  - [ ] Support multiple team_keys in config (list)
  - [ ] Check input against all configured keys
  - [ ] First match wins

- [ ] **Task 5**: Add helpful error messages
  - [ ] If task ID detected but task not found: clear error
  - [ ] If `--task-id` with non-matching input: warning
  - [ ] Suggest `--no-task-manager` if fetch fails

- [ ] **Task 6**: Write unit tests
  - [ ] Test pattern matching for various inputs
  - [ ] Test flag overrides
  - [ ] Test case insensitivity
  - [ ] Test multiple team keys

---

## Developer Context

### Technical Requirements

This story improves UX by automatically detecting whether user input is a task ID or feature description. Pattern detection is based on team key prefix matching.

**Key Design Decisions:**
- Pattern: `^{TEAM_KEY}-\d+$` (case insensitive)
- Auto-detect first, flags override
- Multiple team keys supported for multi-team organizations

### Architecture Compliance

**Modified Files:**
```
src/adw/cli/
├── run.py       # Add flags and detection logic
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| re | stdlib | Regex pattern matching |
| typer | 0.21+ | CLI flags |

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/cli/run.py` - Add detection logic and flags
- `src/adw/task_managers/linear.py` - Update resolve_task_id

**New Files:**
- `tests/unit/cli/test_run_task_detection.py`

### Testing Requirements

```python
# tests/unit/cli/test_run_task_detection.py
def test_detects_linear_task_id():
    """Input matching team_key pattern detected as task ID."""
    resolver = TaskIdResolver(team_keys=["RULE", "ENG"])

    assert resolver.resolve("RULE-123") == "RULE-123"
    assert resolver.resolve("ENG-456") == "ENG-456"
    assert resolver.resolve("rule-789") == "RULE-789"  # Case insensitive

def test_feature_string_not_detected():
    """Regular text not detected as task ID."""
    resolver = TaskIdResolver(team_keys=["RULE"])

    assert resolver.resolve("Add user authentication") is None
    assert resolver.resolve("Fix bug in login") is None
    assert resolver.resolve("OTHER-123") is None  # Wrong team key

def test_task_id_flag_forces_detection():
    """--task-id flag forces input to be treated as task ID."""
    # Even if pattern doesn't match, treat as task ID

def test_no_task_manager_flag_disables():
    """--no-task-manager flag prevents any task detection."""
```

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManagerProtocol defines `resolve_task_id(input: str) -> str | None`
- TaskManagerConfig contains `team_key: str`

**From Story 12.2:**
- LinearTaskManager implements resolve_task_id
- Returns identifier if pattern matches, None otherwise

---

## Latest Technical Information

### Pattern Detection Regex

```python
import re

def resolve_task_id(self, input: str) -> str | None:
    """Check if input matches a task ID pattern."""
    for team_key in self.team_keys:
        pattern = rf"^{re.escape(team_key)}-(\d+)$"
        match = re.match(pattern, input, re.IGNORECASE)
        if match:
            # Return normalized identifier (uppercase team key)
            return f"{team_key.upper()}-{match.group(1)}"
    return None
```

### CLI Flag Design

```python
@app.command()
def run(
    feature_or_task: str = typer.Argument(..., help="Feature description or task ID"),
    task_id: bool = typer.Option(False, "--task-id", help="Force treat input as task ID"),
    no_task_manager: bool = typer.Option(False, "--no-task-manager", help="Disable task manager"),
):
    """Start a new ADW run."""
    task_manager = None if no_task_manager else get_task_manager(config)

    # Detect if input is task ID
    resolved_task_id = None
    if task_id:
        resolved_task_id = feature_or_task
    elif task_manager:
        resolved_task_id = task_manager.resolve_task_id(feature_or_task)

    if resolved_task_id:
        # Fetch task and use as feature
        task_info = task_manager.fetch_task(resolved_task_id)
        if not task_info:
            raise TaskError(f"Task not found: {resolved_task_id}")
        feature = f"{task_info.title}\n\n{task_info.description}"
    else:
        feature = feature_or_task
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- CLI options: `--kebab-case`
- Error messages: Include suggestions

---

## Dev Notes

### Configuration Example

```yaml
task_manager: linear
task_manager_config:
  team_key: RULE           # Single key
  # OR
  team_keys:               # Multiple keys
    - RULE
    - ENG
    - DOCS
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.4]
- [Source: src/adw/cli/run.py] - Existing run command

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1
- **Blocks:** None
- **Can Parallel With:** Story 12.2, Story 12.10

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with resolve_task_id method signature

