# TASK-004: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 02.1-remove-the-security-package`

## Goal

Confirm the plan is fully implemented and production-ready, and produce the evidence the epic's Validation section asks for.

## Steps

Set `WORKTREE` to this worktree's root first. Every `adw` command below runs as `uv run --project "$WORKTREE" adw …`: the `adw` on `PATH` is installed from another checkout and would validate the old code.

- [ ] TASK-001 to TASK-003 are ticked in `PLAN.md`. Tick TASK-004 only after every step below has produced its evidence.
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] `uv run pytest` passes with coverage ≥ 80%; record the summary line and compare it with the baseline at `ad704a17`: 3,581 passed, 5 skipped, coverage 85.34%
- [ ] The plan's grep returns nothing: `grep -rn --exclude-dir=__pycache__ "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|allow-dangerous\|security_interceptor\|adw\.security" src tests`
- [ ] The epic's literal command returns nothing too. First clear the bytecode that `git rm` leaves behind: `find src tests -type d -name __pycache__ -prune -exec rm -rf {} +`. Then run `grep -rn "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|adw.security" src tests` exactly as the epic's phase 2.1 criterion writes it, and record that output as the evidence for ticking it.
- [ ] Vulture: `uvx vulture src/adw --min-confidence 60`, line numbers stripped and sorted, diffed against the same output at the merge-base, shows no new entry
- [ ] `uv run --project "$WORKTREE" adw validate` in a scratch project (`git init` in a temp dir, `.adw/project.yaml` with `name: scratch-sec`, `language` and a `security:` section with `blocked_patterns` and `blocked_env_files`) reports the config valid. Save the transcript.
- [ ] `adw init --wizard` in a scratch git repo, fed its answers on stdin, completes with no security prompt and no Security summary line: `yes "" | head -60 | NO_COLOR=1 COLUMNS=100 uv run --project "$WORKTREE" adw init --wizard`, run from the scratch repo with `HOME` set to a scratch dir. Save the transcript next to the before transcript, which shows `Step 8/10: Security Settings` and `Security: Default` (captured during planning; piped stdin drives every prompt).
- [ ] Dashboard: start `uv run --project "$WORKTREE" adw dashboard web` with a scratch `HOME` whose registry holds the scratch project (the one with the `security:` section), open `/settings?project=scratch-sec`, and screenshot it. The tab list has no Security tab and Basics has no `security` row.
- [ ] `uv run --project "$WORKTREE" adw run --allow-dangerous x` exits 2 with "No such option". Save the transcript.
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced — no criterion ticked on "the code looks right"
- [ ] Write `VALIDATION.md` in the plan dir with the evidence, and save the screenshot under `evidence/`

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick this phase's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`. No epic-level criterion is fully met by this phase alone (`src/adw` still has `webhook/`, `server/`, `validation/` and `utils/`).
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.1 --plan 2026-09-24-02.1-remove-the-security-package --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` if it isn't already `In progress`
