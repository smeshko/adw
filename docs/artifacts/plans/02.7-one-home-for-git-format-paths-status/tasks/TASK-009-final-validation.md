# TASK-009: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: finalize 02.7-one-home-for-git-format-paths-status`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes with no issues.
- [ ] `uv run pytest` passes with coverage ≥ 80%, and its summary line reports no warnings. Record the pass/skip counts against the baseline on `7b61e72a` (after #212): 2982 passed, 5 skipped, 84.79%.
- [ ] Scratch-project transcripts, saved under the plan's `evidence/` for the PR:
  - Use this worktree's binary, `/Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-23/.venv/bin/adw`, not a bare `adw` (that is the main checkout's `staging` install).
  - Run them in scratch dirs under the session scratchpad, with `HOME` pointed at a scratch dir.
  - Before committing, grep the evidence files for the username; Rich wraps long paths across lines.

  The transcripts:
  - **Outside a project:** in an empty dir, run `adw status; echo "exit=$?"; ls -a`.
  - **Colours:** in a scratch project (`adw init --no-interactive`) with one fabricated run per status, capture `FORCE_COLOR=1 COLUMNS=160 adw list` and `FORCE_COLOR=1 adw status <id>` for each status.
    - Fabricate each run by writing a `context.json` through `RunContext(...).model_dump_json()` under `.adw/runs/<id>/`.
    - Reduce each transcript to a table of status → the SGR sequence before the status word, from both commands.

### Acceptance-to-evidence matrix (one per `PLAN.md` criterion)

- [ ] **Every git and gh subprocess goes through `adw.git`.**
  - `rg -U 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src` prints nothing.
  - `rg -l 'import subprocess' src` prints `src/adw/git.py` and `src/adw/core/run_trigger.py` only.
  - `ls src/adw/hooks src/adw/worktree` shows none of the four deleted modules.
- [ ] **A timed-out git command raises instead of hanging.** `uv run pytest tests/unit/git/test_run.py -o addopts="" --durations=5` passes. `test_git_fetch_times_out_against_a_sleeping_git` takes under 5 s. `test_timeout_sends_sigterm_first`, both cases of `test_escalates_to_sigkill_only_after_the_grace_period` (elapsed ≥ timeout + grace) and `test_interrupt_stops_git_and_propagates` also pass.
- [ ] **Each formatter and the status-style map is defined exactly once.**
  - The formatter `rg` lists only the five `adw.format` functions.
  - `rg -n 'STATUS_COLORS|STATUS_ICONS|_get_status_style' src` prints nothing.
  - `rg -n ':,?\.2f\}' src` prints only `format_cost` in `src/adw/format.py`.
  - `status_badge.html` holds no map.
  - Write the list of formatters and the greps into the PR body.
- [ ] **`adw list` and `adw status` colour every status identically.** `test_list_and_status_colour_each_status_alike` passes, and the colour transcript table shows the same SGR per status in both commands.
- [ ] **Run status is a `RunStatus` everywhere.**
  - Both status greps from TASK-004's Acceptance print nothing. There is no `progress.py` exception any more, because TASK-006 removed it.
  - `RunContext.status` and `IndexEntry.status` are annotated `RunStatus`: `rg -n "status: RunStatus" src/adw/models` shows both.
  - `test_update_run_validates_status` passes.
  - The full suite reports no warnings.
  - `test_context_json_status_round_trips` passes.
- [ ] **One helper writes state files atomically.** `tests/unit/test_fs.py` (including the two mode tests) and the index, registry and context failure tests pass, and `rg -n 'os\.fsync|\.tmp"|\.rename\(' src` prints only `src/adw/fs.py`.
- [ ] **One runs-path helper, one atomic writer, no hand-written status or phase lists.**
  - `rg -n '/ "runs"' src` prints only `src/adw/core/constants.py`.
  - `rg -n 'atomic_write\(' src | rg -v 'def |atomic_write_config'` lists the seven callers from TASK-007.
  - `rg -n "VALID_STATUSES|AVAILABLE_PHASES|canonical_phases" src tests` prints nothing.
- [ ] **`adw status` outside a project errors and creates nothing.** `test_read_only_commands_outside_a_project_create_nothing` passes for all seven argument lists. The outside-a-project transcript shows `No .adw directory found`, `exit=1`, and an `ls -a` with nothing but `.` and `..`.
- [ ] **Lint and tests pass.** The preflight and full-suite tails above.

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick this phase's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`. The first criterion's grep matched nothing even before this phase, so add a sub-bullet recording the stronger `rg -U` / `import subprocess` checks this phase used.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.7 --plan 02.7-one-home-for-git-format-paths-status --status done`
- [ ] Leave the epic's row in `docs/artifacts/epics/EPICS.md` at `In progress`: phases 2.8–2.12 remain.
