# TASK-001: Bundle the plan templates and port plan authoring

Depends on: None
Suggested commit: `feat(plans): bundle the plan templates and port plan authoring`

## Goal

`adw plan init`, `add-task` and `add-final` write the same tree that create-plan's `init_plan.py`, `add_task.py` and `add_final_task.py` write for the same inputs. The test pins this against a golden tree the scripts wrote.

## Files

- `src/adw/defaults/plans/`: new. Byte-for-byte copies of the ten templates listed in PLAN.md's Scope, taken from `~/.claude/skills/{create-plan,validate-plan,review-plan}/references/`. The two `round.md.tmpl` files become `validation-round.md.tmpl` and `review-round.md.tmpl`.
- `src/adw/plans/__init__.py`: new. A docstring naming the submodules, no re-exports.
- `src/adw/plans/templates.py`: new.
  - `read_template(name) -> str` reads `files("adw") / "defaults" / "plans" / name` as UTF-8.
  - It raises `PlanError("INVALID_PLAN", …)` for an unknown name.
- `src/adw/plans/paths.py`: new.
  - `plans_dir(root) -> Path` is `root / "docs" / "artifacts" / "plans"`.
  - `plan_dir(root, slug)` is that plus the slug.
  - `slugify(text)` is the scripts' `slugify`.
  - Later tasks reuse all three.
- `src/adw/plans/authoring.py`: new.
  - `VALID_RISKS`, `RESEARCH_REQUIRED` and `TASK_TYPES = ("impl", "checklist")`.
  - `init_plan(root, *, title, risk, slug=None, today=None) -> Path` returns the plan dir.
  - `add_task(root, slug, *, task_type, title, depends=None) -> str` returns the task id.
  - `add_final_task(root, slug) -> str` returns the task id.
  - `depends` is a list of ids, rendered joined with `,`.
  - Each function keeps its script's replace calls, in the same order and each with count 1, and the script's `next_task_number` and `append_task_line`.
  - Files are written with `encoding="utf-8"`.
  - Validation runs before anything is written, so a failed call leaves no stray task file. (The scripts write the task file first and only then find `## Tasks` missing.)
- `src/adw/exceptions.py`: add `PlanError(ADWError)` with a docstring that lists its codes.
- `src/adw/cli/plan.py`: new.
  - `plan_app = typer.Typer(name="plan", help=…)`.
  - A `_root(root: Path | None) -> Path` helper: `--root` resolved, else `git rev-parse --show-toplevel` from the cwd, else the cwd.
  - Commands `init` (`--title`, `--risk`, `--slug`, `--root`), `add-task` (`SLUG`, `--type`, `--title`, `--depends`, `--root`) and `add-final` (`SLUG`, `--root`).
  - `init` prints the script's four lines: `created: <dir>`, `slug:    <slug>`, `risk:    <risk>`, `research: …`. `add-task` and `add-final` print the id.
  - A `PlanError` prints `error: <message>` to stderr and exits 1.
- `src/adw/cli/app.py`: `app.add_typer(plan_app, name="plan")`.
- `tests/fixtures/plans/golden/add-a-dry-run-flag-to-the-importer/`: new. The skill scripts' output, untouched.
- `tests/fixtures/plans/golden/README.md`: new. What the tree is and the exact commands that regenerate it.
- `tests/unit/plans/__init__.py`, `tests/unit/plans/test_authoring.py`: new.
- `tests/unit/cli/test_plan.py`: new.

## Acceptance

- [ ] `test_cli_scaffold_matches_skill_golden_tree` runs these in `tmp_path` through `CliRunner`:
  - `adw plan init --title "Add a --dry-run flag to the importer" --risk medium`
  - `add-task --type impl --title "Parse the --dry-run flag"`
  - `add-task --type checklist --title "Document the flag in the README" --depends TASK-001`
  - `add-final`

  The test then asserts the same relative file list and the same bytes as the golden tree. A `normalise` helper rewrites `^Created: \d{4}-\d{2}-\d{2}$` to `Created: <date>` on both sides, and names every normalisation it applies.
- [ ] Error paths, each raising `PlanError` with the right code and writing nothing:
  - `init_plan` on an existing dir (`PLAN_EXISTS`)
  - `init_plan` with an unknown risk, or with a title that slugifies to nothing (`INVALID_PLAN`)
  - `add_task` / `add_final_task` on a missing plan (`PLAN_NOT_FOUND`)
  - `add_task` with an unknown type, or on a PLAN.md without `## Tasks` (`INVALID_PLAN`)
- [ ] `init_plan` with risk `small` writes no `RESEARCH.md`.
- [ ] With `TASK-001` and `TASK-003` in `tasks/`, the next id is `TASK-004`.
- [ ] `adw plan init` run twice exits 1, with `error: plan directory already exists: …` on stderr.
- [ ] Without `--root`, `adw plan init`, run from a subdirectory of a `git_repo`, writes under the repo's toplevel.
- [ ] `uv run pytest tests/unit/plans tests/unit/cli/test_plan.py -o addopts=""` and `scripts/preflight.sh` pass.

Evidence:
- the golden commands' output;
- `diff -r` of each template copy against its skill original (empty);
- the RED failure of the golden test (`No such command 'plan'`), then the GREEN pytest tail and the preflight tail.

## Steps

### RED
- [ ] In a scratch dir, run the four skill-script commands from the README (`--root <scratch>`). Copy `docs/artifacts/plans/add-a-dry-run-flag-to-the-importer/` into `tests/fixtures/plans/golden/`, and write the README.
- [ ] Write `test_plan.py`'s golden and error tests, and `test_authoring.py`. Run them: they fail.

### GREEN
- [ ] Copy the templates; `diff` each against its original.
- [ ] Add `PlanError`, `paths.py`, `templates.py`, `authoring.py`, `cli/plan.py`, and the `add_typer` line.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- The final-validation template holds `<plan-slug>` twice. The script replaces only the first, so the stamped file keeps `--plan <plan-slug>` on its link line. The port must do the same.
- This task copies `template-task-final-validation.md` verbatim, so `grep -rn "\.claude/skills" src/adw` hits it until TASK-004 changes that line.
- `tests/unit/cli/conftest.py`'s autouse `isolated_cwd` already puts every CLI test in `tmp_path`. The default-root test builds its repo with the `git_repo` fixture, which also uses `tmp_path`, and `monkeypatch.chdir`s into a subdirectory.
- Click 8.3's `CliRunner` result keeps `stdout` and `stderr` apart, so the tests assert on each.
