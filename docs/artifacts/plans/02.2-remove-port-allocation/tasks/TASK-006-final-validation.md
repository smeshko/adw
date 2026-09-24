# TASK-006: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 02.2-remove-port-allocation`

## Goal

Confirm the plan is fully implemented, with runtime evidence for each acceptance criterion in `PLAN.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] `uv run pytest` passes, with coverage ≥ 80%
- [ ] `grep -rn "PortAlloc\|port_range\|ports.env" src` returns nothing, and `grep -rln "PortAlloc\|port_range\|ports.env" tests` lists only `tests/unit/models/test_config.py`
- [ ] Runtime smoke test in a scratch repo (see below)
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Runtime smoke test

Work in `$SCRATCH/portless`, where `$SCRATCH` is the session scratchpad, never in this checkout. Export `HOME=$SCRATCH/home` and `ADW_MOCK_EXECUTOR=1`, and run every `adw` command as `uv run --project <checkout> adw`.

- [ ] `git init` the scratch repo, make one commit, and write `.adw/project.yaml` with `name`, `language: python`, and this block:

  ```yaml
  worktree:
    max_concurrent: 1
    port_range:
      backend_start: 8000
      frontend_start: 8100
  ```

- [ ] `adw validate` exits 0 and reports no error on `worktree`. Save the transcript. Also run it with the overlapping `port_range` from `test_legacy_port_range_is_ignored`, which the old validator rejected. It must exit 0 too.
- [ ] Start `sleep 300 &` and write `trees/.locks/01TESTLOCK0000000000000000.lock` in the old lock-file format, as JSON with every key `get_active_runs` reads, plus the old port keys:

  ```json
  {"run_id": "01TESTLOCK0000000000000000", "pid": <sleep PID>,
   "start_time": "<now, UTC ISO-8601>", "worktree_path": "<scratch>/trees/01TESTLOCK0000000000000000",
   "backend_port": 9100, "frontend_port": 9200}
  ```
- [ ] `adw list --running` shows a table titled `Active Runs (1 of 15)` with `Run ID`, `Elapsed` and `Worktree` columns and no `Ports` column. `adw list --running --json` has no port keys. Save both transcripts. The "of 15" is the pre-existing default noted in PLAN.md, Out of Scope.
- [ ] `adw run "second run"` prints "Maximum concurrent runs reached (1)" and its suggestion, exits non-zero, and creates no worktree: `trees/` holds only `.locks`. Save the transcript and the `ls -A trees`. The CLI prints `ADWError.message`, not the code. `MAX_CONCURRENT_REACHED` itself is pinned by `test_check_can_start_or_raise_raises_at_limit`, which must pass in the full run.
- [ ] Kill the `sleep`, and delete `$SCRATCH/portless` and `$SCRATCH/home`.

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick this phase's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`, plus any epic-level criteria this phase satisfies. Under the grep criterion, note its one allowed file, `tests/unit/models/test_config.py`, which holds the legacy-config regression test (see PLAN.md, Decisions)
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.2 --plan 02.2-remove-port-allocation --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` (`In progress` after the first phase merges; `Done` when this is the last phase — then tick the remaining epic-level criteria and note any newly-unblocked epics)
