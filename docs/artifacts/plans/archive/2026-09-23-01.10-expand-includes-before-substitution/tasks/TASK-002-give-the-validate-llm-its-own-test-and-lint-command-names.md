# TASK-002: Give the validate LLM its own test and lint command names

Depends on: None
Suggested commit: `fix(prompts): keep validate auto-detect working once commands are filled`

## Goal

Validate's instructions read ADW's `{{test_command}}` and `{{lint_command}}` once each, and the LLM keeps its own working variables, `test_cmd` and `lint_cmd`. After TASK-003 fills these names, an unset command (rendered as `""`) still triggers auto-detect instead of producing `Execute: `.

## Files

- `src/adw/defaults/commands/validate/code-review-loop/instructions.xml`:
  - Lines 95–113, the `detect-test-command` and `detect-lint-command` steps, become:
    ```xml
          <step name="detect-test-command">
            <critical>Use the configured test command; auto-detect only when none is configured</critical>
            <action>Provided test command: `{{test_command}}` (empty = not configured)</action>
            <action>If the provided test command is not empty, set test_cmd to it.
            Otherwise, try to the best of your abilities to extract the test command based on the project structure and framework, and set test_cmd to it.</action>
            <check if="no test command provided or detected">
              <action>Set test_cmd = null</action>
              <note>Will skip test phase if no test framework detected</note>
            </check>
          </step>

          <step name="detect-lint-command">
            <action>Provided lint command: `{{lint_command}}` (empty = not configured)</action>
            <action>If the provided lint command is not empty, set lint_cmd to it. Otherwise, set lint_cmd = null.</action>
            <note>Will skip lint phase if no linter configured</note>
          </step>
    ```
    Lint keeps today's semantics: provided, or null, with no detection.
  - Line 122: `<check if="{{lint_command}} is null">` becomes `<check if="lint_cmd is null">`.
  - Lines 137 and 160: `Execute: {{lint_command}}` becomes `Execute: lint_cmd`.
  - Line 186: `<check if="{{test_command}} is null">` becomes `<check if="test_cmd is null">`.
  - Lines 201 and 224: `Execute: {{test_command}}` becomes `Execute: test_cmd`.
- `src/adw/defaults/commands/ship/instructions.xml`, lines 168–170, the `extract-ship-config` substep:
  ```
            - Version bump command: `{{version_bump_command}}` (empty = not configured)
            - Build command: `{{build_command}}` (empty = not configured)
            - Publish command: `{{publish_command}}` (empty = not configured)
  ```
  Leave the `{{… | default: "not configured"}}` lines as they are. They never match `VARIABLE_PATTERN`, and the LLM fills them.

## Acceptance

- [ ] `grep -c "{{test_command}}" src/adw/defaults/commands/validate/code-review-loop/instructions.xml` prints `1`, and the same grep for `{{lint_command}}` prints `1`.
- [ ] `grep -n "test_cmd\|lint_cmd" …/validate/code-review-loop/instructions.xml` shows the detect steps, the two null checks and the four `Execute:` actions.
- [ ] `tests/unit/commands/test_bundled_commands.py::test_bundled_phase_files_are_well_formed` passes for `validate` and `ship`.
- [ ] `scripts/preflight.sh` passes.

Evidence: the two grep outputs and the `test_bundled_commands.py` run. The rendered-prompt behaviour is demonstrated in TASK-003 by `test_validate_prompt_fills_included_commands` and `test_validate_prompt_without_commands_keeps_auto_detect`.

## Steps

- [ ] Run `git diff` on both files first (expect nothing).
- [ ] Edit the validate steps and the six references as listed.
- [ ] Edit ship lines 168–170.
- [ ] Run the greps and `uv run pytest tests/unit/commands/test_bundled_commands.py -o addopts="" -q`.
- [ ] Run `scripts/preflight.sh`.

## Notes

- This lands before the reorder on purpose. At this commit, the included placeholders are still not filled, so the LLM sees `Provided test command: \`{{test_command}}\``, which reads like today's unfilled placeholder. No commit renders an empty `Execute:`.
- `version_bump_command` and `publish_command` are keys of the variables only when the project has `.adw/commands/ship/config.yaml` (`test_flat_variables_absent_when_no_ship_config`). Without one, those two placeholders stay literal after TASK-003, the same as today. `build_command` is always a key, so it renders `""` when unset.
- Keep the edit to these lines. Everything else in the BMAD-derived prompts belongs to Epic 05.
