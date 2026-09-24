# Plan: adw.plans: plan files in ADW

Status: in-progress
Branch: feature/adw-39
Risk: medium
Epic: 04 — Plan-driven runs ([epic](../../epics/04-plan-driven-runs.md))
Phase: 4.1 — adw.plans: plan files in ADW
Linear: ADW-39
Created: 2026-09-24

## Goal

ADW reads and writes the plan directory format that the plan skills use (`docs/artifacts/plans/<slug>/`). It does this through one tested package, `adw.plans`, and an `adw plan` CLI group that Epic 05's prompts call through Bash.

## Scope

- **Templates.** `src/adw/defaults/plans/` holds copies of the skills' templates under the skills' file names:
  - from create-plan: `template-plan.md`, `template-research.md`, `template-decisions.md`, `template-task-implementation.md`, `template-task-checklist.md`, `template-task-final-validation.md`
  - from validate-plan: `VALIDATION.md.tmpl`, `validation-round.md.tmpl`
  - from review-plan: `REVIEW.md.tmpl`, `review-round.md.tmpl`

  Both skills ship a file called `round.md.tmpl`, so each copy is prefixed with its skill's name. `adw.plans.templates.read_template(name)` loads a template through `importlib.resources`, as `CommandResolver` does for `defaults/commands` (TASK-001).
- **Authoring.** `adw.plans.authoring` gets `init_plan`, `add_task` and `add_final_task`, ported from `init_plan.py`, `add_task.py` and `add_final_task.py` (TASK-001).
- **Reading.**
  - `adw.plans.model` gets `Plan` and `PlanTask`.
  - `adw.plans.reader` gets `load_plan`, `list_plans`, `list_tasks` and `resolve_plan_by_branch`. They port `list_plans.py`, `list_tasks.py`, and the slug-from-branch rule shared by review-plan's `resolve_plan.py` and `archive_plan.sh` (TASK-002).
- **State.** `adw.plans.state` gets `mark_task_done`, `set_plan_status` and `set_plan_branch` (TASK-003).
- **Epics.** `adw.plans.epics` gets `resolve_epic_file`, `link_plan` and `epic_status`, ported from create-epic's `link_plan.py` and `epic_status.py` (TASK-004).
- **Archive.** `adw.plans.archive.archive_plan(root, slug, merged_on)` moves the plan to `plans/archive/<YYYY-MM-DD>-<slug>/`, adding `-2`, `-3` and so on when that name is taken. It also repairs the relative links the move breaks (TASK-005).
- **CLI.** `src/adw/cli/plan.py` adds an `adw plan` Typer group, registered in `cli/app.py`:
  - `init`, `add-task`, `add-final` (TASK-001)
  - `list`, `show`, `tasks` (TASK-002)
  - `link` (TASK-004)

  Every command takes `--root`. Without it, the root is the cwd's git toplevel, or the cwd outside a repo, the same rule as the skills' `find_project_root`.
- **Errors.** A new `PlanError(ADWError)` in `adw/exceptions.py` (TASK-001).
- **Docs.** An `AGENTS.md` architecture note on `adw.plans`, its templates and the golden test (TASK-006).

## Out of Scope

