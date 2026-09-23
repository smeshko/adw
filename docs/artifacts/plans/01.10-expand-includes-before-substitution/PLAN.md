# Plan: Expand includes before substitution

Status: draft
Branch: feature/adw-16
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.10 — Expand includes before substitution
Linear: ADW-16
Created: 2026-09-23

## Goal

ADW fills its own variables inside the files a prompt includes, through one include handler. Every other `{{…}}` placeholder reaches the LLM untouched (B5).

## Scope

- `src/adw/commands/template.py`:
  - **Render order.** `render()` expands `{{include:}}`, `{{shared:}}` and `{{file:}}` first, then substitutes variables.
  - **Fill rule.** A `{{name.path}}` placeholder is filled only when `name`, its top-level segment, is a key of the variables that `render()` receives. Those keys are what ADW defines: `artifacts`, `inputs`, `task`, `context`, `run_id`, `phase`, `feature`, `feature_description`, `worktree_path`, `project_config`, `pre_hook_output`, `schema`, `ship_config`, `doc_mappings`, the `*_command` variables, and any pre-hook variables.
    - A placeholder with any other top-level name passes through verbatim and is not logged.
    - A known top-level name whose path does not resolve, such as `{{artifacts.build.diff}}` before build has run, passes through verbatim and logs one warning.
    - A `None` value renders as `""`, which is unchanged.
  - **One include pass.** One regex, `\{\{(include|shared|file):([^}]+)\}\}`, replaced in a single pass through one `_read_under(root, rel, error_prefix)`. That function keeps the path-traversal guard and the existing `INCLUDE_*`, `SHARED_*` and `TEMPLATE_*` error codes. Included text is not rescanned for directives, and variable values are never expanded.
  - **Deletions:**
    - `validate_artifact_references` and `ARTIFACT_REF_PATTERN`
    - the `strict` parameter and the `UNKNOWN_VARIABLE` error
    - the `command_root` and `shared_root` constructor arguments and instance attributes. `render()`'s per-call arguments remain.
- `src/adw/core/phase_runner.py`: `_load_and_render_prompt` drops the `validate_artifact_references` call and `strict=False`.
- Bundled prompts, keeping validate's auto-detect working now that an unset command renders as `""`:
  - `validate/code-review-loop/instructions.xml` shows `{{test_command}}` and `{{lint_command}}` once each, as "Provided … command". The LLM then works with brace-less `test_cmd` and `lint_cmd`.
  - `ship/instructions.xml` lines 168–170 get "(empty = not configured)" wording.
- Tests:
  - rewrite the template unit tests for the new rules
  - add a new `tests/integration/core/test_prompt_rendering.py` that renders the bundled phases through the real `PhaseRunner` render path (the B5 regression tests)
- Docs: `docs/templates.md` gets the syntax, the render order and the fill rule. `docs/architecture/deep-dive/phase-runner.md` is updated to match.

## Out of Scope

- Any other change to the BMAD-derived prompt text. For example, the plan instructions now inline `{{feature_description}}` four more times, and `{{run_id}}` twice. Epic 05 rewrites these prompts.
- Saving rendered prompts to disk. The dashboard reads a `{phase}_prompt.txt` that nothing writes, and this phase leaves it that way.
- Resolving `{{file:}}` against the worktree instead of the `project_root` set at bootstrap.
- Dropping `BaseModel` context support in `render()`, `GracefulDict`, or `build_task_context`.
- Epic 04's `{{plan.*}}` and `{{issue.*}}` variables. The fill rule admits them automatically once `PhaseRunner` passes them.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Key findings:

- **B5 reproduced on HEAD (`be1d5bf8`).** The bundled validate prompt was rendered with `test_command: "uv run pytest"`. It kept 5 literal `{{test_command}}` and 5 literal `{{lint_command}}`, and `uv run pytest` appeared 0 times. The document prompt got the diff once, from `prompt.md`, but kept 2 literal `{{artifacts.build.diff}}` and 3 `{{doc_mappings}}` from its included `instructions.xml`.
- **ADW names collide with LLM names in only one place.** Across the files that prompts include, only these names are also ADW variables: `artifacts.build.diff(_stats)`, `doc_mappings`, `feature_description`, `run_id`, `test_command`, `lint_command`, `build_command`, `version_bump_command`, `publish_command`, and the ship pre-hook's `pr_number`. All of them are meant to be filled except validate's "Store detected command as `{{test_command}}`" and "Set `{{test_command}} = null`" lines (and their `lint_command` twins), which TASK-002 rewrites. The roughly 200 other placeholders (`{{story_key}}`, `{{analysis.*}}`, `{{#…}}`, `{{x | default: …}}`) are the LLM's.
- **Today, variable values are expanded as directives.** Variables are substituted before includes are expanded, so a ticket description or build diff that contains `{{file:.env}}` pulls that project file into the prompt. The new order closes this.
- **No bundled file nests directives.** Only the five `prompt.md` files contain `{{include:}}` or `{{shared:}}`, so the single include pass changes nothing for bundled commands.
- **Baseline:** the five affected test files pass (186 tests in 6.9 s).

## Decisions

