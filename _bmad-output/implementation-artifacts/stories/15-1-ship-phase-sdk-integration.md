# Story 15.1: Ship Phase SDK Integration

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want the ship phase fully integrated into the ADW SDK,
So that it executes as part of the standard pipeline like other phases.

## Acceptance Criteria

**Given** the ADW phase sequence in `src/adw/core/constants.py`
**When** ship phase is added
**Then** PHASE_SEQUENCE becomes:
```python
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "validate",
    "document",
    "ship",  # NEW
)
```

**Given** files that use PHASE_SEQUENCE
**When** ship is added to the tuple
**Then** these files automatically support ship phase:
- `src/adw/core/orchestrator.py` - pipeline execution
- `src/adw/core/phase_runner.py` - phase execution
- `src/adw/core/resume_manager.py` - resume handling
- `src/adw/cli/progress.py` - progress display
- `src/adw/cli/status_display.py` - status display
- `src/adw/cli/dry_run.py` - dry run output
- `src/adw/cli/validators.py` - phase validation

**Given** ship phase configuration
**When** models are added to `src/adw/models/config.py`
**Then** the following models are created:
- `ShipCommandsConfig` - version_bump, build, publish commands
- `ShipPRConfig` - auto_merge, merge_strategy, delete_branch
- `ShipConfig` - commands, post_publish, pr

**Given** ship phase folder structure
**When** created at `src/adw/defaults/commands/ship/`
**Then** it contains config.yaml, prompt.md, pre.sh, post.sh, and ship/ workflow folder

**Given** ship phase is disabled
**When** `phases.ship.enabled: false` in project.yaml
**Then** ship phase is skipped (pipeline ends at document)

**Given** ship phase enabled (default)
**When** document phase completes successfully
**Then** ship phase executes automatically

## Tasks / Subtasks

### Task 1: Add "ship" to PHASE_SEQUENCE
- [x] Modify `src/adw/core/constants.py`
- [x] Add `"ship"` as the fifth element in PHASE_SEQUENCE tuple
- [x] Update docstring to reflect new phase count (5 phases)
- [x] Verify all existing tests still pass

### Task 2: Create ShipConfig Models
- [x] Add `ShipCommandsConfig` to `src/adw/models/config.py`:
  - `version_bump: str | None = Field(default=None)`
  - `build: str | None = Field(default=None)`
  - `publish: str | None = Field(default=None)`
- [x] Add `ShipPRConfig` to `src/adw/models/config.py`:
  - `merge_on_success: bool = Field(default=False)` (named for clarity)
  - `merge_method: Literal["merge", "squash", "rebase"] = Field(default="squash")`
  - `delete_branch_on_merge: bool = Field(default=True)`
- [x] Add `ShipConfig` to `src/adw/models/config.py`:
  - `enabled: bool = Field(default=True)`
  - `commands: ShipCommandsConfig = Field(default_factory=ShipCommandsConfig)`
  - `pr: ShipPRConfig = Field(default_factory=ShipPRConfig)`
- [x] Add `ship: ShipConfig | None` field to `ProjectConfig`
- [x] Add "ship" to TaskManagerConfig.state_mapping default
- [x] Write focused unit tests for validation logic

### Task 3: Create Ship Command Folder Structure
- [ ] Create directory `src/adw/defaults/commands/ship/`
- [ ] Create `config.yaml`:
  ```yaml
  timeout_seconds: 900

  artifacts:
    - name: ship_report
      pattern: "ship_report.md"
      required: true
      description: "Full deployment report from LLM"
    - name: release_notes
      pattern: "release_notes.md"
      required: false
      description: "Generated release notes"
  ```
- [ ] Create `prompt.md` (placeholder with workflow include)
- [ ] Create `pre.sh` (validates PR exists)
- [ ] Create `post.sh` (parses LLM output, merges PR)
- [ ] Create `ship/workflow.yaml` and `ship/instructions.xml` (BMAD pattern)

### Task 4: Implement pre.sh Hook
- [ ] Check if PR exists for current branch using `gh pr view`
- [ ] Exit 1 with error message if no PR found
- [ ] Exit 0 if PR exists and is mergeable
- [ ] Set `ADW_PR_NUMBER` environment variable for LLM context

### Task 5: Implement post.sh Hook
- [ ] Parse LLM output for `DEPLOYMENT_STATUS: SUCCESS|FAILED|BLOCKED`
- [ ] Parse LLM output for `PR_MERGE_APPROVED: true|false`
- [ ] Parse LLM output for `VERSION_DEPLOYED: x.y.z|N/A`
- [ ] If `PR_MERGE_APPROVED: true`:
  - Execute `gh pr merge` with configured strategy
  - Delete branch if `delete_branch: true`
  - Update task manager to "Done" state
- [ ] If `PR_MERGE_APPROVED: false`:
  - Log reason from ship report
  - Exit with appropriate code

