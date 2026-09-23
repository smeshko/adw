# TASK-006: Delete unused bundled BMAD copies

Depends on: None
Suggested commit: `chore(defaults): delete bundled BMAD files no prompt includes`

## Goal

Remove the three bundled BMAD files that no prompt includes and no code reads (D6).

## Files

- Delete `src/adw/defaults/commands/build/dev-story/checklist.md`.
- Delete `src/adw/defaults/commands/plan/create-story/template.md`.
- Delete `src/adw/defaults/commands/plan/create-story/validation-prompt.md`.

## Acceptance

- [ ] `grep -rn "{{include:[^}]*\(checklist\|template\|validation-prompt\)\.md" src/adw/defaults` returns nothing, both before and after the deletion.
- [ ] `grep -rn "checklist.md\|template.md\|validation-prompt" src tests` finds exactly two lines, as it does today: `plan/create-story/workflow.yaml:18` (`template: "{installed_path}/template.md"`) and `build/dev-story/workflow.yaml:13` (`validation: "{installed_path}/checklist.md"`). `installed_path` points under `{project-root}/_bmad/…` in target projects, so neither line refers to the bundled copies.
- [ ] The parametrized bundled-phase test from phase 1.4 still passes, and so does the template-render test for plan and build: `uv run pytest tests/unit/commands -o addopts=""`.
- [ ] `adw validate` in a scratch repo still reports `OK` for all five phases.

Evidence:
- both grep outputs
- the pytest summary line
- the `adw validate` transcript

## Steps

- [ ] Run both greps and record the output.
- [ ] `git rm` the three files. Stage explicitly, by path.
- [ ] Run `uv run pytest tests/unit/commands tests/integration/test_document_phase.py -o addopts=""`.
- [ ] In a scratch directory (`cd "$(mktemp -d)" && git init -q`), run `adw init --no-interactive` and then `adw validate`, and record the transcript. Never run it from the checkout.

## Notes

- Leave the `workflow.yaml` lines alone. Rewriting the BMAD workflow prompts is out of scope for Epic 01.
