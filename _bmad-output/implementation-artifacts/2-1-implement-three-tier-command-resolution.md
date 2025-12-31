# Story 2.1: Implement Three-Tier Command Resolution

Status: ready-for-dev
Linear Issue: not-configured
Epic: 2 - Command Resolution & Templates
Created: 2025-12-31

---

## Story

As a developer,
I want commands resolved from project, then user, then bundled defaults,
so that users can override any command at the appropriate level.

## Acceptance Criteria

**Given** a command name "plan"
**When** the resolver searches for it
**Then** it checks in order:
  1. `.adw/commands/plan/` (project level)
  2. `~/.adw/commands/plan/` (user level)
  3. Bundled defaults in package

**Given** a command exists at project level
**When** the same command exists at user and bundled level
**Then** the project-level command is used

**Given** a command exists only at bundled level
**When** project and user levels are empty
**Then** the bundled command is used

**Given** a command name that doesn't exist anywhere
**When** resolution is attempted
**Then** ConfigError is raised with code "COMMAND_NOT_FOUND" and helpful suggestion

**Given** a resolved command directory
**When** I inspect its contents
**Then** it contains: prompt.md, optionally schema.json, optionally pre-hook.sh, post-hook.sh

## Tasks / Subtasks

### Task 1: Create Command Resolution Module Structure
- [x] Create `src/adw/commands/__init__.py` with exports
- [x] Create `src/adw/commands/resolver.py` with `CommandResolver` class
- [x] Create `src/adw/commands/loader.py` with `CommandLoader` class

### Task 2: Implement ResolvedCommand Model
- [x] Add `ResolvedCommand` model to `src/adw/models/command.py`
- [x] Define fields: `name`, `path`, `tier`, `has_schema`, `has_pre_hook`, `has_post_hook`
- [x] Implement `model_validator` to verify directory structure

### Task 3: Implement Three-Tier Resolution Logic
- [x] Implement `resolve(command_name: str) -> ResolvedCommand`
- [x] Check project tier: `{project_root}/.adw/commands/{name}/`
- [x] Check user tier: `~/.adw/commands/{name}/` (expand `~`)
- [x] Check bundled tier: `adw/defaults/commands/{name}/` (package resources)
- [x] Return `ResolvedCommand` with `tier` indicating which level matched

### Task 4: Implement Error Handling
- [x] Raise `ConfigError(code="COMMAND_NOT_FOUND")` when command not found at any tier
- [x] Include `suggestion` field with available commands
- [x] Include command name in error message

### Task 5: Implement Command Directory Validation
- [x] Verify `prompt.md` exists in resolved directory (required)
- [x] Detect presence of `schema.json` (optional)
- [x] Detect presence of `pre-hook.sh` / `pre.sh` (optional)
- [x] Detect presence of `post-hook.sh` / `post.sh` (optional)
- [x] Raise `ConfigError(code="INVALID_COMMAND")` if prompt.md missing

### Task 6: Create Default Command Scaffolding
- [x] Create `defaults/commands/plan/` directory structure
- [x] Create `defaults/commands/build/` directory structure
- [x] Create `defaults/commands/verify/` directory structure
- [x] Create `defaults/commands/validate/` directory structure
- [x] Create `defaults/commands/document/` directory structure
- [x] Add minimal `prompt.md` placeholders to each

### Task 7: Write Unit Tests
- [ ] Test three-tier resolution priority (project > user > bundled)
- [ ] Test fallback behavior when tiers are empty
- [ ] Test `COMMAND_NOT_FOUND` error with helpful message
- [ ] Test `INVALID_COMMAND` error when prompt.md missing
- [ ] Test detection of optional files (schema, hooks)

---

## Relevant Feature Documentation

_No conditional docs matched for this story context._

---

## Developer Context

### Technical Requirements

- **FR19:** System resolves commands using three-tier hierarchy (project → user → default)
- **FR20:** User can override any command file at project level
- **FR21:** User can override any command file at user level
- Resolution must be deterministic: first match wins, no merging between tiers
- Package resources must be accessible both in development (editable install) and production (installed package)

### Architecture Compliance

**From architecture.md:**

1. **Module Location:** Command resolution lives in `src/adw/commands/`
   - `resolver.py` - Three-tier resolution logic
   - `loader.py` - Load command from resolved directory (Story 2.3)

2. **Pydantic Models in `models/`:**
   - `ResolvedCommand` model MUST be in `src/adw/models/command.py`
   - Never define models inside `commands/` modules

3. **Exception Hierarchy:**
   - Use `ConfigError` from `src/adw/exceptions.py`
   - Include `code`, `message`, `suggestion`, `recoverable` fields
   - Never raise bare `Exception`

4. **Three-Tier Hierarchy (FR19-FR21):**
   ```
   1. .adw/commands/{name}/        (project level - highest priority)
   2. ~/.adw/commands/{name}/      (user level)
   3. defaults/commands/{name}/    (bundled - lowest priority)
   ```

5. **Config Key Snake Case:**
   - All paths and config keys use `snake_case`
   - Directory names can use `kebab-case` for CLI aesthetics

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | ResolvedCommand model with validation |
| pathlib | stdlib | Path manipulation (use `Path`, not strings) |
| importlib.resources | stdlib | Access bundled defaults in package |