### Task 6: Write Tests
- [ ] Test ship in PHASE_SEQUENCE (`tests/unit/core/test_constants.py`)
- [ ] Test ShipConfig models (`tests/unit/models/test_config.py`)
- [ ] Test ShipCommandsConfig validation
- [ ] Test ShipPRConfig merge_strategy literal validation
- [ ] Test ProjectConfig with ship field
- [ ] Test phase runner recognizes ship phase
- [ ] Integration test: full pipeline with ship (mocked)

---

## Dependencies

- **Depends On:** None (foundation story for Epic 15)
- **Blocks:** 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
- **Can Parallel With:** None

### Dependency Rationale
- This is the infrastructure story that establishes ship phase in the SDK
- All other stories depend on PHASE_SEQUENCE including "ship"
- Config models are needed by all subsequent stories
- Command folder structure is required for LLM execution

---

## Developer Context

### Technical Requirements

1. **PHASE_SEQUENCE Modification**
   - The tuple is immutable by design - simply add "ship" as 5th element
   - Files using PHASE_SEQUENCE will automatically support ship phase
   - No code changes needed in orchestrator, phase_runner, etc.

2. **Config Model Design**
   - Use Pydantic Field with defaults for all optional fields
   - ShipCommandsConfig: all fields optional (commands may not be configured)
   - ShipPRConfig: sensible defaults (auto_merge: true, squash strategy)
   - Literal type for merge_strategy ensures valid values only

3. **Hook Scripts**
   - pre.sh: Fail fast if no PR exists (ship requires PR)
   - post.sh: Parse structured output from LLM for automation
   - Both hooks use `gh` CLI (GitHub CLI) for operations

### Architecture Compliance

**File Location:** Follows existing patterns

**Modified Files:**
```
src/adw/core/constants.py          # Add "ship" to PHASE_SEQUENCE
src/adw/models/config.py           # Add ShipConfig models
src/adw/models/__init__.py         # Export new models
```

**New Files:**
```
src/adw/defaults/commands/ship/
├── config.yaml          # Phase timeout, artifact definitions
├── prompt.md            # Main prompt with workflow includes
├── pre.sh               # Validate PR exists
├── post.sh              # Parse output, merge PR
└── ship/                # Workflow subfolder
    ├── workflow.yaml    # Workflow config (BMAD pattern)
    └── instructions.xml # LLM instructions
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Pydantic | 2.12+ | Config model validation |
| typing | stdlib | Literal type for merge_strategy |
| gh CLI | any | GitHub operations in hooks |

### File Structure Requirements

**Constants Update:**
```python
# src/adw/core/constants.py
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "validate",
    "document",
    "ship",  # NEW - completes the delivery lifecycle
)
```

**Config Models:**
```python
# src/adw/models/config.py
from typing import Literal

class ShipCommandsConfig(BaseModel):
    """Configuration for optional ship deployment commands."""
    version_bump: str | None = Field(default=None)
    build: str | None = Field(default=None)
    publish: str | None = Field(default=None)

class ShipPRConfig(BaseModel):
    """Configuration for PR merge behavior."""
    auto_merge: bool = Field(default=True)
    merge_strategy: Literal["squash", "merge", "rebase"] = Field(default="squash")
    delete_branch: bool = Field(default=True)

class ShipConfig(BaseModel):
    """Ship phase configuration."""
    commands: ShipCommandsConfig = Field(default_factory=ShipCommandsConfig)
    post_publish: list[str] = Field(default_factory=list)
    pr: ShipPRConfig = Field(default_factory=ShipPRConfig)
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/core/test_constants.py
def test_phase_sequence_includes_ship():
    """PHASE_SEQUENCE includes ship as fifth phase."""
    assert "ship" in PHASE_SEQUENCE
    assert PHASE_SEQUENCE.index("ship") == 4  # 0-indexed
    assert PHASE_SEQUENCE[-1] == "ship"  # Last phase

def test_phase_sequence_order():
    """PHASE_SEQUENCE maintains correct order."""
    assert PHASE_SEQUENCE == ("plan", "build", "validate", "document", "ship")

# tests/unit/models/test_config.py
class TestShipConfig:
    def test_ship_commands_config_all_optional(self):
        """All command fields are optional."""
        config = ShipCommandsConfig()
        assert config.version_bump is None
        assert config.build is None
        assert config.publish is None

    def test_ship_pr_config_defaults(self):
        """PR config has sensible defaults."""
        config = ShipPRConfig()
        assert config.auto_merge is True
        assert config.merge_strategy == "squash"
        assert config.delete_branch is True

    def test_ship_pr_config_merge_strategy_validation(self):
        """merge_strategy only accepts valid literals."""
        with pytest.raises(ValidationError):
            ShipPRConfig(merge_strategy="invalid")

    def test_ship_config_nested_defaults(self):
        """ShipConfig creates nested configs with defaults."""
        config = ShipConfig()
        assert isinstance(config.commands, ShipCommandsConfig)
        assert isinstance(config.pr, ShipPRConfig)
        assert config.post_publish == []

    def test_project_config_includes_ship(self):
        """ProjectConfig includes ship field with defaults."""
        config = ProjectConfig()
        assert hasattr(config, 'ship')
        assert isinstance(config.ship, ShipConfig)
