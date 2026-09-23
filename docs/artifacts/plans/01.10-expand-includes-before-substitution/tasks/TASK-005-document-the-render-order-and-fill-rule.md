# TASK-005: Document the render order and fill rule

Depends on: TASK-004
Suggested commit: `docs: document the template render order and fill rule`

## Goal

`docs/templates.md` and the PhaseRunner deep dive describe the rendering that TASK-001 to TASK-004 shipped. Epic 05 relies on these docs: its prompts are written against "includes first, only ADW names filled."

## Files

- `docs/templates.md`: add these sections before `## Task Variables`, and leave that section as it is:
  - **Template syntax**: a table of the four forms.
    - `{{name.path}}` and `{{name.*}}` are variables.
    - `{{include:rel}}` resolves under the command's own directory.
    - `{{shared:rel}}` resolves under the commands directory, which is the command directory's parent.
    - `{{file:rel}}` resolves under the project root.
    - Directive paths must stay inside their root. `..` and absolute paths raise `INCLUDE_PATH_TRAVERSAL`, `SHARED_PATH_TRAVERSAL` or `TEMPLATE_PATH_TRAVERSAL`.
  - **Render order**:
    1. Every directive is replaced with its file's contents, in one pass. Included text is not scanned for further directives, so there is no nesting.
    2. Variables are filled in the combined text, so ADW variables work inside included files.
    3. Variable values are inserted literally and never expanded. A value that contains `{{file:…}}` stays text.
  - **Which placeholders ADW fills**:
    - The top-level names ADW defines, with their source: `artifacts`, `inputs`, `task`, `context`, `run_id`, `phase`, `feature`, `feature_description`, `worktree_path`, `project_config`, `pre_hook_output`, `schema`, `ship_config`, `doc_mappings`, `build_command`, `test_command`, `lint_command` (validate), `version_bump_command` and `publish_command` (ship, with a project ship config), plus any keys a pre-hook writes to `pre_hook_vars.json`.
    - A placeholder with any other top-level name is left verbatim for the LLM, and nothing is logged. This is how the BMAD workflow files' `{{story_key}}`, `{{analysis.*}}` and similar placeholders reach Claude.
    - A known name whose path does not resolve is left verbatim and logged as a warning.
    - `None` renders as an empty string.
    - Only lowercase dotted names are variables. `{{#x}}`, `{{x | default: …}}` and `{{A/B}}` are never touched.
  - Note that a `{{file:}}`-included project file has ADW names filled too.
- `docs/architecture/deep-dive/phase-runner.md`:
  - **Phase Execution Flow**: replace the `Validate artifact references` and `Render with variables` lines with `Render: expand includes, then fill ADW variables (see docs/templates.md)`.
  - **Template Variables**: add rows for `inputs`, `task`, `run_id`, `phase`, `feature`, `project_config`, `ship_config`, `doc_mappings`, the `*_command` variables and pre-hook variables, and link to `../../templates.md` for the fill rule.
  - **Error Handling**: replace the stale `ConfigError | Fail if strict_artifacts=True and artifact missing` row with `ConfigError | Include directive fails: path traversal, missing file, or missing root`, and add `Missing artifact | Placeholder left verbatim, warning logged`.

## Acceptance

- [ ] `docs/templates.md` contains the three new sections, and each states the rules above.
- [ ] `grep -n "strict_artifacts\|Validate artifact references" docs/architecture/deep-dive/phase-runner.md` returns nothing.
- [ ] Every relative link added in either doc resolves to an existing file.

Evidence: the `git diff --stat` and the empty grep, plus a link check, for example, with `DOC` set to each doc: `for l in $(grep -o '](\.\.[^)]*)' "$DOC" | tr -d '()]'); do test -e "$(dirname "$DOC")/$l" || echo MISSING $l; done` with no output.

## Steps

- [ ] Run `git diff` on both docs first (expect nothing).
- [ ] Write the `docs/templates.md` sections. Check every rule against `template.py` as it stands after TASK-004, not against this plan.
- [ ] Update the three places in the deep dive.
- [ ] Run the grep and the link check.

## Notes

- Keep `## Task Variables` and its examples unchanged; phase 1.10 does not touch `build_task_context`.
- Do not document `strict`, `validate_artifact_references` or the per-instance roots; they no longer exist.
