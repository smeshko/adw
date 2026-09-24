# TASK-001: Delete the webhook package and the adw webhook command group

Depends on: None
Suggested commit: `refactor(cli): delete the webhook server and its command group`

## Goal

`src/adw/webhook/`, `adw webhook` and `LogCategory.WEBHOOK` are gone. This also removes bugs B6 and B7.

## Files

- `src/adw/webhook/`: delete it all with `git rm -r`.
- `src/adw/cli/webhook.py`: delete it.
- `src/adw/cli/app.py`:
  - drop `from adw.cli.webhook import webhook_app` (`:27`)
  - drop the `# Register the webhook subapp (Story 13.1)` comment and `app.add_typer(webhook_app, name="webhook")` (`:512-513`)
- `src/adw/models/logging.py`: drop the `WEBHOOK` docstring bullet (`:87`) and the enum member (`:96`).
- `src/adw/logging/handler.py:_infer_category`: drop the `webhook` docstring bullet (`:116`) and the `elif "webhook" in name_lower` branch with its comment (`:129-132`).
- `src/adw/logging/live_stream.py:CATEGORY_COLORS`: drop `LogCategory.WEBHOOK: "cyan"` (`:61`).
- `tests/unit/webhook/`: delete it all with `git rm -r`.

## Acceptance

- [ ] `uv run adw --help` lists no `webhook` group.
- [ ] `uv run adw webhook --help` exits 2 with "No such command 'webhook'".
- [ ] `grep -rn "adw\.webhook\|webhook_app\|LogCategory.WEBHOOK" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/cli tests/unit/logging tests/unit/models -o addopts=""` passes.
- [ ] `scripts/preflight.sh` passes.

Evidence:
- the `adw --help` command list and the `adw webhook --help` error, both before and after
- the grep
- the pytest tail

## Steps

### RED
- [ ] Capture the "before" state: `uv run adw --help` shows `webhook`, and `uv run adw webhook --help` exits 0. There's no new test: ADR-001 leaves help-text tests unwritten, so the transcripts are the evidence.

### GREEN
- [ ] `git rm -r src/adw/webhook tests/unit/webhook src/adw/cli/webhook.py`.
- [ ] Remove the `app.py` import and registration.
- [ ] Remove `LogCategory.WEBHOOK` and its two consumers.
- [ ] Run the partial suite above. Then capture the "after" transcripts.

### REFACTOR
- [ ] `scripts/preflight.sh` passes: ruff finds no unused imports, and mypy `--strict` is clean.

## Notes

- `models/webhook.py`, `server/` and `RunTrigger` still exist after this task. TASK-003, TASK-004 and TASK-005 remove them, now that their last webhook importers are gone.
- After this task, a logger named `adw.webhook.*` would fall into the `hook` branch. No such module exists any more, so no test covers it.
