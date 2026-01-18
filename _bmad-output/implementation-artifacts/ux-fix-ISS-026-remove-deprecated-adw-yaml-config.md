# Story ISS-026: Remove Deprecated adw.yaml Config and Add base_branch

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure / Tech Debt
Created: 2026-01-18

---

## Story

As a **developer using ADW SDK**,
I want **the deprecated `.adw/adw.yaml` configuration references removed and a `base_branch` field added to GitConfig**,
so that **I can configure the base branch for PRs via the current `.adw/project.yaml` config without confusion from deprecated paths**.

## Acceptance Criteria

- [ ] `GitConfig` model in `src/adw/models/config.py` has new `base_branch: str | None` field with default `None`
- [ ] `_get_base_branch()` function in `src/adw/cli/pr.py` reads from `.adw/project.yaml` via ConfigLoader instead of `.adw/adw.yaml`
- [ ] No references to `.adw/adw.yaml` remain in `src/` or `tests/` directories
- [ ] Tests in `tests/unit/cli/test_pr.py` updated to use `project.yaml` and `git.base_branch`
- [ ] All existing tests pass after changes
- [ ] The implementation follows the resolution order: `git.base_branch` from config → fallback to "main"

## Tasks / Subtasks

### Task 1: Add `base_branch` to GitConfig Model
- [ ] Add `base_branch: str | None = Field(default=None, ...)` to `GitConfig` in `src/adw/models/config.py:500-558`
- [ ] Update docstring to include `base_branch` attribute
- [ ] Update YAML example in docstring to show `base_branch` configuration

### Task 2: Update `_get_base_branch()` Function
- [ ] Modify `src/adw/cli/pr.py:506-537` to use ConfigLoader
- [ ] Remove all references to `.adw/adw.yaml`
- [ ] Add import for ConfigLoader
- [ ] Follow resolution order: config `git.base_branch` → fallback "main"

### Task 3: Update Unit Tests
- [ ] Update `test_reads_from_config()` in `tests/unit/cli/test_pr.py:311-330`
- [ ] Change test to create `.adw/project.yaml` instead of `.adw/adw.yaml`
- [ ] Change test to use `git.base_branch` instead of `git.default_branch`

### Task 4: Verify No Other References
- [ ] Run grep to ensure no `.adw/adw.yaml` references remain
- [ ] Run full test suite to ensure no regressions

---

## Relevant Feature Documentation

### Matched: Configuration Patterns
From project-context.md - Configuration models and patterns apply to this story.

---

## Developer Context

### Technical Requirements

1. **Model Update Location:** `src/adw/models/config.py` - GitConfig class at lines 500-558
2. **Function Update Location:** `src/adw/cli/pr.py` - `_get_base_branch()` at lines 506-537
3. **Test Update Location:** `tests/unit/cli/test_pr.py` - TestGetBaseBranch class at lines 300-330
4. **Use ConfigLoader:** Import from `adw.config.loader` - already exists and implements three-tier resolution

### Architecture Compliance

**Config Resolution Pattern (from ConfigLoader):**
```python
# Three-tier resolution - project → user → bundled defaults
# Project config location: .adw/project.yaml (NOT adw.yaml!)
```

**Exception Handling Pattern:**
```python
from adw.exceptions import ConfigError
# Catch exceptions gracefully and fall back to defaults
```

**Type Annotation Requirements:**
```python
# REQUIRED: Full type annotations, modern Python 3.13+ syntax
def _get_base_branch(run_dir: Path) -> str:
    ...
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | Field definitions in models |
| PyYAML | 6.0+ | YAML parsing (via ConfigLoader) |

**Pydantic Field Pattern (from existing GitConfig):**
```python
base_branch: str | None = Field(
    default=None,
    description="Base branch for PRs (e.g., 'main', 'develop'). "
    "If not set, falls back to 'main'.",
)
```

### File Structure Requirements

**Files to Modify:**
1. `src/adw/models/config.py` - Add field to GitConfig
2. `src/adw/cli/pr.py` - Update `_get_base_branch()` function
3. `tests/unit/cli/test_pr.py` - Update test method

**No New Files Required**

### Testing Requirements

**Test File:** `tests/unit/cli/test_pr.py`

**Required Test Updates:**

1. **Update `test_reads_from_config`** (lines 311-330):
   - Create `.adw/project.yaml` instead of `.adw/adw.yaml`
   - Use `git.base_branch: develop` instead of `git.default_branch`
   - Create valid minimal project config with required fields (name, language)

**Test Pattern (based on existing tests in file):**
```python
def test_reads_from_config(self, tmp_path: Path) -> None:
    """Test reads base_branch from project.yaml config."""
    project_root = tmp_path
    runs_dir = project_root / ".adw" / "runs"
    run_dir = runs_dir / "test"
    run_dir.mkdir(parents=True)

    # Create project.yaml config (not adw.yaml)
    config_dir = project_root / ".adw"
    config_file = config_dir / "project.yaml"
    config_file.write_text("""
name: test-project
language: python
git:
  base_branch: develop
""")

    result = _get_base_branch(run_dir)
    assert result == "develop"
