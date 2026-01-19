# Story: UX Fix - Auto-load .adw/.env for Linear Credentials

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-19

---

## Story

As a developer working with multiple ADW projects using different Linear workspaces,
I want ADW to auto-load credentials from a project-specific `.adw/.env` file,
so that I can easily manage per-project Linear credentials without global shell configuration.

## Acceptance Criteria

- [ ] **AC1**: Add `python-dotenv` dependency to `pyproject.toml`
- [ ] **AC2**: Create env loading in CLI bootstrap that loads `.adw/.env` if it exists
  - Loading happens in `@app.callback()` BEFORE any command runs
  - Only loads from `.adw/.env` path (not project root `.env`)
  - Silent if file doesn't exist (no error)
- [ ] **AC3**: Create `.adw/.env.template` during `adw init` (both wizard and minimal mode)
  - Contains placeholder for `LINEAR_API_KEY` and `LINEAR_TEAM_ID`
  - Includes helpful comments explaining how to use
- [ ] **AC4**: Update `.adw/.gitignore` to include `.env` pattern
  - Update in `initializer.py` (minimal mode)
  - Update in `summary.py` (wizard mode)
- [ ] **AC5**: Update error messages in `linear.py` to reference `.adw/.env`
  - `_get_api_key()` suggestion: "Add LINEAR_API_KEY to .adw/.env file"
  - `_get_team_id()` suggestion: "Add LINEAR_TEAM_ID to .adw/.env file"
- [ ] **AC6**: All existing tests pass after changes
- [ ] **AC7**: Add tests for new .env loading functionality

## Tasks / Subtasks

### Task 1: Add python-dotenv Dependency
**Files**: `pyproject.toml`

- [x] 1.1 Add `python-dotenv>=1.0.0` to dependencies list (line 11-22)

### Task 2: Implement .env Loading in CLI Bootstrap
**Files**: `src/adw/cli/app.py`

- [x] 2.1 Add import for `dotenv` at top of file
- [x] 2.2 Create `_load_env_file()` helper function that:
  - Constructs path: `Path.cwd() / ".adw" / ".env"`
  - Checks if file exists
  - Calls `dotenv.load_dotenv(path)` if exists
  - Silently returns if file doesn't exist
- [x] 2.3 Call `_load_env_file()` at the START of `@app.callback()` function (line 96)
  - Must be called BEFORE verbosity handling (line 112)
  - Environment must be loaded before any command runs

### Task 3: Update Error Messages in Linear Task Manager
**Files**: `src/adw/task_managers/linear.py`

- [x] 3.1 Update `_get_api_key()` suggestion message (line 78)
  - Change from: `"Add LINEAR_API_KEY to your .env file"`
  - Change to: `"Add LINEAR_API_KEY to .adw/.env file, then retry"`
- [x] 3.2 Update `_get_team_id()` suggestion message (line 97)
  - Change from: `"Add LINEAR_TEAM_ID to your .env file"`
  - Change to: `"Add LINEAR_TEAM_ID to .adw/.env file, then retry"`

### Task 4: Update Gitignore in Minimal Init Mode
**Files**: `src/adw/config/initializer.py`

- [x] 4.1 Update `GITIGNORE_CONTENT` constant to include `.env`:
  ```python
  GITIGNORE_CONTENT = """\
  # ADW run data (can be large)
  runs/

  # ADW logs
  *.log

  # Environment files with secrets
  .env
  """
  ```

### Task 5: Create .env.template in Minimal Init Mode
**Files**: `src/adw/config/initializer.py`

- [ ] 5.1 Add `ENV_TEMPLATE_CONTENT` constant:
  ```python
  ENV_TEMPLATE_CONTENT = """\
  # ADW Credentials
  # Copy this file to .env and fill in your values
  # The .env file is gitignored and will NOT be committed

  # Linear Task Manager (required if using linear task manager)
  # Get your API key from: Linear Settings > API > Personal API keys
  LINEAR_API_KEY=

  # Linear Team ID (UUID format)
  # Find via: Linear Settings > Workspace > Copy team ID
  LINEAR_TEAM_ID=
  """
  ```
- [ ] 5.2 Add `_write_env_template()` method to create `.env.template` file
- [ ] 5.3 Call `_write_env_template()` in `initialize()` method after `_write_gitignore()`

### Task 6: Update Wizard Summary Gitignore
**Files**: `src/adw/cli/wizard/summary.py`