- **The fill rule is keyed on the variables dict, not a hard-coded list.** Pre-hook variables such as `pr_number` and future variables such as Epic 04's `plan.*` qualify automatically, and nothing needs to be kept in sync.
- **An unknown name is silent; a known name with a missing path warns.** After the reorder, the included BMAD files carry about 200 LLM-facing names, and today's per-name warning would flood the log. A missing artifact path is still a probable typo or a skipped phase, and its warning replaces `validate_artifact_references`.
- **`None` renders as `""`** (user's choice). This keeps today's behaviour for custom prompts. So that validate still auto-detects when no command is configured, TASK-002 moves the LLM's working variable to `test_cmd` and `lint_cmd` (also the user's choice, instead of leaving the placeholder in place for `None`).
- **Edit the bundled prompts minimally, and only in validate and ship** (user's choice). Other oddities are left for Epic 05.
- **A single include pass with no nesting.** This matches the module's "no recursive expansion" design, and the bundled commands do not need nesting. An included file's own directives are left verbatim.
- **Keep the existing error codes.** `_read_under` takes the prefix (`INCLUDE`, `SHARED`, `TEMPLATE`) and appends the same suffixes as today. The two "no root" codes become `INCLUDE_NO_ROOT` and `SHARED_NO_ROOT`. Nothing outside `template.py` references `INCLUDE_NO_COMMAND_ROOT`.
- **Task order: the prompt edit (TASK-002) lands before the reorder (TASK-003).** No commit then renders `Execute: ` with an empty command. The B5 fix (TASK-003) is a separate commit from the handler refactor (TASK-004), so the regression tests are RED against a minimal diff.
- **The acceptance tests call `PhaseRunner._load_and_render_prompt` through a small helper.** `run()` would execute `ship/pre.sh` and `document/post.sh`, which need `gh` and a PR. The helper resolves the real bundled command and merged config, which is the production render path minus hooks and the LLM.
- **Validation captures the prompt with a fake `claude` on `PATH`** (user's choice), the recipe from phase 1.6. No product change is needed to save prompts.

## Risks

- **A project file included with `{{file:}}` now has its ADW names filled.** A doc that shows `{{task.identifier}}` as an example would render it as a value. Accepted: only ADW's top-level names are touched, and the bundled prompts use no `{{file:}}`. `docs/templates.md` states the rule.
- **Custom prompts that relied on nested directives lose them.** An `{{include:}}`d file that contained `{{file:}}` used to be expanded. Accepted: no bundled command nests directives, and the docs state the single-pass rule.
- **A future LLM-facing placeholder could collide with an ADW name.** An example is a BMAD file that uses `{{phase}}` for its own step counter. Mitigation: `test_llm_facing_placeholders_survive` renders all five bundled phases and fails if any non-ADW placeholder is lost.
- **Prompts grow.** The plan instructions inline `feature_description` four more times, and the document instructions inline the diff twice more. Accepted: that is what "filled" means, and Epic 05 rewrites these prompts.
- **Merge conflicts with phase 1.9 (ADW-15).** That phase edits `ship/pre.sh`, `ship/post.sh` and the bundled BMAD copies, but not `ship/instructions.xml` or `template.py`. Mitigation: TASK-002 changes only lines 168–170 of `ship/instructions.xml`.

## Acceptance Criteria

- [ ] Rendering the document phase for a run whose build artifacts exist produces a prompt that contains the actual diff and the rendered `doc_mappings`, with no literal `{{artifacts.build.diff}}` or `{{doc_mappings}}`. Evidence: `test_document_prompt_fills_included_build_diff` fails before TASK-003 and passes after it.
- [ ] Rendering the validate phase with `test_command: "uv run pytest"` and `lint_command: "ruff check ."` produces a prompt that contains both commands, with no literal `{{test_command}}` or `{{lint_command}}`. With both unset, the prompt has no empty `Execute:` action. Evidence: `test_validate_prompt_fills_included_commands` and `test_validate_prompt_without_commands_keeps_auto_detect`.
- [ ] Every LLM-facing placeholder in the five bundled phases is present verbatim in the rendered output. The test lists them per phase. Evidence: the `test_llm_facing_placeholders_survive[*]` output.
- [ ] `{{include:../../etc/passwd}}`, `{{shared:../x}}` and `{{file:../x}}` still raise `*_PATH_TRAVERSAL`. Evidence: the parametrized traversal test.
- [ ] A variable value that contains `{{file:…}}` or `{{include:…}}` is emitted literally. Evidence: `test_variable_value_directives_not_expanded`.
- [ ] `grep -rn "validate_artifact_references\|ARTIFACT_REF_PATTERN\|UNKNOWN_VARIABLE\|strict=" src/adw/commands src/adw/core/phase_runner.py` returns nothing.
- [ ] A real `adw run --phase document --from-run` against a real source run, in a scratch repo, with a fake `claude` on `PATH`, captures a prompt that contains the source run's diff inside the instructions section. The before and after snapshots for document and validate are in `VALIDATION.md`.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [ ] TASK-001: Fill only ADW-defined names and drop strict mode
- [ ] TASK-002: Give the validate LLM its own test and lint command names
- [ ] TASK-003: Expand includes before substituting variables (depends on TASK-001,TASK-002)
- [ ] TASK-004: Read every include through one _read_under handler (depends on TASK-003)
- [ ] TASK-005: Document the render order and fill rule (depends on TASK-004)
- [ ] TASK-006: Final Validation
