# Validation: Make dashboard settings read-only

Validated on `feature/adw-21` at `a1cd34d5`, merge-base `910b890e` (`origin/staging`), 2026-09-24.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The settings page renders every section for this repo's `.adw` config | Met | [Smoke test](#smoke-test): all 9 tabs return 200 as a full page, an HTMX partial and a content partial. [Screenshots](#screenshots): the Basics, Task Manager and Phases tabs render values, and the invalid phase files show their errors. `test_every_tab_renders_its_values_without_touching_config` passes |
| The only POST routes left are run start and abort; no route accepts PUT/PATCH/DELETE | Met | [Route list](#route-list), and `test_only_run_start_and_abort_accept_writes` |
| Visiting every settings view leaves `.adw/project.yaml` and `.adw/commands/*/config.yaml` byte-identical | Met | [Smoke test](#smoke-test): `shasum` before and after, `diff` empty (`byte-identical`). The byte-identity test covers the file set too |
| `tests/dashboard/` no longer exists | Met | `ls tests/dashboard` → `No such file or directory`, and `grep -rn "tests/dashboard" pyproject.toml tests` exits 1 |
| Nothing new is dead (`vulture`, diffed against the merge-base) | Met with a recorded exception | [Vulture diff](#vulture-diff). Of the 3 new entries, 2 are `ConfigRegistry` query methods whose only `src` caller was the deleted settings code; they are left to phase 2.8, see [Divergence](#divergence-from-the-plan). The third, `source_pattern`, is a false positive |
| `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80% | Met | [Preflight and tests](#preflight-and-tests): `preflight: ok`; 3,581 passed, 5 skipped, 85.34% |

## Preflight and tests

```text
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
362 files already formatted
==> mypy
Success: no issues found in 154 source files
preflight: ok

$ uv run pytest
TOTAL                                    11615   1482   3292    329    85%
Required test coverage of 80% reached. Total coverage: 85.34%
================= 3581 passed, 5 skipped in 173.31s (0:02:53) ==================

$ uv run python -c "import adw.dashboard.server, adw.dashboard.settings, adw.dashboard.routes, adw.dashboard.partials, adw.dashboard.mutations"; echo "import-exit=$?"
import-exit=0
```

The baseline at the merge-base was 3,722 passed, 5 skipped, 85.53%. The count reconciles: 3,722, minus the 160 tests collected under `tests/dashboard/`, plus 19 in `tests/unit/dashboard/test_settings.py`, is 3,581. Coverage fell 0.19 points because the deleted edit code was covered better than average.

## Route list

```text
$ uv run python -c "...every (path, method) with a method outside GET/HEAD in create_dashboard_app().routes..."
POST /runs/start
POST /runs/{run_id}/abort
```

## Smoke test

Run against this repo's real `.adw` (the main checkout) with a scratch `HOME`, `adw register --name adw` and `adw dashboard web --port 8765`. The script is TASK-004's recipe.

```text
$ shasum .adw/project.yaml .adw/commands/*/config.yaml   # before
94e1738f09cc40dbff364f116c1f8c26022ef533  .adw/project.yaml
4d65440748226bb8ea63052ecac5c995e33310e6  .adw/commands/build/config.yaml
798c6dbc7f6a868440a68f7c07111c50b1f0b551  .adw/commands/document/config.yaml
85f24743fba1dcfbf4345f36406d32ae575c0110  .adw/commands/plan/config.yaml
b8dee8996605ce8e4cf57663c0ea1f49479e9bfe  .adw/commands/ship/config.yaml
029de3b9a72c367b453b5854d597537cac08c562  .adw/commands/validate/config.yaml
registry: projects.yaml
tabs: project llm hooks logging git worktree task_manager webhook phases
project       page=200 htmx=200 partial=200
llm           page=200 htmx=200 partial=200
hooks         page=200 htmx=200 partial=200
logging       page=200 htmx=200 partial=200
git           page=200 htmx=200 partial=200
worktree      page=200 htmx=200 partial=200
task_manager  page=200 htmx=200 partial=200
webhook       page=200 htmx=200 partial=200
phases        page=200 htmx=200 partial=200
form controls on any tab: 27
$ shasum .adw/project.yaml .adw/commands/*/config.yaml   # after
94e1738f09cc40dbff364f116c1f8c26022ef533  .adw/project.yaml
4d65440748226bb8ea63052ecac5c995e33310e6  .adw/commands/build/config.yaml
798c6dbc7f6a868440a68f7c07111c50b1f0b551  .adw/commands/document/config.yaml
85f24743fba1dcfbf4345f36406d32ae575c0110  .adw/commands/plan/config.yaml
b8dee8996605ce8e4cf57663c0ea1f49479e9bfe  .adw/commands/ship/config.yaml
029de3b9a72c367b453b5854d597537cac08c562  .adw/commands/validate/config.yaml
byte-identical
```

The 27 form controls are 3 per tab: the header's project filter, the theme toggle and the settings project selector. `/partials/settings-content` (the settings content alone) has none.

## Screenshots

Headless Chrome, 1280×1700, against the smoke dashboard:

- [Basics](evidence/settings-project.jpg): the top-level values, with `security: —` (unset)
- [Task Manager](evidence/settings-task_manager.jpg): `type: linear`, `team_key: ADW`, the six-entry `state_mapping`, `labels.*`
- [Phases](evidence/settings-phases.jpg): plan, build, validate and document show the validation error of their `.adw/commands/<phase>/config.yaml`, named by path (a stale `timeout_seconds`, removed in #159). Ship shows `commands.version_bump: ./update.sh`

## Vulture diff

```text
== new at HEAD
src/adw/config/registry.py: unused method 'get_all_settings' (60% confidence)
src/adw/config/registry.py: unused method 'get_phase_settings' (60% confidence)
src/adw/models/command.py: unused variable 'source_pattern' (60% confidence)
== gone since merge-base
src/adw/dashboard/mutations.py: unused function 'save_phase_settings' (60% confidence)
src/adw/dashboard/mutations.py: unused function 'save_settings' (60% confidence)
src/adw/dashboard/partials.py: unused function 'phase_config_partial' (60% confidence)
src/adw/dashboard/partials.py: unused function 'task_manager_fields' (60% confidence)
src/adw/security/override.py: unused property 'overrides' (60% confidence)
```

- `source_pattern` is a `DocMappingConfig` field. Runs read it through `model_dump()` (`phase_runner.py:470`), which vulture can't see; the deleted editor read it by attribute.
- `overrides` left the list only because `settings.py` has a local variable of that name. Vulture matches names, and `security/override.py` is unchanged.

LOC (`find src -name '*.py' | xargs cat | wc -l`): 41,474 at the merge-base, 40,245 at HEAD, down 1,229.

## Divergence from the plan

- **The edit tests went in TASK-001, not TASK-002.** The save routes re-render `settings_content.html`, and after TASK-001 rewrote it, 31 tests in `test_settings_save.py`/`test_settings_phase.py` failed with `'sections' is undefined`. Those routes were unreachable by then, since no template linked to them, so their tests were deleted with the view. TASK-002 deleted the routes and the last file in `tests/dashboard/`.
- **The phase cards needed a fix, found by the screenshots (`a1cd34d5`).** The card listed a file only after it loaded, so a broken project `config.yaml` showed its error under the bundled file's name. Each file is now listed before it loads, the error is prefixed with the failing path, and paths are shortened. A test pins this.
- **Two `ConfigRegistry` methods are newly unused, left to 2.8.** `get_all_settings` and `get_phase_settings` had one `src` caller, the deleted settings builders, and now only `tests/unit/config/test_registry.py` calls them. The plan puts `ConfigRegistry` out of scope, and epic phase 2.8 owns "drop the sections and methods nothing reads". Phases 2.1–2.3, including `feature/adw-19`, which is in flight, also edit `registry.py`. The epic's 2.8 bullet now names the two methods.
- **The phase view merges tiers the way a run does.** This was added during plan validation (round 1 #1), and TASK-001 tests it. The user-tier cases use the document phase: the fixture's build file is intentionally invalid.

## Plan validation (pre-implementation, Codex)

**Rounds:** 3
**Plan status at validation:** draft
**Run on:** 2026-09-23

### Rounds

| Round | Findings | Applied | Deferred | Rejected |
|-------|----------|---------|----------|----------|
| 1     | 3        | 3       | 0        | 0        |
| 2     | 2        | 2       | 0        | 0        |
| 3     | 3        | 3       | 0        | 0        |

Round 3 still produced applies. They were precise fixes, so they were applied under the session's autonomy instruction, and no fourth round was run (see `validation/round-3.md`).

### Applied

#### Round 1
- PLAN.md:Scope, Out of Scope, Decisions, Risks; RESEARCH.md:Uncertainty; TASK-001; TASK-003 — Phase values are the effective ones, merged the way `PhaseRunner` merges them. That means the resolved tier's (user/bundled) `enabled`/`input_files`/`llm` under the project file, with phase-specific fields from the project file only. Tests pin the merge. (round-1 #1)
- TASK-004 — `$SCRATCH` is created with `mktemp -d` and cleaned up by a trap. (round-1 #2)
- PLAN.md:Decisions, Acceptance Criteria; TASK-002; TASK-004 — The write-surface guard covers every non-GET/HEAD method, not only POST. (round-1 #3)

#### Round 2
- TASK-003; PLAN.md:Scope, Risks — Epic phase 2.8's read-site list now points at `dashboard/settings.py`, not `dashboard/partials.py`. (round-2 #1)
- TASK-004 — The smoke test and screenshots run as one ordered block: hash, start the server, curl, screenshot, hash, stop. The server PID is in the EXIT trap. (round-2 #2)

#### Round 3
- TASK-002 — The deletion grep matches only the quoted `"has_project_config"` context key, so `settings.py` can keep using the `ConfigLoader` property. (round-3 #1)
- TASK-001 — A parametrized test shows that user-tier `lint_command`/`doc_mappings`/ship fields are ignored and project values win. (round-3 #2)
- TASK-003 — Phase 2.8 (epic and Linear ADW-24) gains the criterion that the dashboard has no direct phase-config loader after consolidation. (round-3 #3)

### Deferred

None.

### Rejected

None.
