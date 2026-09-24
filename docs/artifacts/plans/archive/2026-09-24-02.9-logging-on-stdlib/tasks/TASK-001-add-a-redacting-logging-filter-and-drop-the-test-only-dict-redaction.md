# TASK-001: Add a redacting logging filter and drop the test-only dict redaction

Depends on: None
Suggested commit: `feat(logging): add a redacting logging filter and drop dict redaction`

## Goal

A `RedactingFilter` rewrites any log record's text through a `Redactor`, and the dict redaction that only tests use is gone.

## Files

- `src/adw/logging/redactor.py`:
  - add `import logging` and `class RedactingFilter(logging.Filter)`, built as `RedactingFilter(redactor: Redactor)`
  - `filter(record) -> bool`:
    - set `record.msg = self._redactor.redact(record.getMessage())` and `record.args = None`, so `%`-args are formatted once and then redacted
    - if `record.exc_info` is set and `record.exc_text` is empty, fill `record.exc_text` with `logging.Formatter().formatException(record.exc_info)`
    - if `record.exc_text` is set, redact it. A formatter reuses a set `exc_text`, so the traceback prints redacted.
    - apply the same to `record.stack_info` when set
    - return `True`
  - delete `redact_dict` and `_redact_list`, and the `from typing import Any` that only they need
  - update the module and class docstrings: drop "(for JSON logs)" and "Deep dictionary redaction", and name `RedactingFilter` as the way log records get redacted
- `tests/unit/logging/test_redactor.py`:
  - delete `TestRedactDict`
  - add `TestRedactingFilter`, each test pushing a record through a `logging.Handler` subclass that stores `handler.format(record)`:
    - `test_redacts_formatted_message`: `logger.info("key=%s", "sk-" + "a" * 24)` → stored text has `[REDACTED]` and no `sk-aaaa`
    - `test_redacts_exception_text`: `logger.exception("failed")` inside `except` of `raise ValueError("token=abcdefgh1234")` → stored text has `[REDACTED]` and no `abcdefgh1234`
    - `test_is_idempotent`: filtering the same record twice leaves one `[REDACTED]` and the same text

## Acceptance

- [ ] A record whose `%`-args carry a secret is emitted with `[REDACTED]` in place of the secret.
- [ ] A logged exception's traceback text is redacted.
- [ ] Running the filter twice on one record changes nothing the second time.
- [ ] `grep -rn "redact_dict\|_redact_list" src tests` prints nothing.
- [ ] `uv run pytest tests/unit/logging -o addopts=""` and `scripts/preflight.sh` pass.

Evidence: the RED run (the new tests fail on `ImportError: cannot import name 'RedactingFilter'`), the GREEN pytest tail, the empty grep, and the preflight tail.

## Steps

### RED
- [ ] Add `TestRedactingFilter` and delete `TestRedactDict`. Run `tests/unit/logging/test_redactor.py`: the new tests fail on the import.

### GREEN
- [ ] Add `RedactingFilter`, delete `redact_dict`/`_redact_list`, and update the docstrings. Run the file: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `record.args = None` matters: without it the next handler's `getMessage()` would format the already-formatted message again, and a `%` in the redacted text would raise.
- The tests use their own logger name (e.g. `adw.test.redacting_filter`) and remove their handler in a `finally`, so no handler leaks into other tests before TASK-002's conftest fixture exists.
