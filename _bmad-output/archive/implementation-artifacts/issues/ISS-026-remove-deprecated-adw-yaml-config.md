# Issue: Remove deprecated .adw/adw.yaml and add git-based base branch config

**ID:** ISS-026
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-18
**Reporter:** Ivo

## Related

- **Epic:** N/A
- **Story:** N/A
- **Component:** CLI / Configuration

## Description

The codebase still references the deprecated `.adw/adw.yaml` configuration file path which no longer exists. The project configuration now lives in `.adw/project.yaml`. This technical debt needs cleanup and the base branch configuration needs to be properly implemented.

### Two Requirements

1. **Remove all `.adw/adw.yaml` references** - The deprecated config path should be removed from the entire codebase
2. **Add `base_branch` to GitConfig** - Make base branch configurable via `git.base_branch` in `project.yaml`

## Affected Code

### Files referencing `.adw/adw.yaml` (to be removed/updated):

1. **`src/adw/cli/pr.py:520-535`** - `_get_base_branch()` function looks for `.adw/adw.yaml`
   ```python
   config_path = project_root / ".adw" / "adw.yaml"
   if config_path.exists():
       # ... reads git.default_branch from deprecated location
   ```

2. **`tests/unit/cli/test_pr.py:311-330`** - Test `test_reads_from_config()` creates `.adw/adw.yaml`

### Model to update:

3. **`src/adw/models/config.py:500-558`** - `GitConfig` class needs new `base_branch` field

## Reproduction Steps

1. Run `adw pr` command in a project without `.adw/adw.yaml`
2. The code attempts to read from non-existent config path
3. Base branch configuration cannot be customized via `project.yaml`

## Expected Behavior

1. All config read from `.adw/project.yaml` (not `.adw/adw.yaml`)
2. Base branch configurable via `git.base_branch` in `project.yaml`
3. Fallback to auto-detection if not configured

## Actual Behavior

1. Code looks for `.adw/adw.yaml` which doesn't exist
2. No `base_branch` option in GitConfig model
3. Users cannot configure base branch

## Impact

- Configuration confusion for users
- Technical debt from deprecated config path
- Inability to configure base branch per-project

## User Impact Score

- **Users Affected:** All users trying to customize git integration
- **Frequency:** Every PR creation

## Workaround

None - users cannot configure base branch without the deprecated file.

## Environment

- **OS:** macOS/Linux/Windows
- **App Version:** Current development
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-026-remove-deprecated-adw-yaml-config.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Implementation Requirements

### Task 1: Add `base_branch` to GitConfig

**File:** `src/adw/models/config.py`

Add new field to `GitConfig` class:

```python
base_branch: str | None = Field(
    default=None,
    description="Base branch for PRs (e.g., 'main', 'develop'). "
    "If not set, auto-detects from repository.",
)
```

Update docstring attributes and YAML example to include `base_branch`.

### Task 2: Update `_get_base_branch()` in pr.py

**File:** `src/adw/cli/pr.py`

Replace the current implementation that reads from `.adw/adw.yaml` with:

```python
def _get_base_branch(run_dir: Path) -> str:
    """Get the base branch for PR creation.

    Resolution order:
    1. git.base_branch from .adw/project.yaml
    2. Auto-detect (defaults to 'main')

    Args:
        run_dir: Path to the run directory.

    Returns:
        Base branch name.
    """
    from adw.config.loader import ConfigLoader

    project_root = run_dir.parent.parent.parent  # .adw/runs/<id> -> project root

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

### Task 3: Update Tests

**File:** `tests/unit/cli/test_pr.py`

Update `TestGetBaseBranch.test_reads_from_config()` to:
- Create `.adw/project.yaml` instead of `.adw/adw.yaml`
- Use `git.base_branch` instead of `git.default_branch`

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

### Task 4: Verify No Other References

Run grep to ensure no other `.adw/adw.yaml` references remain:
```bash
grep -r "adw\.yaml" src/ tests/ --include="*.py" | grep -v "project\.yaml"
```

## Acceptance Criteria

- [ ] `GitConfig` has `base_branch: str | None` field with default `None`
- [ ] `_get_base_branch()` reads from `.adw/project.yaml` via ConfigLoader
- [ ] No references to `.adw/adw.yaml` remain in `src/` or `tests/`
- [ ] Tests updated to use `project.yaml` and `git.base_branch`
- [ ] All existing tests pass
