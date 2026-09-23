# TASK-004: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 02.5-make-dashboard-settings-read-only`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] Project analyzer/linter passes with no issues: `scripts/preflight.sh`
- [ ] Full test suite passes: `uv run pytest` is green with coverage ≥ 80%.
  - Expect about 3,574 + N passed: 3,730 at baseline, minus the 156 in `tests/dashboard/`, plus N new in `tests/unit/dashboard/test_settings.py`.
  - Expect coverage near the baseline's 85.56%.
- [ ] Module/import boundaries respected: `uv run python -c "import adw.dashboard.server, adw.dashboard.settings, adw.dashboard.routes, adw.dashboard.partials, adw.dashboard.mutations"` exits 0
- [ ] Before the steps below, set up the scratch dir and a cleanup trap: `SCRATCH="$(mktemp -d)"; trap 'rm -rf "$SCRATCH"' EXIT; test -d "$SCRATCH"`. Copy anything worth keeping, such as screenshots, out of it before the shell exits.
- [ ] Route list: print every `(path, method)` pair with a method other than `GET`/`HEAD` from `create_dashboard_app().routes`. Expect exactly `POST /runs/start` and `POST /runs/{run_id}/abort`.
- [ ] `ls tests/dashboard` fails, and `grep -rn "tests/dashboard" pyproject.toml tests` is empty
- [ ] Nothing new is dead. Build a baseline from the merge-base, compare it with HEAD, and expect empty output:

  ```bash
  mkdir -p "$SCRATCH/base" && git archive "$(git merge-base HEAD origin/staging)" src | tar -x -C "$SCRATCH/base"
  uvx vulture "$SCRATCH/base/src/adw" --min-confidence 60 | sed -E 's/^[^ ]*src\/adw/src\/adw/; s/:[0-9]+:/:/' | sort > "$SCRATCH/vb.txt"
  uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vh.txt"
  comm -13 "$SCRATCH/vb.txt" "$SCRATCH/vh.txt"
  ```

- [ ] Smoke test and screenshots, in one shell session, against this repo's real `.adw` config. A scratch `HOME` keeps the real `~/.adw` registry untouched. `$MAIN` is the main checkout, the only place that holds `.adw/`, which is gitignored. Order: hash, start the server, curl every tab, screenshot, hash again, then stop the server.

  ```bash
  ADW="$PWD/.venv/bin/adw"; EVID="$PWD/docs/artifacts/plans/02.5-make-dashboard-settings-read-only/evidence"
  MAIN=/Users/A1E6E98/Developer/Projects/adw/adw-final; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  mkdir -p "$SCRATCH/home" "$EVID" && cd "$MAIN"
  shasum .adw/project.yaml .adw/commands/*/config.yaml > "$SCRATCH/sha-before.txt"
  HOME="$SCRATCH/home" "$ADW" register --name adw        # registers the cwd; writes only $SCRATCH/home/.adw/projects.yaml
  HOME="$SCRATCH/home" "$ADW" dashboard web --no-browser --port 8765 & SERVER=$!
  trap 'kill "$SERVER" 2>/dev/null; rm -rf "$SCRATCH"' EXIT
  until curl -sf -o /dev/null http://127.0.0.1:8765/health; do kill -0 "$SERVER" || exit 1; sleep 0.5; done
  # 1. For each tab key, curl -s -o /dev/null -w '%{http_code}' three URLs and expect 200 from each:
  #      /settings?project=adw&tab=<key>                          (full page)
  #      /settings?project=adw&tab=<key>, with -H 'HX-Request: true'  (partial)
  #      /partials/settings-content?project=adw&tab=<key>
  # 2. Screenshot the Basics (tab=project), Task Manager (tab=task_manager) and Phases (tab=phases) tabs:
  #      "$CHROME" --headless --screenshot="$EVID/<tab>.png" --window-size=1280,1600 "http://127.0.0.1:8765/settings?project=adw&tab=<tab>"
  shasum .adw/project.yaml .adw/commands/*/config.yaml > "$SCRATCH/sha-after.txt"
  diff "$SCRATCH/sha-before.txt" "$SCRATCH/sha-after.txt" && echo byte-identical
  kill "$SERVER"; wait "$SERVER" 2>/dev/null
  ```

  Every status is 200, and `diff` prints nothing. View each screenshot: the values render, with no form controls or Save button. The screenshots live in `$EVID`, outside `$SCRATCH`, so the trap keeps them.
- [ ] LOC: record `find src -name '*.py' | xargs cat | wc -l` against 42,085 at baseline. Expect a drop of about 1,300.
- [ ] Write `docs/artifacts/plans/02.5-make-dashboard-settings-read-only/VALIDATION.md` with:
  - a table of each acceptance criterion and its evidence
  - the preflight output and the pytest summary and coverage lines
  - the POST route list, the `vulture` diff, and the LOC before and after
  - the smoke transcript: statuses, `shasum` before and after, `diff`
  - links to the screenshots
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] In `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`, tick phase 2.5's five `### Acceptance criteria`. No epic-level criterion is satisfied by this phase alone.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.5 --plan 02.5-make-dashboard-settings-read-only --status done`
- [ ] Epic 02's row in `docs/artifacts/epics/EPICS.md` already reads `In progress`. Leave it: phases 2.1–2.3 and 2.6–2.12 remain.