**importlib.resources Pattern (Python 3.13+):**
```python
from importlib.resources import files

# Access bundled defaults
defaults_path = files("adw") / "defaults" / "commands" / name
if defaults_path.is_dir():
    return Path(defaults_path)
```

### File Structure Requirements

**Files to Create:**
```
src/adw/
├── commands/
│   ├── __init__.py      # Export CommandResolver
│   └── resolver.py      # CommandResolver class
├── models/
│   └── command.py       # ResolvedCommand model (may exist, add to it)
└── ...

defaults/
└── commands/
    ├── plan/
    │   └── prompt.md    # Placeholder prompt
    ├── build/
    │   └── prompt.md
    ├── verify/
    │   └── prompt.md
    ├── validate/
    │   └── prompt.md
    └── document/
        └── prompt.md

tests/
└── unit/
    └── commands/
        └── test_resolver.py
```

**Files to Modify:**
- `src/adw/models/__init__.py` - Export ResolvedCommand
- `src/adw/commands/__init__.py` - Export CommandResolver

### Testing Requirements

**Test File:** `tests/unit/commands/test_resolver.py`

**Test Cases (>80% coverage):**

1. **Resolution Priority:**
   ```python
   def test_project_tier_takes_precedence():
       # Setup project-level command
       # Assert project tier returned, not user or bundled

   def test_user_tier_fallback():
       # No project-level, user-level exists
       # Assert user tier returned

   def test_bundled_tier_fallback():
       # No project or user level
       # Assert bundled tier returned
   ```

2. **Error Cases:**
   ```python
   def test_command_not_found_raises_config_error():
       # Non-existent command
       # Assert ConfigError with code="COMMAND_NOT_FOUND"

   def test_missing_prompt_md_raises_config_error():
       # Directory exists but no prompt.md
       # Assert ConfigError with code="INVALID_COMMAND"
   ```

3. **Optional File Detection:**
   ```python
   def test_detects_schema_json():
       # Command with schema.json
       # Assert resolved.has_schema == True

   def test_detects_hooks():
       # Command with pre.sh and post.sh
       # Assert resolved.has_pre_hook and has_post_hook
   ```

**Fixtures Needed:**
- Temporary directory with mock command structures
- Use `tmp_path` pytest fixture
- Mock `importlib.resources` for bundled defaults in tests

---

## Previous Story Intelligence

_This is the first story in Epic 2. No previous story intelligence available._

**Relevant Context from Epic 1:**
- Exception hierarchy is implemented in `src/adw/exceptions.py`
- Use `ConfigError` for configuration-related errors
- Pydantic models pattern established in `src/adw/models/`

---

## Git Intelligence

**Recent Commits (Epic 1):**
- Project structure established with `src/adw/` layout
- Pydantic models in `models/` directory
- Exception hierarchy with `ADWError` base class
- pytest fixtures in `tests/conftest.py`

**Conventions Observed:**
- Type hints on all functions
- Docstrings for public methods
- Test files mirror source structure

---

## Latest Technical Information

**importlib.resources (Python 3.13):**
- Use `files()` function to access package resources
- Supports traversable interface for directory access
- Works with both installed packages and editable installs

**Pydantic 2.12+ Model Validation:**
```python
from pydantic import BaseModel, model_validator

class ResolvedCommand(BaseModel):
    name: str
    path: Path
    tier: Literal["project", "user", "bundled"]
    has_schema: bool = False
    has_pre_hook: bool = False
    has_post_hook: bool = False

    @model_validator(mode="after")
    def validate_prompt_exists(self) -> "ResolvedCommand":
        if not (self.path / "prompt.md").exists():
            raise ValueError(f"Command {self.name} missing prompt.md")
        return self
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All Pydantic models in `src/adw/models/`
- Use exception hierarchy, never bare Exception
- Full type annotations required
- Structured logging with context fields
- Tests mirror source structure in `tests/unit/`

---

## Dev Notes

### Key Implementation Decisions:

1. **Resolution Order is Fixed:** Project → User → Bundled. No configuration to change order.

2. **First Match Wins:** No merging of files between tiers. If project has `prompt.md`, that's used even if user tier has different `schema.json`.

3. **Path Expansion:** Use `Path.home()` for user directory, not environment variable directly.

4. **Bundled Access:** Use `importlib.resources` for Python 3.13+ compatible package resource access.

### Project Structure Notes

- `src/adw/commands/resolver.py` - Main resolution logic
- `src/adw/models/command.py` - ResolvedCommand model
- `defaults/commands/` - Bundled default commands (package data)

### References

- [Source: _bmad-output/architecture.md#Command Boundary]
- [Source: _bmad-output/architecture.md#Config Hierarchy]
- [Source: _bmad-output/prd.md#FR19-FR25 (Command System)]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dependencies

**Depends On:** None (Wave 1 - can start immediately)

**Blocks:**
- Story 2.3: Load and Render Phase Prompts (needs resolved command directory)
- Story 2.4: Validate LLM Output Against Schema (needs to locate schema.json)

---

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