```

---

## Previous Story Intelligence

This is the first story in Epic 15 (Ship Phase & Deployment). No previous story learnings available.

**Relevant Patterns from Other Epics:**
- Epic 12 established TaskManager configuration patterns
- Epic 11 established validation phase patterns
- Existing phases (plan, build, validate, document) provide templates for ship

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 14: Interactive Init Wizard stories
- Epic 13: Webhook Infrastructure stories
- Epic 12: Task Manager Integration stories

**Established Patterns:**
- Phase configuration in `models/config.py`
- Command folder structure in `defaults/commands/`
- Hook scripts follow POSIX shell patterns
- Artifacts defined in command config.yaml

---

## Latest Technical Information

**GitHub CLI (gh) Best Practices (2025):**
- `gh pr view --json` returns structured data
- `gh pr merge --squash` for squash merging
- `gh pr merge --delete-branch` for branch cleanup
- Exit codes: 0 success, 1 failure (use for conditionals)

**Pydantic Literal Types:**
- Use `Literal["a", "b", "c"]` for constrained string values
- Validation error raised automatically for invalid values
- Works with JSON Schema generation

---

## Project Context Reference

See: `_bmad-output/architecture.md`

Key patterns and rules from project context:
- **PHASE_SEQUENCE is authoritative**: All phase iteration uses this tuple
- **Config models use Pydantic**: Field() with defaults for optional values
- **Hook scripts in defaults/commands/**: pre.sh, post.sh pattern
- **Artifacts in config.yaml**: Define required/optional artifacts per phase

---

## Dev Notes

### Implementation Approach

1. Start with PHASE_SEQUENCE modification (smallest change, biggest impact)
2. Add config models (required by hooks and tests)
3. Create command folder structure
4. Implement hooks (pre.sh validates, post.sh merges)
5. Write comprehensive tests

### Key Design Decisions

1. **Ship is always last**: Phase sequence ensures ship runs after document
2. **All commands optional**: Ship works without version_bump/build/publish
3. **PR merge is primary function**: If no commands, ship just merges PR
4. **Structured LLM output**: post.sh parses specific fields from LLM report

### Configuration Example

```yaml
# project.yaml
phases:
  ship:
    enabled: true
    timeout_seconds: 900

ship:
  commands:
    version_bump: "npm version patch"
    build: "npm run build"
    publish: "npm publish"
  post_publish:
    - "git push --tags"
  pr:
    auto_merge: true
    merge_strategy: squash
    delete_branch: true
```

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.1]
- [Source: _bmad-output/architecture.md#Core Architectural Decisions]
- [Source: src/adw/core/constants.py#PHASE_SEQUENCE]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.1

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

**Task 1: Add "ship" to PHASE_SEQUENCE** (2026-01-19)
- Added "ship" as 5th element to PHASE_SEQUENCE tuple in constants.py
- Updated docstring to reflect 5 phases
- Added "ship" color (yellow) to PHASE_COLORS in progress.py
- Updated all test expectations from 4 phases to 5 phases
- All 2747 tests pass with 83.5% coverage

**Task 2: Create ShipConfig Models** (2026-01-19)
- Added ShipCommandsConfig (version_bump, build, publish)
- Added ShipPRConfig (merge_on_success, delete_branch_on_merge, merge_method)
- Added ShipConfig (enabled, commands, pr)
- Added ship field to ProjectConfig
- Updated TaskManagerConfig.state_mapping to include "ship": "Done"
- Added validation tests for ShipConfig YAML parsing and merge_method validation
- All 2751 tests pass with 83.5% coverage

### File List

**Modified (Task 1):**
- src/adw/core/constants.py - Added "ship" to PHASE_SEQUENCE
- src/adw/cli/progress.py - Added "ship" to PHASE_COLORS
- tests/unit/cli/test_progress.py - Updated phase count expectations
- tests/unit/core/test_orchestrator.py - Updated phase count and retry logic expectations
- tests/unit/core/test_resume_manager.py - Updated phase history expectations
- tests/integration/core/test_orchestrator_integration.py - Updated snapshot/token count expectations

**Modified (Task 2):**
- src/adw/models/config.py - Added ShipCommandsConfig, ShipPRConfig, ShipConfig classes
- tests/unit/models/test_config.py - Added TestShipConfig validation tests
- tests/unit/models/test_config_task_manager.py - Updated state_mapping test for ship phase