- [ ] 6.1 Update `generate_gitignore()` function (line 522-533) to include `.env`:
  ```python
  return """# ADW runtime artifacts
  runs/
  logs/
  *.log
  state.json

  # Environment files with secrets
  .env
  """
  ```

### Task 7: Add .env.template to Wizard File Generation
**Files**: `src/adw/cli/wizard/summary.py`

- [ ] 7.1 Add `generate_env_template()` function:
  ```python
  def generate_env_template() -> str:
      """Generate .env.template content for credential setup."""
      return """\
  # ADW Credentials
  # Copy this file to .env and fill in your values
  # The .env file is gitignored and will NOT be committed

  # Linear Task Manager (required if using linear task manager)
  # Get your API key from: Linear Settings > API > Personal API keys
  LINEAR_API_KEY=

  # Linear Team ID (UUID format)
  # Find via: Linear Settings > Workspace > Copy team ID
  LINEAR_TEAM_ID=
  """
  ```
- [ ] 7.2 Update `_generate_all_files()` (line 322) to include `.env.template`:
  ```python
  files[".env.template"] = generate_env_template()
  ```
- [ ] 7.3 Update `_get_files_to_create()` (line 264) to include `.env.template`:
  ```python
  files = ["project.yaml", ".gitignore", ".env.template"]
  ```

### Task 8: Add Unit Tests
**Files**: `tests/unit/cli/test_env_loading.py` (new file)

- [ ] 8.1 Test `_load_env_file()` loads from correct path
- [ ] 8.2 Test `_load_env_file()` silently does nothing if file doesn't exist
- [ ] 8.3 Test environment variables are available after loading
- [ ] 8.4 Test that callback loads env before commands run

**Files**: `tests/unit/config/test_initializer.py` (update)

- [ ] 8.5 Add test for `.env.template` creation in minimal mode
- [ ] 8.6 Add test for `.env` in `.gitignore` content

**Files**: `tests/unit/cli/wizard/test_summary.py` (update)

- [ ] 8.7 Add test for `.env.template` in generated files
- [ ] 8.8 Add test for `.env` in gitignore content

---

## Developer Context

### Technical Requirements

- Use `python-dotenv` library for .env file loading (industry standard)
- Load env file very early in CLI bootstrap, before any imports that might need env vars
- `.env.template` is committed (has placeholders), `.env` is gitignored (has secrets)
- Maintain backward compatibility - existing projects without `.adw/.env` should work fine

### Architecture Compliance

**CLI Bootstrap Pattern**:
- `app.py` `@app.callback()` at line 96 runs on EVERY command invocation
- This is the correct place to load env vars - before any command logic
- Currently callback only handles verbosity flags (lines 121-128)
- Env loading must happen BEFORE line 112 (start of verbosity handling)

**Init Pattern**:
- Minimal mode: `initializer.py` creates files via `initialize()` method
- Wizard mode: `summary.py` generates files via `_generate_all_files()`
- Both must create `.env.template` for consistency

**Task Manager Pattern**:
- `TaskManagerFactory.create()` is called in `run()` command (line 252-255)
- Factory creates `LinearTaskManager` which reads env vars in `__init__()` (line 50-51)
- By this point, env must already be loaded via callback

### Library & Framework Requirements

- **python-dotenv**: Use `load_dotenv(dotenv_path=path)` for explicit path loading
  ```python
  from dotenv import load_dotenv
  from pathlib import Path

  def _load_env_file() -> None:
      env_path = Path.cwd() / ".adw" / ".env"
      if env_path.exists():
          load_dotenv(dotenv_path=env_path)
  ```

- **Typer/Rich**: No changes needed - existing patterns work

### File Structure Requirements

Files to modify:
```
pyproject.toml                          # Add dependency
src/adw/cli/app.py                      # Add env loading in callback
src/adw/task_managers/linear.py         # Update error messages
src/adw/config/initializer.py           # Add .env.template, update gitignore
src/adw/cli/wizard/summary.py           # Add .env.template, update gitignore
```

New files:
```
tests/unit/cli/test_env_loading.py      # Tests for env loading
```

Files to update (tests):
```
tests/unit/config/test_initializer.py   # Test .env.template creation
tests/unit/cli/wizard/test_summary.py   # Test .env.template in wizard
```

### Testing Requirements

- Use `monkeypatch.setenv()` / `monkeypatch.delenv()` for env var manipulation
- Use `tmp_path` fixture for creating test directories with .env files
- Test both "file exists" and "file doesn't exist" scenarios
- Verify env vars are actually set after `load_dotenv()` call
- Follow existing test patterns in `tests/unit/task_managers/test_linear.py`