- **The git and GitHub steps of the lifecycle scripts.** This covers `prepare_branch.sh` (branch, stash, plan commit) and, in `archive_plan.sh`, the merged-PR check, the checkout, the pull and the branch delete. Phase 4.4 cuts the branch and makes the plan commit. Phase 5.7 merges and commits the archive. Here, `archive_plan` only moves files.
- **Linear writes.** They belong to Epic 06; `adw.plans` never calls Linear.
- **Epic authoring:** `add_epic.py`, `add_phase.py`, `init_epics_index.py`, `set_linear.py` and `set_milestone.py`. Epic 06's `adw run --epic` needs only `link_plan` and `epic_status`.
- **Wiring plans into runs.** Phase 4.3 adds `RunContext.plan_slug` and the `{{plan.*}}` variables, and Epic 05 writes the prompts.
- **CLI commands for `mark_task_done`, `set_plan_status`, `set_plan_branch` and `archive_plan`.** Epic 05 calls them from ADW's Python code: 5.4's build loop and 5.7's ship. A prompt that needs one can add its command then.
- **The skills under `~/.claude/skills`.** They stay the interactive tools and are not edited.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **The format is produced by twelve small scripts:** eleven Python scripts plus `archive_plan.sh`. Each is one template substitution or one regex over plain Markdown. All of them resolve the root the same way (`--root`, else the git toplevel, else the cwd).
- **Substitution is first-occurrence `str.replace`.** To write identical bytes, a port must replace the same placeholder strings, once each, in the same order.
- **Two acceptance criteria collide on one template line.** The final-validation template tells its reader to run `python3 ~/.claude/skills/create-epic/scripts/link_plan.py`. A verbatim copy under `src/adw/defaults/plans/` makes `grep -rn "\.claude/skills" src/adw` hit (see Decisions).
- **`archive_plan.sh` leaves two links broken:** the epic's `**Plan**:` line and the archived PLAN.md's `Epic:` link. Every archive in this repo so far fixed them by hand.
- **Packaging needs no change.** Hatch ships every file under `src/adw`, which is how `defaults/commands/*` reaches the wheel today.
- **Baseline.** `uv run pytest` on `779ecec6`: 2982 passed, 5 skipped, coverage 84.79% (gate 80%).

## Decisions

- **Vertical slices.** Each task ships its functions together with their `adw plan` commands and tests, so every commit is usable end to end.
- **The golden tree is the skill scripts' own output, committed as a fixture.** CI has no `~/.claude/skills`, so the test cannot run the scripts. `tests/fixtures/plans/golden/` holds, untouched, the tree the scripts wrote for one title, risk and task list. A README next to it records the exact commands that regenerate it. The test runs `adw plan init/add-task/add-final` with the same inputs, then compares the file lists and the bytes, with `Created:` normalised.
- **ADW's final-validation template calls `adw plan link`, not the skill script.** This is the one line where the two criteria collide. The template is an instruction an agent follows during an ADW run, and a CI box or scratch repo has no `~/.claude/skills`, so the skill path would be wrong there anyway. ADW's copy says `adw plan link <NN> --phase <NN.M> --plan <plan-slug> --status done`. The golden test's normaliser maps the skill's command to ADW's, and names it as the only substitution besides the date. Every other template byte stays identical, including PLAN.md's pointer to `scripts/add_task.py`.
- **`adw plan link` joins the six commands the epic lists.** The final-validation template needs a real command to point at. It is a thin wrapper over `link_plan`.
- **`archive_plan` repairs links; the skill doesn't.** Epic 05's ship phase runs `archive_plan` with nobody to fix links by hand. The move puts the plan one level deeper:
  - In each Markdown file under the moved dir, a relative link that pointed outside the old plan dir is recomputed from the new location. Links inside the plan dir stay as they are.
  - In the epic files, links into `../plans/<slug>/` become `../plans/archive/<name>/`.
- **`archive_plan` only moves files, and takes `merged_on: date`.** The archive date is the PR's merge date, which only the caller knows.
- **Output is plain and tab-separated, as the skills print it.**
  - `list` prints `<slug>\t<status>\t<title>` and `tasks` prints `<task-id>\t<done|pending>\t<task-file>\t<title>`, as `list_plans.py` and `list_tasks.py` do.
  - `show` prints `key=value` lines, like the skills' `resolve_plan.py`.
  - Output goes through `typer.echo`, not Rich, which would wrap and colour text that prompts parse from Bash.
  - Errors go to stderr as `error: <message>`, with exit code 1.
