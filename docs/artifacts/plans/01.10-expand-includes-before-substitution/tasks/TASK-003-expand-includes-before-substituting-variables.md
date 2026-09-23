# TASK-003: Expand includes before substituting variables

Depends on: TASK-001, TASK-002
Suggested commit: `fix(template): expand includes before substituting variables`

## Goal

`render()` expands `{{include:}}`, `{{shared:}}` and `{{file:}}` first and substitutes variables second. ADW's names inside included files get filled, and variable values are never expanded as directives (B5).

## Files

- `src/adw/commands/template.py`, `render()`: move `_process_variables` after the three include passes. The order becomes include, shared, file, then variables. This is the whole production change. TASK-004 replaces the three passes with one.
  - Update the module docstring, the class docstring and `render()`'s docstring. Each currently says "Variables are processed first, then file inclusions."
- `tests/unit/commands/test_template.py`, class `TestSingleLevelSubstitution`:
  - `test_file_content_not_expanded` becomes `test_included_content_is_filled`. A `{{file:config.txt}}` whose content is `Run {{some_var}} then {{story_key}}`, with `{"some_var": "REPLACED"}`, renders as `Run REPLACED then {{story_key}}`.
  - `test_variables_processed_before_files` becomes `test_includes_expanded_before_variables`. `{{include:header.txt}}` holds `Cmd: {{test_command}}`, `command_root=tmp_path`, and `{"test_command": "uv run pytest"}` renders as `Cmd: uv run pytest`.
  - add `test_variable_value_directives_not_expanded`:
    - `tmp_path/secret.txt` holds `SECRET` and `tmp_path/x.txt` holds `INCLUDED`
    - `{{desc}}` with `{"desc": "see {{file:secret.txt}} and {{include:x.txt}}"}` and `command_root=tmp_path` renders as exactly the value
    - `SECRET` and `INCLUDED` do not appear
- New `tests/integration/core/test_prompt_rendering.py`, which renders the real bundled commands through `PhaseRunner`'s render path:
  - Helper `_render(project_root, phase, *, project_config=None) -> tuple[str, set[str]]`. It returns the prompt and the variable keys ADW passed:
    - `resolver = CommandResolver(project_root=project_root)`, `engine = TemplateEngine(project_root=project_root)`
    - `runner = PhaseRunner(command_resolver=resolver, template_engine=engine, hook_runner=MagicMock(), executor=MockExecutor(), artifact_manager=ArtifactManager(runs_dir=project_root / ".adw" / "runs"), project_config=project_config)`
    - `command = resolver.resolve(phase)`, and assert `command.tier == "bundled"`
    - `ctx = RunContext(run_id=RUN_ID, feature_description="Add OAuth login", current_phase=phase, started_at=datetime.now(UTC))`
    - `with patch.object(engine, "render", wraps=engine.render) as spy:` call `runner._load_and_render_prompt(phase, ctx, "", command, merged_config=runner._get_merged_config(phase, command))`
    - return the prompt and `set(spy.call_args.args[1])`
  - Fixture `project(tmp_path)` writes:
    - build artifacts under `.adw/runs/<RUN_ID>/artifacts/build/`: `diff.txt` containing `+DIFF-MARKER-7f3a`, `diff_stats.json` and `build_output.md`
    - `plan/plan_output.md`
    - `validate/validate_output.md`
    - `.adw/commands/document/config.yaml` with `doc_mappings: [{source_pattern: "src/**", docs_dir: "docs/features"}]`
  - `test_document_prompt_fills_included_build_diff(project)` (the B5 regression test):
    - `instructions = prompt.split("### Instructions", 1)[1]`
    - `DIFF-MARKER-7f3a` is in `instructions`
    - `docs/features` is in `instructions`
    - `{{artifacts.build.diff}}`, `{{artifacts.build.diff_stats}}` and `{{doc_mappings}}` are not in `prompt`
  - `test_validate_prompt_fills_included_commands(project)` (the B5 regression test): `project_config=ProjectConfig(name="t", language="python", test_command="uv run pytest")`, plus `.adw/commands/validate/config.yaml` with `lint_command: "ruff check ."`. Assert:
    - `` `uv run pytest` `` and `` `ruff check .` `` are in `prompt`
    - `{{test_command}}` and `{{lint_command}}` are not
  - `test_validate_prompt_without_commands_keeps_auto_detect(project)`: no test or lint command. Assert:
    - `re.search(r"Execute:\s*</action>", prompt)` is `None`
    - `re.search(r'if="\s*is null"', prompt)` is `None`
  - `test_llm_facing_placeholders_survive[plan|build|validate|document|ship]`, parametrized:
    - Read `prompt.md` and each file its `{{include:…}}` (under `command.path`) and `{{shared:…}}` (under `command.path.parent`) directives name.
    - Collect every `\{\{([^}]+)\}\}` token that is not an `include:`, `shared:` or `file:` directive.
    - A token is ADW-owned when `VARIABLE_PATTERN.fullmatch("{{" + tok + "}}")` matches and `tok.split(".", 1)[0]` is in the returned keys. Every other token is LLM-facing.
    - Assert every LLM-facing `{{tok}}` is in `prompt`. The failure message lists the missing tokens, sorted.
    - Assert that at least one token is LLM-facing, so a broken scanner cannot pass vacuously.
    - Render with `project_config` carrying `test_command` and `build_command`, so the command names count as ADW-owned.

## Acceptance

- [ ] RED on the TASK-002 code:
  - `test_document_prompt_fills_included_build_diff` fails: the marker is not in the instructions section, and the literal `{{artifacts.build.diff}}` is present
  - `test_validate_prompt_fills_included_commands` fails
  - `test_variable_value_directives_not_expanded` fails: `SECRET` appears
  - `test_includes_expanded_before_variables` fails
- [ ] GREEN after the reorder, together with `test_validate_prompt_without_commands_keeps_auto_detect` and all five `test_llm_facing_placeholders_survive` cases.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

Evidence: the RED and GREEN output of `uv run pytest tests/integration/core/test_prompt_rendering.py tests/unit/commands/test_template.py -o addopts="" -v`. The RED output is the B5 regression evidence for `VALIDATION.md` and for the epic-level "fails on the pre-epic code" criterion.

## Steps

### RED
- [ ] Write the new integration module and the three unit-test changes, and run them against the TASK-002 code. Save the failing output.

### GREEN
- [ ] Move `_process_variables` to the end of `render()`.
- [ ] Rerun the two test files, then `tests/integration/test_document_phase.py` and `tests/unit/core/test_phase_runner.py`.

### REFACTOR
- [ ] Update the three docstrings for the new order.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- `_load_and_render_prompt` is private, but it is exactly the production render path. `run()` would execute `ship/pre.sh`, which needs `gh` and a PR, and `document/post.sh`. The helper keeps the tests off git and hooks, so no `git_repo` or `chdir` is needed.
- `lint_command` and `doc_mappings` come only from the project's `.adw/commands/<phase>/config.yaml`, through `_load_project_config`. `test_command` and `build_command` come from `ProjectConfig`. Confirm that a config-only project dir does not shadow the bundled command, which is the purpose of the `tier == "bundled"` assert.
- The placeholder test is a guard: it also passes on the pre-reorder code, where nothing included is touched. It fails if a later change fills a name ADW does not own, or drops LLM text.
- `ship` without `pre_hook_vars.json` has no `pr_*` keys, so `{{pr_number}}` counts as LLM-facing in that case and must survive verbatim. That is correct under the fill rule.
