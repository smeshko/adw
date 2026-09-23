# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.8-fix-path-config-default-drift`

## Goal

Confirm the plan is fully implemented and production-ready, and write the PR evidence to `docs/artifacts/plans/01.8-fix-path-config-default-drift/VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes with no issues.
- [ ] Full test suite passes: `uv run pytest`, green, coverage ≥ 80%. Rerun `test_stats_display_with_real_data` once if it flakes.
- [ ] The plan-level greps all pass:
  - `grep -rn '"In Review"' src/adw --include='*.py'` → only `models/config.py`
  - `grep -rn "0.000009\|_load_project_build_command\|DEFAULT_CONFIG_TEMPLATE\|DEFAULT_STATE_MAPPINGS" src` → empty
  - `grep -rn '"logs" / "live.log"' src` → empty
- [ ] **Log search and live stream on a real run.**
  - From the worktree, run `uv run adw dashboard web --port 8765` against the real `~/.adw` index.
  - Open `/runs/01KHAPGM6PRX55TZQF5V082DDH` (or any run in the main checkout's `.adw/runs`), then its log search at `/runs/<id>/logs`.
  - Screenshot both, showing entries (Claude in Chrome). Only view pages; click no abort, delete or settings controls.
  - Capture `curl -N http://127.0.0.1:8765/runs/<id>/logs/stream | head -20`, which shows `event: log-line`.
  - Stop the server.
- [ ] **Interrupted-run stream closes.**
  - In a scratch project, copy one real run dir and set its `context.json` `status` to `interrupted`.
  - Add an index entry through a temp `HOME`.
  - Show that `curl -N …/events` and `…/logs/stream` both return and exit on their own.
- [ ] **Ship hook env.**
  - In a scratch git repo with a temp `HOME`, write `.adw/project.yaml` with `name: demo` and `build_command: "echo built"`.
  - Add a project override `.adw/commands/ship/post.sh` that runs `env | grep '^ADW_SHIP_' > ship-env.txt`.
  - Run `ADW_MOCK_EXECUTOR=1 uv run --project "$WORKTREE" adw run --phase ship "noop"`, where `$WORKTREE` is the checkout that holds this branch.
  - Show that `ship-env.txt` contains `ADW_SHIP_BUILD_CMD=echo built`. If the override mechanism differs, use whatever `CommandResolver` accepts for a project-level ship hook.
- [ ] **Init + validate.** In a fresh scratch git repo, show the transcript of `adw init --no-interactive`, then `cat .adw/project.yaml | grep '^name:'`, then `adw validate`, ending `0 errors`.
- [ ] **Cost agreement.** From the running dashboard (step above), screenshot or copy the run-detail total cost and the analytics per-project cost for a project with one run. Or cite `test_run_detail_cost_matches_analytics` output if no real project has exactly one run.
- [ ] Write `VALIDATION.md` with:
  - the RED/GREEN lines from each task's new tests
  - the greps
  - the screenshots and curl transcripts
  - the hook-env dump
  - the init/validate transcript
  - the cost comparison
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced. No criterion is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 1.8's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`. Next to the epic-level "Bugs B1–B5, B9–B12, B16, B17 and B21 each have a regression test" line, record which B3/B4/B11/B17/B21 tests this phase added.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.8 --plan 01.8-fix-path-config-default-drift --status done`
- [ ] Update epic 01's row in `docs/artifacts/epics/EPICS.md`. It is already `In progress` once phase 1.1 merged; keep it so unless this is the last phase.
