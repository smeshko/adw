# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 02.3-remove-webhook-server`

## Goal

Confirm the plan is fully implemented, and write the PR evidence to `docs/artifacts/plans/02.3-remove-webhook-server/VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes with no issues.
- [ ] Full test suite passes: `uv run pytest`, green, coverage ≥ 80% (baseline 85.05%). Rerun `test_stats_display_with_real_data` once if it flakes.
- [ ] **CLI surface.** Capture these transcripts:
  - `uv run adw --help`: no `webhook` group
  - `uv run adw webhook --help`: exits 2 with "No such command"
  - `uv run adw dashboard web --help | grep -ci webhook`: prints `0`
- [ ] **The greps:**
  - `grep -rn "adw.webhook\|adw.server\|WebhookConfig" src tests` returns nothing
  - `grep -rni webhook src` matches only `src/adw/config/checker.py`
  - `grep -rni webhook docs --exclude-dir=artifacts` returns nothing
  - `ls src/adw/webhook src/adw/server src/adw/models/webhook.py src/adw/cli/webhook.py src/adw/cli/wizard/webhooks.py` reports that each is missing
- [ ] **Old config under `adw validate`.**
  - In a scratch git repo (`mktemp -d`, `git init`), write `.adw/project.yaml` with the pre-epic fixture from RESEARCH.md.
  - Run `uv run --project "$WORKTREE" adw validate`: 0 errors, one warning on `webhook`, exit 0.
  - Run it again with `--strict`: exit 1.
  - Capture both transcripts, with `echo $?`.
- [ ] **Dashboard and New Run.** Use a temp `HOME` and a scratch project; never this checkout.
  - `export HOME=$(mktemp -d)`, then make a scratch git repo with one commit and run `uv run --project "$WORKTREE" adw init --no-interactive` in it.
  - Register it with `uv run --project "$WORKTREE" adw register`, run from inside that repo.
  - `ADW_MOCK_EXECUTOR=1 uv run --project "$WORKTREE" adw dashboard web --no-browser --port 8765` (run in the background).
  - `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/` prints `200`. Capture it.
  - In Chrome (Claude in Chrome), open `http://127.0.0.1:8765/`, click "+ New Run", pick the scratch project, enter "noop", and submit. Screenshot the run-started view.
  - Show the mocked run in the scratch `$HOME/.adw` index or the scratch repo's `.adw/runs/`, for example with `uv run --project "$WORKTREE" adw list` from the scratch repo.
  - Stop the server.
- [ ] Write `VALIDATION.md` with:
  - the RED/GREEN lines from TASK-002 and TASK-003
  - the transcripts and greps above
  - the curl output
  - the New Run screenshot
  - the run listing
  - the full-suite tail
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced. No criterion is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 2.3's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`. Leave the epic-level criteria unticked: they need 2.1, 2.2, 2.4 and the rest.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.3 --plan 02.3-remove-webhook-server --status done`
- [ ] Update epic 02's row in `docs/artifacts/epics/EPICS.md`: set it to `In progress` once this phase merges, unless another epic-02 phase has already done so.
