# TASK-004: Trim package re-export lists to what src imports

Depends on: None
Suggested commit: `refactor: trim package re-exports to what src imports`

## Goal

The `hooks`, `executors`, `commands`, `logging`, `cli` and `config` package `__init__.py` files re-export only what `src` imports through the package path, plus `adw.config.ConfigLoader`.

## Files

- `src/adw/hooks/__init__.py`, `src/adw/executors/__init__.py`, `src/adw/commands/__init__.py` — keep a short module docstring; no imports, no `__all__`.
- `src/adw/logging/__init__.py` — keep `LogManager`, `LogManagerHandler` and `create_redactor_from_config` (plus the `configure_redactor` and `Redactor` imports that function needs); delete `get_logger`, `reset_logger`, `_default_logger` and the docstring's Quick Start examples that use them; `__all__` lists the three kept names.
- `src/adw/cli/__init__.py` — import and export `app` only.
- `src/adw/config/__init__.py` — import and export `ConfigLoader` only; the docstring says why it stays (external hook scripts).
- `tests/unit/logging/test_package.py` — delete `TestGetLogger` and `TestResetLogger`; import `Redactor` from `adw.logging.redactor`; update the `REDUCED:` header comment.
- `tests/unit/executors/test_protocol.py` — `from adw.executors.base import LLMExecutor`.
- `tests/unit/commands/test_template.py` (2 imports), `test_resolver.py`, `test_resolver_errors.py`, `test_directory_validation.py`, `test_bundled_commands.py`, `tests/unit/core/test_ship_extension.py` — import `CommandResolver` from `adw.commands.resolver` and `TemplateEngine` from `adw.commands.template`.

## Acceptance

- [ ] `grep -rn "from adw\.\(hooks\|executors\|commands\|logging\|cli\|config\) import" src tests` lists only the `cli/bootstrap.py` logging import, `__main__.py`'s `app`, and `from adw.cli import wizard`.
- [ ] `adw --help` output matches the baseline, and `python -m adw --version` still works.
- [ ] The full suite passes.

Evidence: the grep, `diff` of `adw --help` against `before-help.txt` (empty), and the full-suite summary line.

## Steps

### RED
- [ ] None: the removed names have no `src` importer. The tests move to the defining modules first, so they keep passing.

### GREEN
- [ ] Point the test imports at the defining modules.
- [ ] Trim the six `__init__.py` files and delete the two logger tests.

### REFACTOR
- [ ] `scripts/preflight.sh`, then `uv run pytest`. A circular import that the old eager re-exports masked shows up here.
- [ ] Capture `adw --help` from an empty scratch directory and diff it against the baseline.
