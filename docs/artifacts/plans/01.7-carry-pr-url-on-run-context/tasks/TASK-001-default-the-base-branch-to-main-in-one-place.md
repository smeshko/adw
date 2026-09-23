# TASK-001: Default the base branch to main in one place

Depends on: None
Suggested commit: `fix(config): default the base branch to main in one place`

## Goal

`GitConfig.base_branch` is the only source of the default base branch (`"main"`). Every consumer reads it, and nothing in `src/adw` falls back to `"staging"`.

## Files

- `src/adw/models/config.py`:
  - `GitConfig.base_branch` becomes `str = Field(default="main", …)`.
  - A `field_validator("base_branch", mode="before")` maps `None` and `""` to `"main"`.
  - Update the class docstring (451) and the field description to say the default is `main`.
- `src/adw/core/run_lifecycle.py`:
  - `_fetch_base_branch` (547–580) uses `self.git_config.base_branch` directly.
  - Its docstring loses the `"staging"` / `"origin/staging"` examples.
- `src/adw/core/extensions/ship.py`:
  - `ShipExtension.__init__` gains `git_config: GitConfig`.
  - `on_complete` (156) uses `merge_record.get("base_branch") or self._git_config.base_branch`.
- `src/adw/core/extensions/__init__.py:66`: `ShipExtension(git_config=git_config, project_root=project_root)`.
- `src/adw/defaults/commands/ship/post.sh:249`: change the fallback from `|| echo "staging"` to `|| echo ""`.
- `src/adw/cli/pr.py`:
  - `_get_base_branch` returns `config.git.base_branch`, and on a load failure returns `GitConfig().base_branch`.
  - `create_pr_via_gh`'s `base` loses its default and becomes keyword-only required.
  - Drop the `staging` wording from the module and function docstrings (7, 181, 186, 365, 425, 587, 593, 718, 777).
- `src/adw/config/yaml_generator.py:270`: the comment reads `# base_branch: main  # PR base branch (default: main)`.
- `docs/architecture/deep-dive/document-phase.md:230–233`: the example says `main`.
- Tests:
  - `tests/unit/models/test_config.py`
  - `tests/unit/core/test_run_lifecycle.py` (`TestFetchBaseBranch`, `TestCreateWorktreeForRunFetch`)
  - `tests/unit/cli/test_pr.py` (`TestCreatePrViaGh::test_create_pr_success`, `TestGetBaseBranch`)
  - `tests/dashboard/test_settings_indicators.py`
  - `tests/unit/config/test_yaml_generator.py`
  - `tests/unit/ship/` or wherever `ShipExtension` is constructed. Grep `ShipExtension(`.

## Acceptance

- [ ] `GitConfig()` and `GitConfig(base_branch=None)` both give `base_branch == "main"`, and a `project.yaml` with `git: {base_branch: null}` loads with `"main"`.
- [ ] With no `base_branch` configured, `RunLifecycle._fetch_base_branch` runs `git fetch origin main` and returns `"origin/main"`.
- [ ] `ShipExtension.on_complete` with a merge record whose `base_branch` is `""` checks out and pulls `git_config.base_branch`.
- [ ] `grep -rn "staging" src/adw` hits only `src/adw/hooks/git_commit.py`.
- [ ] `uv run pytest tests/unit/models tests/unit/core/test_run_lifecycle.py tests/unit/cli/test_pr.py tests/unit/config tests/dashboard/test_settings_indicators.py tests/unit/ship -o addopts=""` passes.

Evidence:
- the RED run, where the new default and empty-merge-record tests fail on today's code
- the GREEN run
- the `grep -rn "staging" src/adw` output

## Steps

### RED
- [ ] `tests/unit/models/test_config.py`: parametrize `test_git_config_base_branch_defaults_to_main` over `{}`, `{"base_branch": None}` and `{"base_branch": ""}`, and assert `"main"`. Explicit `"develop"` stays `"develop"`.
- [ ] `TestFetchBaseBranch`:
  - Rename `test_fetch_falls_back_to_staging_when_base_branch_none` to `…_to_main_…`, and assert `origin/main` and the `fetch` argv.
  - Change the `origin/staging` / `"staging"` expectations in `test_fetch_succeeds_returns_remote_ref`, `test_fetch_failure_raises_worktree_error` and `TestCreateWorktreeForRunFetch::test_passes_source_branch_to_create_worktree` to `main`.
- [ ] Add a `ShipExtension.on_complete` test:
  - `merge_record.json` has `"base_branch": ""`, and `git_config=GitConfig(base_branch="develop")`.
  - Patch `subprocess.run`, and assert `git checkout develop` and `git pull origin develop`.
- [ ] `tests/unit/cli/test_pr.py::TestGetBaseBranch`: `test_returns_staging_by_default` → `test_returns_main_by_default`.
- [ ] Run and confirm the new and renamed tests fail.

### GREEN
- [ ] Make the `GitConfig` field and validator change.
- [ ] Update `_fetch_base_branch`, `ShipExtension` and its registration, `post.sh`, `_get_base_branch` and `create_pr_via_gh`.
- [ ] `tests/dashboard/test_settings_indicators.py::TestTabBadgesInHTML::test_git_badge_count_matches_changed`: use `base_branch="develop"` as the changed value.
- [ ] Update any `ShipExtension(project_root=…)` construction in tests to pass `git_config=GitConfig()`.
- [ ] Run the partial suite until it's green.

### REFACTOR
- [ ] Update the generator comment and `document-phase.md`, then drop the stale `staging` docstring text in `cli/pr.py` and `run_lifecycle.py`.
- [ ] `grep -rn "staging" src/adw`, then `scripts/preflight.sh`.

## Notes

- This repo's own `.adw/project.yaml` sets `base_branch: staging`, so ADW's own runs keep targeting staging. Don't touch that file; it's gitignored runtime state.
- `cli/pr.py` is gutted in TASK-004 and TASK-005. Here it only loses its `staging` fallbacks, so the commit is self-contained.