- **Functions take the project root explicitly.** Only the CLI works out a default. Runs (4.3) will pass the worktree root, and tests pass `tmp_path`. Nothing in `adw.plans` runs git.
- **`Plan` stores ids, not display strings.** `epic="04"`, `phase="4.1"`, `linear="ADW-39"` are the first token of each field, and `none` becomes `None`. Phase 4.3's `RunContext` needs the ids; the titles stay in the file.
- **Errors raise `PlanError`, not `sys.exit` as the scripts do,** so run code can catch them. Its codes: `PLAN_NOT_FOUND`, `PLAN_EXISTS`, `INVALID_PLAN`, `TASK_NOT_FOUND`, `EPIC_NOT_FOUND`, `PHASE_NOT_FOUND`, `AMBIGUOUS_PLAN`.
- **Reading is lenient and writing is strict.**
  - `load_plan` accepts any `Status:` value, and a missing one reads as `unknown`, as in `list_plans.py`.
  - `set_plan_status` accepts only `draft`, `ready`, `in-progress` and `done`; `init_plan` accepts only the five risk tiers; `link_plan` accepts only `planned`, `in-progress` and `done`.
- **`adw/plans/__init__.py` re-exports nothing.** Callers import the submodules, following 01.3's trim of unused re-exports.
- **The round-trip fixture is this plan.** `tests/fixtures/plans/04.1-adw-plans-module/` is a snapshot of this directory, taken in TASK-002: a real `/create-plan` plan from this repo, with one task done and the rest pending.
- **No `validate-plan` pass.** The requested flow for this phase is create-plan → implement-plan → review-plan. The change is additive: a new package and a new CLI group, touching `cli/app.py` and `exceptions.py` only to register them. The golden test pins the format against the skills' own output, and review-plan's adversarial pass covers the implementation.

## Risks

- **ADW's copy of the format drifts from the skills over time.** Mitigation: the golden test pins today's output. The AGENTS.md note (TASK-006) says to update the bundled templates and regenerate the golden tree together whenever a skill changes.
- **Byte-level details break "identical trees":** a trailing newline, the encoding, or a replace count. Mitigation: the ports keep the scripts' exact `str.replace(…, 1)` calls and `append_task_line`'s separator rule. The golden test compares bytes, not parsed content, and `adw.plans` reads and writes UTF-8 explicitly.
- **Link repair corrupts a link.** Mitigation: only relative Markdown link targets change (no scheme, no leading `/` or `#`), and an anchor carries over. Tests cover a link that leaves the plan dir, one that stays inside it (`tasks/` → `../PLAN.md`), an external URL, and the epic side.
- **Tests write into the checkout.** Mitigation: every function takes `root`, and the tests pass `tmp_path`. The CLI tests run under `tests/unit/cli/`'s autouse `isolated_cwd` and pass `--root`, and the default-root test runs in the `git_repo` fixture.

## Acceptance Criteria

- [ ] For the same title, risk and task list, `adw plan init/add-task/add-final` and the skill scripts produce identical trees once dates are normalised (and the final-validation link command mapped; see Decisions). Evidence: the golden CLI test, RED then GREEN, plus the fixture README's regeneration commands.
- [ ] `adw plan tasks <slug>` and `mark_task_done` round-trip on a plan written by `/create-plan` in this repo. Evidence: the round-trip test on `tests/fixtures/plans/04.1-adw-plans-module/`, RED then GREEN.
- [ ] `adw plan list` prints slug, status and title for every plan, archived ones excluded. Evidence: the list test, and the scratch-repo transcript.
- [ ] `grep -rn "\.claude/skills" src/adw` returns nothing. Evidence: the grep output.
- [ ] Lint and tests pass. Evidence: `scripts/preflight.sh` and the tail of `uv run pytest`, with coverage ≥ 80%.
- [ ] A scratch-repo transcript of `adw plan init` → `add-task` ×2 → `add-final` → `tasks` → `list`, run with the worktree's `.venv/bin/adw`, is saved under `evidence/` and goes into the PR. Evidence: the transcript file.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Bundle the plan templates and port plan authoring
- [x] TASK-002: Parse PLAN.md into a Plan model and add list, show and tasks (depends on TASK-001)
- [x] TASK-003: Port the plan state updates (depends on TASK-002)
- [x] TASK-004: Port epic linking and status, and add adw plan link (depends on TASK-001)
- [x] TASK-005: Archive a plan and repair its relative links (depends on TASK-001)
- [ ] TASK-006: Document adw.plans for agents (depends on TASK-001,TASK-002,TASK-003,TASK-004,TASK-005)
- [ ] TASK-007: Final Validation