---

## Previous Story Intelligence

**From ISS-027 implementation (wizard UX fixes)**:
- Wizard summary generates files via `_generate_all_files()` returning dict of path -> content
- `_get_files_to_create()` returns list shown in summary panel
- `atomic_write_config()` writes all files atomically with rollback support
- Testing pattern uses `unittest.mock.patch` for Rich prompts

**From Story 12-2 (Linear task manager)**:
- `LinearTaskManager.__init__()` calls `_get_api_key()` and `_get_team_id()`
- Both methods use `os.environ.get()` directly (no .env loading)
- Error messages suggest .env file but SDK doesn't load it
- Tests use `monkeypatch.setenv("LINEAR_API_KEY", "test_key")` pattern

**From Story 6-6 (initialize new project)**:
- `Initializer` class handles minimal init mode
- Creates `.adw/` directory, `project.yaml`, `.gitignore`
- `GITIGNORE_CONTENT` constant defines gitignore content
- Called from `init.py` when user chooses minimal mode

---

## Git Intelligence

**Recent relevant commits**:
- `a780e68` - ISS-027 wizard UX fixes - shows wizard modification pattern
- `92b0b3e` - Story 15.1 ship phase SDK integration - recent Epic 15 work
- `2eeb72d` - Story 14-10 summary file generation - shows wizard file generation

**Code patterns observed**:
- CLI commands use `@app.callback()` for global setup (app.py:96)
- Error messages use `ConfigError` with `suggestion` field
- Wizard generates files through `_generate_all_files()` returning dict
- Tests use pytest fixtures and monkeypatch for env manipulation

---

## Latest Technical Information

**python-dotenv (v1.0.1, Dec 2024)**:
- Stable, widely-used library for .env file loading
- `load_dotenv(dotenv_path=...)` for explicit file path
- `load_dotenv(override=False)` - won't overwrite existing env vars (default behavior)
- Returns `True` if file was found and loaded, `False` otherwise
- No breaking changes between 1.0.x versions

**Usage pattern**:
```python
from dotenv import load_dotenv
from pathlib import Path

# Load from specific path, don't override existing env vars
env_path = Path.cwd() / ".adw" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
```

---

## Project Context Reference

See: docs/arch-entry-point.md, docs/arch-high-level.md

Key patterns and rules:
- CLI is the main entry point via Typer app
- `@app.callback()` runs before all commands - ideal for env loading
- Task manager configured in `project.yaml` under `task_manager:` key
- Credentials come from environment (LINEAR_API_KEY, LINEAR_TEAM_ID)

---

## Dev Notes

### Key Implementation Details

1. **Load Order**: The env file MUST be loaded before any code that might access env vars:
   ```
   CLI invoked -> @app.callback() -> _load_env_file() -> verbosity handling -> command runs
   ```

2. **Path Construction**: Always use `Path.cwd() / ".adw" / ".env"` not hardcoded strings
   - This respects worktree scenarios where cwd may differ

3. **Silent Failure**: If `.adw/.env` doesn't exist, don't log or warn - just return
   - Many projects won't use Linear integration

4. **Template vs Actual**:
   - `.env.template` - committed, has placeholders, shows what vars are needed
   - `.env` - gitignored, has actual secrets, user creates by copying template

5. **Backward Compatibility**: Projects that already set env vars via shell will continue to work
   - `load_dotenv(override=False)` is default - won't overwrite existing vars

### Source References

- [Source: src/adw/cli/app.py:96-139] - CLI callback where env loading goes
- [Source: src/adw/task_managers/linear.py:64-100] - Error messages to update
- [Source: src/adw/config/initializer.py:67-73] - GITIGNORE_CONTENT constant
- [Source: src/adw/config/initializer.py:158-161] - _write_gitignore method
- [Source: src/adw/cli/wizard/summary.py:322-343] - _generate_all_files function
- [Source: src/adw/cli/wizard/summary.py:522-533] - generate_gitignore function
- [Source: tests/unit/task_managers/test_linear.py:19-58] - Test patterns for env vars

---

## Dev Agent Record

### Context Reference

Issue: `_bmad-output/implementation-artifacts/issues/ISS-028-sdk-no-env-file-for-linear-credentials.md`

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

(To be filled by dev agent after implementation)

### File List

(To be filled by dev agent after implementation)
