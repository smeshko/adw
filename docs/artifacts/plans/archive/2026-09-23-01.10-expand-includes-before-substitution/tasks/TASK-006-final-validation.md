# TASK-006: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.10-expand-includes-before-substitution`

## Goal

Confirm the plan is fully implemented and production-ready. The evidence goes in `VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] Project analyzer/linter passes with no issues: `scripts/preflight.sh`
- [ ] Full test suite passes: `uv run pytest` green with coverage ≥ 80%. Record the summary line and the coverage total.
- [ ] Module/import boundaries respected: `grep -rn "validate_artifact_references\|ARTIFACT_REF_PATTERN\|UNKNOWN_VARIABLE\|strict=" src/adw/commands src/adw/core/phase_runner.py` is empty
- [ ] Manual smoke test performed: the scratch-repo recipe below, for both before and after
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Scratch-repo prompt capture (before and after)

Everything runs under a scratch `HOME` in the session scratchpad, so neither the checkout nor the real `~/.adw` is touched.

1. Set up:
   - `S=$SCRATCHPAD/p110` (the session scratchpad directory), then `mkdir -p $S/{bin,home,repo,prompts,before}`.
   - `git archive be1d5bf8 | tar -x -C $S/before` gives a pre-phase copy of the code. It has no `.git`, and nothing touches the repo's worktree list.
2. Write a fake `$S/bin/claude` (`chmod +x`):
   - It writes its last argument (the prompt) to `$PROMPT_DIR/prompt-$$.md` (macOS `date` has no `%N`).
   - It prints `{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}` and then `{"type":"result","subtype":"success","is_error":false,"result":"ok","usage":{"input_tokens":1,"output_tokens":1},"total_cost_usd":0}`.
   - It exits 0.

   Also write a fake `$S/bin/gh` that exits 1, so the document step's `create_pr` fails harmlessly (the failure is caught and logged).
3. Scratch repo:
   - `git init -b main`
   - `.adw/project.yaml` with `name: scratch`, `language: python`, `test_command: "uv run pytest"`, `worktree: {enabled: false}`
   - `.adw/commands/validate/config.yaml` with `lint_command: "ruff check ."`
   - `.adw/commands/document/config.yaml` with one `doc_mappings` entry
   - `.gitignore` with `.adw/runs/`
   - commit
4. Source run: copy a real run with a non-empty build diff from the main checkout's `.adw/runs/` (for example `01KF636397JZC18V4K8MGS59G7` or `01KH72J5HMVVJGQBPWJS26R337`) into `$S/repo/.adw/runs/`, and set `SRC` to its id.
   - Fallback, if `--from-run` cannot load an older `context.json`: produce a source run in the scratch repo with the fake `claude`. It appends a line to a tracked file when the prompt starts with `# Build Phase`, so `diff.txt` is non-empty.
5. For `CODE` in `$S/before` and this checkout, run from `$S/repo` with `HOME=$S/home PATH=$S/bin:$PATH` and `PROMPT_DIR` set to `$S/prompts/before-document`, `after-validate` and so on plus the `GIT_AUTHOR_*` and `GIT_COMMITTER_*` variables:
   - `uv run --project $CODE adw run --phase document --from-run $SRC`
   - `uv run --project $CODE adw run --phase validate --from-run $SRC`
6. Compare the captured prompts:
   - `grep -c "{{artifacts.build.diff}}\|{{doc_mappings}}\|{{test_command}}\|{{lint_command}}"` on each
   - check that the source diff's first line appears after `### Instructions` in `after-document`
   - check that `uv run pytest` and `ruff check .` appear in `after-validate`
   - put a `diff -u` excerpt of the instructions section, before against after, for both phases in `VALIDATION.md`

### Evidence to collect in `VALIDATION.md`

- An acceptance-criteria table, with evidence per row.
- The B5 regression tests: the RED output from TASK-003 (`test_document_prompt_fills_included_build_diff`, `test_validate_prompt_fills_included_commands`) and the GREEN output.
- The `test_llm_facing_placeholders_survive[*]` and `TestDirectives` `-v` output.
- The scratch-repo transcript and the before/after prompt excerpts from above.
- `find src -name '*.py' | xargs wc -l | tail -1` before (`be1d5bf8`) and after, for the epic's LOC criterion.

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick phase 1.10's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`, each with a pointer to its evidence.
- [ ] Epic-level criteria: add `phase 1.10: B5 test_document_prompt_fills_included_build_diff, test_validate_prompt_fills_included_commands` to the regression-test line, and this phase's LOC delta to the LOC line, in the style of the phase 1.7 and 1.8 entries.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.10 --plan 01.10-expand-includes-before-substitution --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` (`In progress` after the first phase merges; `Done` when this is the last phase — then tick the remaining epic-level criteria and note any newly-unblocked epics). Epic 01 stays `In progress` while phases 1.3, 1.5 and 1.9 are open.
