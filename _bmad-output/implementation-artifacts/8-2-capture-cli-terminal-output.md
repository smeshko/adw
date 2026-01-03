# Story 8.2: Capture CLI Terminal Output

Status: ready-for-dev
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-03

---

## Story

As a developer,
I want terminal output captured for CLI projects,
so that command execution can be verified.

## Acceptance Criteria

**Given** CLI platform type
**When** evidence gathering runs
**Then** configured commands are executed and output captured

**Given** commands from project.yaml `evidence.commands`
**When** each command executes
**Then** stdout and stderr are captured to `evidence/<cmd_name>.txt`

**Given** command output
**When** captured
**Then** it includes: command executed, exit code, duration, full output

**Given** command fails (non-zero exit)
**When** capturing
**Then** failure is recorded but doesn't fail the phase

**Given** evidence capture
**When** complete
**Then** exit codes are summarized (X passed, Y failed)

## Tasks / Subtasks

### Task 1: Create CLI Evidence Models (models/evidence.py)
- [ ] Create `CLIEvidenceConfig` model for command configuration
- [ ] Create `CommandResult` model with command, exit_code, duration, stdout, stderr
- [ ] Create `CLIEvidenceSummary` model for aggregate results
- [ ] Export from `models/__init__.py`

### Task 2: Implement Command Executor (evidence/cli_capture.py)
- [ ] Create `CLICaptureStrategy` class
- [ ] Implement `execute_command(cmd: str, timeout: int) -> CommandResult`
- [ ] Use `subprocess.run()` with capture_output=True
- [ ] Capture stdout, stderr, exit code, and duration
- [ ] Handle timeout gracefully with TimeoutExpired

### Task 3: Implement Evidence File Writer
- [ ] Create evidence directory structure: `.adw/runs/<run_id>/evidence/cli/`
- [ ] Write individual command results to `<cmd_name>.txt`
- [ ] Include header with command, timestamp, duration, exit code
- [ ] Append stdout and stderr with clear section markers

### Task 4: Implement Config-Based Command Loading
- [ ] Read `evidence.commands` from `.adw/project.yaml`
- [ ] Support command configuration format:
  ```yaml
  evidence:
    commands:
      - name: "version"
        cmd: "adw --version"
        timeout: 30
      - name: "help"
        cmd: "adw --help"
        timeout: 30
  ```
- [ ] Validate command configuration
- [ ] Handle missing config gracefully (skip with warning)

### Task 5: Implement Summary Generation
- [ ] Track passed/failed command counts
- [ ] Generate summary output: "X passed, Y failed"
- [ ] Create summary file with all command results
- [ ] Log summary to console via LogManager

### Task 6: Integrate with Verify Phase
- [ ] Wire CLICaptureStrategy into evidence gathering
- [ ] Execute only when platform is CLI
- [ ] Store results for manifest generation (Story 8.5)
- [ ] Return structured results for phase runner

### Task 7: Write Unit Tests
- [ ] Test command execution with mock subprocess
- [ ] Test output capture (stdout, stderr)
- [ ] Test timeout handling
- [ ] Test non-zero exit code handling
- [ ] Test evidence file writing
- [ ] Test summary generation
- [ ] Test config loading

---

## Relevant Feature Documentation

**From Architecture (Evidence Gathering MVP):**
> MVP Scope:
> - Terminal output capture for CLI commands
> - JSON response storage in `artifacts/verify/`

---

## Developer Context

### Technical Requirements

**From PRD FR13-FR18 (Verify Phase):**
- FR15: CLI projects capture terminal output
- FR14: Evidence stored in run artifacts directory
- FR18: Evidence failure doesn't fail the phase

**From Epic 8.2 Acceptance Criteria:**
- Commands defined in `evidence.commands` config
- Output includes: command, exit code, duration, full output
- Failures recorded but don't fail phase
- Summary shows X passed, Y failed

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create/Modify:**
```
src/adw/evidence/
├── __init__.py         # Package exports (update)
├── detector.py         # From Story 8.1
├── cli_capture.py      # CLI evidence capture (NEW)
└── strategies/
    ├── __init__.py
    └── cli.py          # CLICaptureStrategy (NEW)

src/adw/models/
└── evidence.py         # Add CLI-specific models (MODIFY)
```

**Evidence Output Structure:**
```
.adw/runs/<run_id>/
└── evidence/
    └── cli/
        ├── version.txt      # Individual command output
        ├── help.txt
        └── summary.json     # Aggregate results
```

**Dependencies:**
- subprocess (stdlib) for command execution
- Pydantic for models (already installed)
- PyYAML for config loading (already installed)

