# TASK-006: Remove webhook references from the docs

Depends on: TASK-001, TASK-004, TASK-005
Suggested commit: `docs: drop webhook references from the new-run docs`

## Goal

No doc outside `docs/artifacts/` describes the webhook module or `WebhookRunTrigger`.

## Files

- `docs/features/new-run-modal-form-submission.md`:
  - `:8` (Overview): replace "extracts core run-triggering logic from the webhook module into a shared `core/run_trigger.py`" with "puts the run-triggering logic in `core/run_trigger.py`".
  - `:12`: replace "Shared run-launching logic extracted from `webhook/runner.py`, usable by both dashboard and webhook without cross-importing" with "Run-launching logic behind the dashboard's New Run".
  - `:29`: delete the `src/adw/webhook/runner.py` bullet.
  - `:39` (Core Extraction Pattern): rewrite it as "Run-launching logic lives in `core/`; the dashboard reaches it through the `get_run_trigger` dependency, so tests can inject a mock."
  - `:101`: delete the `WebhookRunTrigger` note.
- `docs/CONDITIONAL_DOCS.md:119`: delete "When extracting shared logic from webhook module to core for dashboard use".

## Acceptance

- [ ] `grep -rni webhook docs --exclude-dir=artifacts` returns nothing.
- [ ] Both files still read coherently: the Overview and Key Patterns sections in `new-run-modal-form-submission.md` keep their other content.

Evidence: the grep output and `git diff --stat docs/features docs/CONDITIONAL_DOCS.md`.

## Steps

- [ ] Apply the five edits to `new-run-modal-form-submission.md`.
- [ ] Delete the condition line in `CONDITIONAL_DOCS.md`.
- [ ] Run the grep and confirm it is empty.
- [ ] Stage the two files explicitly and commit.
