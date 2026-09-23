# ADW — agent guide

ADW (Agentic Development Workflow) is a Python 3.13 CLI, `adw`, that drives Claude Code through plan → build → validate → document → ship phases to take a ticket to a merged PR.

## Commands

- Setup: `uv sync`
- Fast feedback — lint, format, types; the same gates as CI's lint and typecheck jobs: `scripts/preflight.sh`
- Full suite: `uv run pytest` — ~3 min, enforces ≥80% coverage through `addopts`. There is no `--timeout` flag.
- Partial run: `uv run pytest <path> -o addopts=""` — drops the coverage gate, which a partial run always fails.

## Workflow

Work moves through the plan skills: `create-plan` → `validate-plan` → `implement-plan` → `review-plan` → `create-pr` → `archive-plan`, or `ship-phase` end to end. `create-epic` / `create-project` sit above plans.

- Base branch: `staging`. Every PR targets `staging`; `main` lags far behind and is never a PR target.
- CI (`.github/workflows/ci.yml`) runs lint, typecheck and the full suite on each PR; green CI gates the merge.
- Tracker: Linear team **ADW** — the workspace holds other teams, so name ADW explicitly. Reading issues: `docs/agents/issue-tracker.md`.
- Labels — apply the ones that fit, never create new ones:
  - Type: `feature`, `bug`, `refactoring`
  - Platform: `core`, `cli`, `dashboard`
  - Source: `code-review`, `dogfooding`, `field-report`
  - `epic` on epic parent issues

## Code standards

- ruff and mypy `--strict` (config in `pyproject.toml`) gate CI; `scripts/preflight.sh` must pass before a task is done.
- Tests follow `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`: test behaviour, error paths, security and I/O; leave trivial attribute, Pydantic-smoke, import-smoke and help-text tests unwritten.
- Tests run on `MockExecutor` (`ADW_MOCK_EXECUTOR=1`, set in `tests/conftest.py`).
- A test that touches git, invokes `adw run`, or executes a phase hook runs inside a throwaway directory — `git_repo` (an isolated temp repo) or `tmp_path`, entered with `monkeypatch.chdir`. From the checkout, those code paths act on the checkout itself: they create branches and worktrees, and `ship/post.sh` commits and pushes.
- `docs/CONDITIONAL_DOCS.md` maps each subsystem to its deep-dive doc — read the matching one before changing orchestration, phases or the dashboard.

## Architecture notes

- Config hierarchy: `ProjectConfig` (`.adw/project.yaml`) → `CommandConfig` (a phase's `config.yaml`) → merged `PhaseConfig`.
- `test_command` / `build_command` live only on `ProjectConfig`; `PhaseRunner` injects them into the validate and ship templates.
- Built-in phases live in `src/adw/defaults/commands/<phase>/` (`config.yaml`, `prompt.md`, optional `pre.sh` / `post.sh`). Their BMAD-derived workflow files point at `{project-root}/_bmad/...` inside *target* projects — product code, kept on purpose.
- `ValidationConfig` is an alias of `ValidateCommandConfig`, re-exported from `adw.validation`.
- `YAMLWithComments` (`src/adw/config/yaml_generator.py`) renders `project.yaml` and phase configs.
- Runtime state is gitignored: `.adw/` (runs, this repo's own ADW config) and `trees/` (worktrees ADW creates for its runs).

## Gotchas

- Flaky: `tests/integration/cli/test_dashboard_integration.py::TestDashboardStatistics::test_stats_display_with_real_data` — rerun it once before investigating.
