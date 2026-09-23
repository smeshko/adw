# TASK-004: Read every include through one _read_under handler

Depends on: TASK-003
Suggested commit: `refactor(template): read every include through one handler`

## Goal

One single-pass directive expansion reads every `{{include:}}`, `{{shared:}}` and `{{file:}}` through `_read_under(root, rel, error_prefix)`. The traversal guard and the error codes are unchanged, included text is not rescanned, and the engine has no per-instance command or shared root.

## Files

- `src/adw/commands/template.py`:
  - Replace `FILE_PATTERN`, `INCLUDE_PATTERN` and `SHARED_PATTERN` with `DIRECTIVE_PATTERN = re.compile(r"\{\{(include|shared|file):([^}]+)\}\}")` and a prefix map `{"include": "INCLUDE", "shared": "SHARED", "file": "TEMPLATE"}`.
  - Add `_expand_directives(template, *, command_root, shared_root) -> str`:
    - one `DIRECTIVE_PATTERN.sub`, where the replacement picks the root: `command_root` for include, `shared_root` for shared, `self.project_root` for file
    - it returns `self._read_under(root, match.group(2).strip(), prefix)`
    - the replacement text is not rescanned, so an included file's own directives stay literal
  - Add `_read_under(root: Path | None, rel: str, error_prefix: str) -> str` (a `@staticmethod`). The body is the current handler logic once, with codes built from the prefix:
    - `root is None` raises `f"{error_prefix}_NO_ROOT"`. `INCLUDE_NO_COMMAND_ROOT` becomes `INCLUDE_NO_ROOT`, and `SHARED_NO_ROOT` is unchanged.
    - `_PATH_TRAVERSAL`: `resolve()` is not `is_relative_to(root.resolve())`, or `resolve()` raised `ValueError`
    - `_FILE_NOT_FOUND`, `_FILE_PERMISSION`, `_FILE_IS_DIRECTORY` and `_FILE_ENCODING`, as today
    - one suggestion per error that names the root path, instead of three hand-written variants
  - Delete `_process_includes`, `_process_shared_inclusions` and `_process_file_inclusions`, and the three `# type: ignore` comments they needed.
  - `__init__(self, project_root: Path | None = None)`: drop `command_root` and `shared_root` and their attributes.
  - `render(template, context, *, command_root=None, shared_root=None)`: `_expand_directives(...)`, then `_process_variables(...)`. Drop the "use parameter overrides, else instance attrs" block and its "ISS-017" note.
- `tests/unit/commands/test_template.py`:
  - Drop `FILE_PATTERN` from the import, and delete `test_file_pattern_matches_simple_path` and `test_file_pattern_matches_path_with_directory`. The inclusion tests cover the behaviour.
  - In `TestRenderWithRootParameters`, delete `test_render_parameters_override_instance_attributes`. Keep the two `accepts_*_parameter` tests.
  - Add `TestDirectives`:
    - `test_directive_path_traversal_raises[include|shared|file]`, using `{{include:../../etc/passwd}}`, `{{shared:../outside.txt}}` and `{{file:../outside.txt}}`, with `outside.txt` created one level above the root. It asserts `INCLUDE_PATH_TRAVERSAL`, `SHARED_PATH_TRAVERSAL` and `TEMPLATE_PATH_TRAVERSAL`.
    - `test_directive_missing_file_raises[include|shared|file]`: `*_FILE_NOT_FOUND`.
    - `test_directive_without_root_raises[include|shared]`: `INCLUDE_NO_ROOT` or `SHARED_NO_ROOT`.
    - `test_included_directives_not_expanded`: `{{include:a.txt}}`, where `a.txt` holds `{{file:secret.txt}}`, renders as `{{file:secret.txt}}` literally.
  - Fold the existing `test_path_traversal_blocked` and `test_path_traversal_absolute_blocked` into the parametrized test only if they become exact duplicates. Keep `test_path_traversal_absolute_blocked`, because an absolute path is a distinct case.

## Acceptance

- [ ] `test_included_directives_not_expanded` fails on the TASK-003 code, where the later `{{file:}}` pass expands the included text, and passes after the change.
- [ ] The parametrized traversal, missing-file and no-root tests pass. The traversal test is the epic's "`{{include:../../etc/passwd}}` still raises" evidence.
- [ ] `grep -n "_process_includes\|_process_shared_inclusions\|_process_file_inclusions\|INCLUDE_NO_COMMAND_ROOT\|self.command_root\|self.shared_root" src/adw/commands/template.py` returns nothing.
- [ ] `tests/integration/core/test_prompt_rendering.py` stays green, which shows the bundled prompts render as they did in TASK-003.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

Evidence: the RED and GREEN output of `test_included_directives_not_expanded`, the `-v` output of `TestDirectives`, the empty grep, and `wc -l src/adw/commands/template.py` before and after, for the epic's LOC criterion.

## Steps

### RED
- [ ] Add `TestDirectives` and run it. `test_included_directives_not_expanded` fails, and so do the `*_NO_ROOT` cases for `include` (the code is still `INCLUDE_NO_COMMAND_ROOT`).

### GREEN
- [ ] Add `DIRECTIVE_PATTERN`, `_expand_directives` and `_read_under`, switch `render()` to them, and delete the three handlers and the instance roots.
- [ ] Update the test imports and delete the tests listed under Files.
- [ ] Run `uv run pytest tests/unit/commands/test_template.py tests/unit/core/test_artifact_passing.py tests/integration/core/test_prompt_rendering.py tests/integration/test_document_phase.py -o addopts="" -q`.

### REFACTOR
- [ ] Keep `_read_under`'s `except` ladder in the current order: `PermissionError`, `IsADirectoryError`, `UnicodeDecodeError`.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- `bootstrap.py` constructs `TemplateEngine(project_root=...)` only. Only tests used the constructor's `command_root` and `shared_root`, so removing them breaks no production caller.
- `ValueError` from `resolve()` is still reachable, for example on an embedded NUL byte. Keep the `except ValueError` branch that maps it to `_PATH_TRAVERSAL`.
- mypy `--strict`: typing `_read_under`'s `root` as `Path | None` and returning early on `None` removes the need for the old `# type: ignore[operator]` and `# type: ignore[union-attr]` comments.