```

**Coverage Expectation:** >80% (per project standards)

---

## Previous Story Intelligence

N/A - This is an issue-based story, not part of sequential epic stories.

---

## Git Intelligence

**Recent Commits Pattern:**
- `refactor(dev-begin): always use worktree, fix parallel run blocking`
- `feat(epic-14): Create Interactive Init Wizard epic and stories`
- Commit message pattern: `type(scope): description`

**Relevant Convention:** Use `fix(cli): ` or `refactor(config): ` prefix for this change.

---

## Latest Technical Information

**ConfigLoader Usage (from existing codebase):**
```python
from adw.config.loader import ConfigLoader

loader = ConfigLoader(project_root)
if loader.has_project_config:
    config = loader.load()
    # Access config.git.base_branch
```

**Current `_get_base_branch` Implementation (to be replaced):**
```python
# Current (DEPRECATED - using adw.yaml):
config_path = project_root / ".adw" / "adw.yaml"
if config_path.exists():
    # ... reads git.default_branch
```

**New Implementation Pattern:**
```python
def _get_base_branch(run_dir: Path) -> str:
    """Get the base branch for PR creation.

    Resolution order:
    1. git.base_branch from .adw/project.yaml
    2. Fallback to 'main'

    Args:
        run_dir: Path to the run directory.

    Returns:
        Base branch name.
    """
    from adw.config.loader import ConfigLoader

    # .adw/runs/<id> -> project root
    project_root = run_dir.parent.parent.parent

    try:
        loader = ConfigLoader(project_root)
        if loader.has_project_config:
            config = loader.load()
            if config.git.base_branch:
                return config.git.base_branch
    except Exception:
        pass

    return "main"
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Naming Conventions:** snake_case for variables/functions, PascalCase for classes
2. **Models Location:** All Pydantic models in `src/adw/models/`
3. **Type Annotations:** Required for all functions, use `X | None` syntax
4. **Exception Pattern:** Use ADWError hierarchy, never bare exceptions
5. **Testing:** Tests mirror source structure, use MockExecutor for LLM tests
6. **Config Keys:** snake_case in YAML files

---

## Dev Notes

### Key Implementation Points

1. **GitConfig is frozen=False** (see config.py:696) - model can be mutated after creation
2. **ConfigLoader already handles project.yaml** - use existing infrastructure
3. **Keep fallback simple** - just return "main" if no config or config.git.base_branch is None
4. **Don't break existing behavior** - users without config should still get "main" as default

### Verification Commands

```bash
# Verify no adw.yaml references remain
grep -r "adw\.yaml" src/ tests/ --include="*.py" | grep -v "project\.yaml"

# Run specific tests
pytest tests/unit/cli/test_pr.py::TestGetBaseBranch -v

# Run full test suite
pytest tests/unit/ -v
```

### Project Structure Notes

- Config model at: `src/adw/models/config.py`
- ConfigLoader at: `src/adw/config/loader.py`
- CLI module at: `src/adw/cli/pr.py`
- Test file at: `tests/unit/cli/test_pr.py`

### References

- [Source: src/adw/models/config.py#GitConfig] - lines 500-558
- [Source: src/adw/cli/pr.py#_get_base_branch] - lines 506-537
- [Source: src/adw/config/loader.py] - ConfigLoader class
- [Source: tests/unit/cli/test_pr.py#TestGetBaseBranch] - lines 300-331
- [Issue: _bmad-output/implementation-artifacts/issues/ISS-026-remove-deprecated-adw-yaml-config.md]

---

## Dev Agent Record

### Context Reference

- Issue file: `_bmad-output/implementation-artifacts/issues/ISS-026-remove-deprecated-adw-yaml-config.md`

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Story file created with exhaustive context analysis
- All affected files identified and documented
- Implementation pattern provided with code examples
- Test update requirements specified with sample code
- Verification commands included

### File List

Files to modify:
1. `src/adw/models/config.py` - Add base_branch field to GitConfig
2. `src/adw/cli/pr.py` - Update _get_base_branch() function
3. `tests/unit/cli/test_pr.py` - Update test_reads_from_config test
