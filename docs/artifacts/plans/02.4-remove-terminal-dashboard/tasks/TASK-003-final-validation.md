# TASK-003: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 02.4-remove-terminal-dashboard`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] Project analyzer/linter passes with no issues: `scripts/preflight.sh`
- [ ] Full test suite passes: `uv run pytest` is green with coverage ≥ 80%. Expect about 3,713 passed (3,817 at baseline, minus 104 deleted tests) and coverage at or above the baseline's 85.05%.
- [ ] Module/import boundaries respected: `uv run python -c "import adw.cli.app, adw.cli.global_commands, adw.dashboard.routes"` exits 0
- [ ] The epic's grep returns nothing: `grep -rn "cli.dashboard import\|cli/dashboard.py\|test_stats_display_with_real_data" src tests AGENTS.md`
- [ ] The wording greps return nothing: `grep -rni "global \(adw \)\?dashboard" src` and `grep -rn "TUI" src`
- [ ] Nothing new is dead. Build a baseline from the merge-base, compare it with HEAD, and expect empty output:

  ```bash
  mkdir -p "$SCRATCH/base" && git archive "$(git merge-base HEAD origin/staging)" src | tar -x -C "$SCRATCH/base"
  uvx vulture "$SCRATCH/base/src/adw" --min-confidence 60 | sed -E 's/^[^ ]*src\/adw/src\/adw/; s/:[0-9]+:/:/' | sort > "$SCRATCH/vb.txt"
  uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vh.txt"
  comm -13 "$SCRATCH/vb.txt" "$SCRATCH/vh.txt"
  ```

- [ ] Manual smoke test, run from a scratch directory with `HOME` set to a scratch home, so nothing touches the checkout or the real `~/.adw`:

  ```bash
  ADW="$PWD/.venv/bin/adw"; mkdir -p "$SCRATCH/home" "$SCRATCH/smoke" && cd "$SCRATCH/smoke"
  HOME="$SCRATCH/home" "$ADW" global --help                        # list, stats, clean; no dashboard
  HOME="$SCRATCH/home" "$ADW" global dashboard; echo "exit=$?"     # No such command 'dashboard', exit=2
  HOME="$SCRATCH/home" "$ADW" register --help                      # "ADW web dashboard"
  HOME="$SCRATCH/home" "$ADW" dashboard web --no-browser --port 8765 &
  for i in $(seq 10); do code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/); [ "$code" = 200 ] && break; sleep 1; done; echo "status=$code"   # status=200
  kill %1
  ```

- [ ] LOC: `find src -name '*.py' | xargs cat | wc -l` drops by at least 1,100 from 43,445
- [ ] Write `docs/artifacts/plans/02.4-remove-terminal-dashboard/VALIDATION.md` with:
  - a table of each acceptance criterion and its evidence
  - the preflight output and the pytest summary and coverage lines
  - the greps, the `vulture` diff, and the LOC before and after
  - the smoke transcripts, including the curl status
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] In `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`:
  - Tick phase 2.4's four `### Acceptance criteria`.
  - Leave unticked the epic-level criterion "`src/adw` has no `security/` … and no `cli/dashboard.py`"; other phases still own the packages it names. Add a note that `cli/dashboard.py` is gone as of phase 2.4.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.4 --plan 02.4-remove-terminal-dashboard --status done`
- [ ] Update Epic 02's row in `docs/artifacts/epics/EPICS.md`:
  - It reads `Blocked` today. Set it to `In progress` when this phase merges, if no other Epic 02 phase has done so first.
  - Set it to `Done` only when the epic's last phase merges. Then tick the remaining epic-level criteria and note any newly unblocked epics.
