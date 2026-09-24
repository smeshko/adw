# TASK-001: Delete the security package and its runtime wiring

Depends on: None
Suggested commit: `refactor(core): remove the inert security interceptor`

## Goal

`src/adw/security/`, `SecurityError` and everything that constructs or carries the interceptor are gone: bootstrap no longer builds one, `ClaudeCodeExecutor` no longer accepts one, and `adw run` no longer has `--allow-dangerous`.

## Files

- `src/adw/security/`: delete the package (6 modules).
- `src/adw/exceptions.py`: delete `class SecurityError` (L189–257) and the two blank lines before it.
- `src/adw/cli/bootstrap.py`:
  - Delete `from adw.security import SecurityInterceptor` (L47).
  - `create_orchestrator`: delete the `allow_dangerous` parameter (L174), its docstring entry (L195) and the "SecurityInterceptor for tool call validation" bullet (L188).
  - Delete the `# Create security components` block (L242–252).
  - Drop `security_interceptor=` and `allow_dangerous=` from the `ClaudeCodeExecutor(...)` call (L271–272).
- `src/adw/executors/claude_code.py`: delete the `TYPE_CHECKING` import of `SecurityInterceptor` (L24), the two keyword parameters (L52–53), their docstring entries (L60–63) and the two attribute assignments (L68–69).
- `src/adw/cli/app.py`: delete the `allow_dangerous` option (L192–196), the `--allow-dangerous` help example and its comment line (L233–234, plus the blank line that separates it from the next example), and `allow_dangerous=allow_dangerous,` in the `create_orchestrator` call (L394).
- `tests/unit/security/`: delete (6 files).
- `tests/unit/test_security_error.py`, `tests/unit/test_exceptions.py`: delete. The latter holds only `TestSecurityError`.
- `tests/unit/cli/test_bootstrap.py`: delete the six `mock_project_config.security = None` lines (L82, 155, 200, 238, 281, 317). Bootstrap no longer reads the field.
- `docs/CONDITIONAL_DOCS.md`: in the `docs/architecture/adrs/` entry, delete "When modifying dangerous command patterns" and "When implementing security interceptors" (L60–61). Keep "When working with secret redaction".

## Acceptance

- [ ] `grep -rn --exclude-dir=__pycache__ "SecurityInterceptor\|SecurityError\|allow_dangerous\|allow-dangerous\|adw\.security\|security_interceptor" src tests` returns only the wizard's `security_allow_dangerous` keys in `tests/unit/cli/wizard/test_security.py` and `test_summary.py`, which TASK-003 removes.
- [ ] `uv run adw run --allow-dangerous x` exits 2 with "No such option: --allow-dangerous".
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/cli tests/unit/executors tests/unit/core -o addopts=""` passes.

Evidence: the grep output, the CLI transcript, the preflight output and the pytest summary line.

## Steps

### RED
- [ ] Record the before state: `uv run adw run --help` lists `--allow-dangerous`. No failing test to write: the removed code has no replacement behaviour, and ADR-001 rules out help-text and import-smoke tests.

### GREEN
- [ ] `git rm -r src/adw/security tests/unit/security tests/unit/test_security_error.py tests/unit/test_exceptions.py`.
- [ ] Edit `exceptions.py`, `bootstrap.py`, `claude_code.py` and `app.py` as listed in Files.
- [ ] Delete the `security = None` lines from `test_bootstrap.py`.
- [ ] Edit `docs/CONDITIONAL_DOCS.md`.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Check `bootstrap.py`'s surrounding comments still read correctly after the block goes (the `# Set up live stream transport` comment follows the hook runner).
- [ ] Run `scripts/preflight.sh`.
- [ ] Run the grep and the CLI command from Acceptance, and keep the output for the PR.

## Notes

- Line numbers refer to `ad704a17`.
- `ProjectConfig.security` and `models/security.py` stay until TASK-002, so nothing else changes shape here.
