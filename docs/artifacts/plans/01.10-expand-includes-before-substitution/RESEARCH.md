# Research: Expand includes before substitution

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/commands/template.py` (803 lines):
  - `VARIABLE_PATTERN` `\{\{([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}` matches lowercase dotted names only. `{{PASS/FAIL}}`, `{{#analysis.x}}`, `{{.}}`, `{{x | default: "…"}}` and `{{a - b}}` never match, so the engine never touches them.
  - `ARTIFACT_REF_PATTERN` is used only by `validate_artifact_references`.
  - `FILE_PATTERN`, `INCLUDE_PATTERN` and `SHARED_PATTERN` all have the shape `\{\{<kind>:([^}]+)\}\}`.
  - `validate_artifact_references(template, artifacts_map, *, strict=True, template_path=None)`. Its only production caller passes `strict=False` and ignores the result. It logs a warning for each missing `artifacts.<phase>.<name>`, which `render()` repeats.
  - `TemplateEngine.__init__(project_root=None, command_root=None, shared_root=None)`.
  - `render(template, context, *, strict=True, command_root=None, shared_root=None)` runs: variables, then `_process_includes`, then `_process_shared_inclusions`, then `_process_file_inclusions`. Each include pass runs over the output of the pass before it, so a variable value or an included file that contains a later directive gets expanded.
  - `_process_variables`: a `KeyError` in strict mode is collected into `ConfigError("UNKNOWN_VARIABLE")`. In lenient mode it logs `"Unknown template variable left as-is: {{%s}}"` and returns the match. `None` becomes `""`, and anything else goes through `str()`.
  - `_resolve_variable` walks dicts (with the `GracefulDict` special case) and falls back to `getattr` for objects, which is how `{{context.run_id}}` reaches the `RunContext` model. `.*` goes to `_resolve_wildcard`, which returns `""` for a missing path.
  - The three include handlers are identical apart from the root and the error-code prefix: `INCLUDE_*`, `SHARED_*`, and `TEMPLATE_*` for `{{file:}}`. Suffixes: `_PATH_TRAVERSAL` (twice: not relative, or `ValueError`), `_FILE_NOT_FOUND`, `_FILE_PERMISSION`, `_FILE_IS_DIRECTORY`, `_FILE_ENCODING`. "No root" codes: `INCLUDE_NO_COMMAND_ROOT` and `SHARED_NO_ROOT`. `{{file:}}` always has `self.project_root`.
- `src/adw/core/phase_runner.py`, `_load_and_render_prompt` (≈ lines 329–509):
  - Reads `command.path / "prompt.md"`.
  - Builds `artifacts_map`, either from `artifacts_override` or `_build_artifacts_map`.
  - Calls `validate_artifact_references(..., strict=False)`.
  - Builds `variables`: `context` (the `RunContext` model), `pre_hook_output`, `artifacts`, `inputs`, `run_id`, `phase`, `feature`, `feature_description`, `worktree_path`, `task`, `project_config`, then `pre_hook_vars.json` merged in, then `ship_config`, `version_bump_command` and `publish_command` (ship only), `build_command`, `test_command`, `lint_command` (validate config only), `doc_mappings` and `schema`.
  - Calls `self.template_engine.render(prompt_template, variables, strict=False, command_root=command.path, shared_root=command.path.parent)`.
- `src/adw/cli/bootstrap.py:240`: `TemplateEngine(project_root=project_root)` is the only production construction, and it never passes `command_root` or `shared_root`.
- `src/adw/commands/__init__.py` re-exports `TemplateEngine` only.
- `src/adw/defaults/commands/<phase>/prompt.md`: each of the five includes `{{shared:workflow.xml}}` and `{{include:<workflow>/workflow.yaml}}`. plan, build, validate and document also include `{{include:<workflow>/instructions.xml}}`, and ship includes `{{include:instructions.xml}}`. No other bundled file contains a directive.
- `src/adw/defaults/commands/ship/pre.sh:105` writes `pre_hook_vars.json` with `pr_number`, `pr_url`, `pr_state` and `pr_mergeable`.
- `src/adw/core/orchestrator.py:765` `_load_artifacts_from_source` loads every earlier phase's artifacts from the source run for `--from-run`.
- `src/adw/dashboard/routes.py:875` reads `{phase}_prompt.txt`, which nothing in `src` writes, so rendered prompts are not persisted. The prompt is passed to `claude` as the last argv item (`executors/claude_code.py`, ≈ line 154).

### ADW names inside included files

A scan of `{{…}}` in the files the five prompts include (not `prompt.md`) found these names that are also keys of `variables`:

| File | ADW names | Meant for |
|---|---|---|
| `plan/create-story/instructions.xml` | `feature_description` (×4), `run_id` (×1) | ADW: "Extract {{feature_description}} from context" |
| `document/document-feature/instructions.xml` | `artifacts.build.diff` (×2), `artifacts.build.diff_stats`, `doc_mappings` (×3), `feature_description` | ADW |
| `ship/instructions.xml` | `build_command`, `version_bump_command`, `publish_command` (lines 168–170), `run_id` (line 975), `pr_number` (pre-hook) | ADW. The `{{x \| default: "not configured"}}` forms (lines 198–200, 729–731, 825–827, 937–939) never match `VARIABLE_PATTERN` |
| `validate/code-review-loop/instructions.xml` | `test_command` (lines 99, 101, 186, 201, 224), `lint_command` (109, 111, 122, 137, 160) | Mixed: 99/101/109/111 are the LLM's own assignments ("Store detected command as {{test_command}}", "Set {{test_command}} = null"). The rest are reads |

Every other placeholder is LLM-facing. There are about 200 distinct tokens, for example `story_key`, `tasks_committed`, `analysis.*`, `updates.*`, `changed_files`, `file`, `type`, `date`, `this`, `else`, `{{#…}}`, `{{/…}}` and `{{^…}}`. No included file uses `context`, `phase`, `feature`, `schema`, `task`, `inputs`, `worktree_path`, `pre_hook_output` or `project_config`.

### Validate's command flow (`code-review-loop/instructions.xml`)

- Lines 95–113: `detect-test-command` and `detect-lint-command`. "Check if test command has been provided in the context. If not, … extract the test command …", "Store detected command as {{test_command}}", and "Set {{test_command}} = null" if none. The lint step has the same shape.
- Line 122 `<check if="{{lint_command}} is null">` skips lint. Lines 137 and 160 run `Execute: {{lint_command}}`.
- Line 186 `<check if="{{test_command}} is null">` skips tests. Lines 201 and 224 run `Execute: {{test_command}}`.
- With variables substituted first (today), none of these are filled, and the LLM detects the command every run. Setting `test_command` in `project.yaml` has no effect (B5).
- With includes first and `None → ""`, an unconfigured project would render `<check if=" is null">` and `Execute: `. The detect step would then have no placeholder left to fill. TASK-002 fixes the text first.

## Architecture Facts

- Rendering is one call per phase. `PhaseRunner.run` runs the pre-hook, then `_load_and_render_prompt`, then the executor, the artifacts and the post-hook. `_load_and_render_prompt` has no side effects beyond logging, so tests can call it directly.
- `_get_merged_config(phase, command)` merges the bundled `config.yaml` with the project's `.adw/commands/<phase>/config.yaml`. `_load_project_config(phase)` reads only the project file, and it is the only source of `lint_command` and `doc_mappings`.
- `CommandResolver(project_root).resolve(phase)` returns the bundled `ResolvedCommand` when the project has no override (`tests/integration/test_document_phase.py` relies on this).
- `_build_artifacts_map(run_id, phase)` reads `<runs_dir>/<run_id>/artifacts/<earlier phase>/*` and strips extensions: `diff.txt` becomes `artifacts.build.diff`.
- `MockExecutor` keeps prompts in the private `_all_prompts` and exposes only `call_count` (phase 1.2 deleted the helpers).
- `render()` accepts a `BaseModel` context through `model_dump()`. `PhaseRunner` always passes a dict whose `context` value is the model itself, resolved by `getattr`.

## Constraints

- ADR-001: test behaviour, errors, security and I/O. Do not assert prompt prose. The acceptance tests assert on filled values, surviving placeholders and the absence of empty `Execute:` actions, not on wording.
- Tests that construct `PhaseRunner` write under `tmp_path`. Nothing runs git or hooks, because the helper calls `_load_and_render_prompt` directly.
- mypy `--strict` covers `src/adw` only.
- Phase 1.9 (ADW-15) is unmerged and edits `ship/pre.sh`, `ship/post.sh`, `document/post.sh`, `build/post.sh`, `plan/pre.sh` and three bundled BMAD copies. This plan touches only `ship/instructions.xml` lines 168–170 among the ship files.
- Epic 05 depends on this phase: its prompts rely on "includes are expanded before variables are filled, and only ADW-defined names are filled."

## Useful Commands

```bash
# Affected tests (baseline at be1d5bf8: 186 passed in 6.9 s)
uv run pytest tests/unit/commands/test_template.py tests/unit/core/test_artifact_passing.py \
  tests/integration/test_document_phase.py tests/unit/core/test_phase_runner.py \
  tests/integration/core/test_phase_runner_integration.py -o addopts="" -q

# B5 reproduction: render bundled prompts with the engine directly
uv run python - <<'EOF'
import logging
from pathlib import Path
from adw.commands.template import TemplateEngine
logging.disable(logging.CRITICAL)
root = Path("src/adw/defaults/commands")
eng = TemplateEngine(project_root=Path.cwd())
v = {"test_command": "uv run pytest", "lint_command": "ruff check"}
out = eng.render((root / "validate/prompt.md").read_text(), v, strict=False,
                 command_root=root / "validate", shared_root=root)
print(out.count("{{test_command}}"), out.count("uv run pytest"))  # HEAD: 5 0
EOF

# Real runs with a non-empty build diff, usable as a --from-run source for validation
find ../../.adw/runs -name diff.txt -size +0 | head   # e.g. 01KF636397JZC18V4K8MGS59G7, 01KH72J5HMVVJGQBPWJS26R337
```

## Uncertainty

- **Whether any user project nests directives.** Unknowable from here. The bundled commands do not. Resolved as an accepted risk, and documented in `docs/templates.md`.
- **Whether a copied real run loads in a scratch repo.** `--from-run` loads `context.json` through `ContextManager(runs_dir).load(id)`. An older run's `context.json` might fail validation against the current `RunContext`. Fallback for TASK-006: produce the source run in the scratch repo with the fake `claude`. It appends a line to a tracked file on the build call, so `diff.txt` is non-empty.
- **Whether `{{doc_mappings}}` renders usefully.** It is `str()` of a list of dicts: `[{'source_pattern': 'src/**', 'docs_dir': 'docs'}]`, or `[]` when unset. The document instructions' `<check if="{{doc_mappings}} is empty">` reads as `<check if="[] is empty">`. Good enough, and the format is left as it is.

## References

- Epic: [01 — Cleanup, phase 1.10](../../epics/01-cleanup-safety-dead-code-bugs.md)
- Epic 05's dependency note: [05 — Plan-workflow phase prompts](../../epics/05-plan-workflow-phase-prompts.md)
- [docs/templates.md](../../../templates.md), [PhaseRunner deep dive](../../../architecture/deep-dive/phase-runner.md)
- [ADR-001 test reduction strategy](../../../architecture/adrs/ADR-001-test-reduction-strategy.md)
- Fake `claude` recipe: [phase 1.6 RESEARCH.md](../archive/2026-09-23-01.6-fail-phases-when-claude-fails/RESEARCH.md)
