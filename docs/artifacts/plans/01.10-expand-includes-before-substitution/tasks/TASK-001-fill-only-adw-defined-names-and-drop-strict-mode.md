# TASK-001: Fill only ADW-defined names and drop strict mode

Depends on: None
Suggested commit: `refactor(template): fill only ADW-defined names and drop strict mode`

## Goal

`render()` fills a placeholder only when its top-level name is a key of the variables it receives. Every other placeholder passes through verbatim, and there is no strict mode and no duplicate artifact validator.

## Files

- `src/adw/commands/template.py`:
  - `_process_variables(template, context)` (drop `strict`). For each `VARIABLE_PATTERN` match:
    - `top = var_path.split(".", 1)[0]`
    - if `top not in context`, return `match.group(0)` and log nothing
    - otherwise `_resolve_variable`. On `KeyError`, log one warning, `"Template variable not found, left as-is: {{%s}}"` with `extra={"variable": var_path}`, and return `match.group(0)`
    - `None` becomes `""`, and anything else goes through `str()` (unchanged)
  - `render(template, context, *, command_root=None, shared_root=None)`: drop `strict`, and update the docstring.
  - Delete `validate_artifact_references`, `ARTIFACT_REF_PATTERN`, the `UNKNOWN_VARIABLE` `ConfigError`, and `"validate_artifact_references"` from `__all__`.
  - Module and class docstrings: describe the fill rule. Leave the render order alone; TASK-003 changes it.
- `src/adw/core/phase_runner.py`, `_load_and_render_prompt`:
  - delete the `validate_artifact_references(...)` call and its "ISS-017" comment
  - drop `strict=False` from `render()`
  - remove the import
  - fix the docstring's `Raises:` entry that mentions strict mode
- `tests/unit/commands/test_template.py`:
  - Delete `TestArtifactRefPattern` and `TestValidateArtifactReferences`, and drop `ARTIFACT_REF_PATTERN` from the import on line 8.
  - Replace `TestStrictVsLenientMode` with `TestFillRule`:
    - `test_unknown_top_level_name_passes_through_silently`: `{{story_key}}` with `{}` stays verbatim, and `caplog` has no warning.
    - `test_known_name_with_missing_path_passes_through_and_warns`: `{{artifacts.build.diff}}` with `{"artifacts": {}}` stays verbatim and logs one warning that names the path.
    - `test_known_and_unknown_names_mixed`: `{{known}} and {{unknown}}` becomes `value and {{unknown}}`.
    - `test_top_level_name_is_the_first_segment`: `{{task_validated}}` with `{"task": {...}}` stays verbatim, because `task_validated` is not `task`.
  - `test_object_attribute_access_missing_raises` becomes `..._passes_through`: the placeholder stays, and nothing raises.
  - Remove `strict=` from every remaining `render()` call. Calls that relied on the strict default with only known names keep passing unchanged.
- `tests/unit/core/test_artifact_passing.py`, class `TestStrictModeForMissingArtifacts` (≈ line 379):
  - delete the three strict-mode tests
  - keep `test_lenient_mode_returns_placeholder_for_missing` and `test_empty_artifacts_map_handled_gracefully` without `strict=False`
  - rename the class to `TestMissingArtifacts`
  - remove `strict=` from the other calls in the file

## Acceptance

- [ ] The four `TestFillRule` tests pass. `test_unknown_top_level_name_passes_through_silently` fails on the pre-change code, which logs "Unknown template variable left as-is".
- [ ] `grep -rn "validate_artifact_references\|ARTIFACT_REF_PATTERN\|UNKNOWN_VARIABLE\|strict=" src/adw/commands src/adw/core/phase_runner.py tests/unit/commands/test_template.py tests/unit/core/test_artifact_passing.py` returns nothing.
- [ ] The affected test files pass, and `scripts/preflight.sh` passes.

Evidence: the RED output of `test_unknown_top_level_name_passes_through_silently` (a warning is present), the GREEN output of `uv run pytest tests/unit/commands/test_template.py tests/unit/core/test_artifact_passing.py tests/unit/core/test_phase_runner.py tests/integration/test_document_phase.py -o addopts="" -q`, and the empty grep.

## Steps

### RED
- [ ] Add `TestFillRule` and run it. The silent-pass-through test fails, because a warning is logged. The first-segment test fails too if the rule is keyed on a prefix match.
- [ ] Delete and adjust the strict-mode and validator tests listed under Files.

### GREEN
- [ ] Rewrite `_process_variables` and `render()`, and delete the validator, the pattern and the error.
- [ ] Remove the call site and import in `phase_runner.py`.
- [ ] Run the affected test files.

### REFACTOR
- [ ] Update the module, class and `render()` docstrings for the fill rule, and drop the "ISS-017" notes on the deleted code.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- The render order is unchanged in this task. Variables are still substituted before includes, so included BMAD placeholders are not seen yet. The new silence only matters from TASK-003 on.
- `_resolve_wildcard` already returns `""` for a missing path, so `{{artifacts.validate.*}}` with no validate artifacts still renders empty and does not warn. Keep that.
- `context` in `PhaseRunner`'s variables is the `RunContext` model, so `{{context.nonexistent}}` resolves through `getattr` and raises `KeyError`, which becomes a warning and pass-through. Keep the `hasattr` path.