**Integration Points:**
- Uses `PlatformDetector` from Story 8.1
- Results used by Story 8.5 (manifest generation)
- Results compressed by Story 8.6

### Library & Framework Requirements

**Subprocess Execution:**
```python
import subprocess
from datetime import datetime, timedelta

def execute_command(cmd: str, timeout: int = 30) -> CommandResult:
    start = datetime.now()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = (datetime.now() - start).total_seconds()
        return CommandResult(
            command=cmd,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=duration,
            success=result.returncode == 0,
        )
    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start).total_seconds()
        return CommandResult(
            command=cmd,
            exit_code=-1,
            stdout="",
            stderr="Command timed out",
            duration_seconds=duration,
            success=False,
        )
```

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from datetime import datetime

class CommandConfig(BaseModel):
    name: str
    cmd: str
    timeout: int = 30

class CommandResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    success: bool
    executed_at: datetime = Field(default_factory=datetime.now)

class CLIEvidenceSummary(BaseModel):
    total_commands: int
    passed: int
    failed: int
    results: list[CommandResult]
```

### File Structure Requirements

**Evidence File Format (version.txt):**
```
================================================================================
COMMAND EVIDENCE
================================================================================
Command: adw --version
Executed: 2026-01-03T10:30:45Z
Duration: 0.125s
Exit Code: 0
Status: PASSED

================================================================================
STDOUT
================================================================================
adw version 1.0.0

================================================================================
STDERR
================================================================================
(empty)
```

**Summary File Format (summary.json):**
```json
{
  "captured_at": "2026-01-03T10:30:45Z",
  "platform": "cli",
  "total_commands": 5,
  "passed": 4,
  "failed": 1,
  "results": [
    {
      "name": "version",
      "command": "adw --version",
      "exit_code": 0,
      "duration_seconds": 0.125,
      "success": true
    }
  ]
}
```

### Testing Requirements

**Test File Structure:**
```
tests/unit/evidence/
├── __init__.py
├── test_detector.py      # From Story 8.1
├── test_cli_capture.py   # CLI capture tests (NEW)
└── fixtures/
    └── cli_configs/      # Test config files
```

**Testing Patterns:**
- Mock `subprocess.run()` for deterministic tests
- Use `tmp_path` for evidence output files
- Test timeout handling with mock
- Test various exit codes (0, 1, -1 timeout)

**Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 8.1 (Platform Detection):**
- `PlatformDetector` determines when CLI strategy is used
- Platform type stored in RunContext
- Evidence models in `models/evidence.py`

**From Epic 7 (Observability & Logging):**
- Use LogManager for execution logging
- Log each command start/end with structured context
- Reference: `src/adw/logging/manager.py`

**From Epic 3 (Hook Phase Execution):**
- Hook execution pattern similar to evidence commands
- Use similar subprocess patterns from `src/adw/hooks/runner.py`
- Shell execution with capture and timeout

---

## Git Intelligence

Recent commits show patterns for:
- Subprocess execution with capture in `hooks/runner.py`
- Pydantic model creation in `models/`
- File writing with atomic operations

---

## Latest Technical Information

**Python 3.13+ subprocess:**
```python
import subprocess

# Capture both stdout and stderr
result = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,  # Captures both stdout and stderr
    text=True,            # Return strings instead of bytes
    timeout=30,           # Timeout in seconds
)
```

**Timeout Handling:**
```python
try:
    result = subprocess.run(cmd, timeout=30, ...)
except subprocess.TimeoutExpired as e:
    # e.stdout and e.stderr contain partial output (if any)
    pass
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required
- Use Rich for CLI output formatting
- Context managers for file operations

---

## Dev Notes

- Command execution should be non-blocking to main phase
- Each command runs independently - one failure doesn't stop others
- Timeout is critical to prevent hung commands
- Consider adding working directory option for commands
- Evidence files should be human-readable

### Project Structure Notes

- Add `cli_capture.py` to `evidence/` package
- Update `evidence.py` models with CLI-specific types
- Evidence output goes to run directory under `evidence/cli/`

### References

- [Source: _bmad-output/architecture.md#Evidence-Gathering-MVP] - MVP scope
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md#Story-8.2] - Story definition
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: src/adw/hooks/runner.py] - Similar subprocess patterns

---

## Dependencies

- **Depends On:** Story 8.1 (Platform Detection)
- **Blocks:** Story 8.5, Story 8.6
- **Can Parallel With:** Story 8.3, Story 8.4

### Dependency Rationale
- Requires platform detection (8.1) to know when to use CLI strategy
- Produces evidence files consumed by manifest (8.5) and compression (8.6)
- Can be developed in parallel with web screenshots (8.3) and API capture (8.4)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

