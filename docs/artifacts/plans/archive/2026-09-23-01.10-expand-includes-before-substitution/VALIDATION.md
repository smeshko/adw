# Validation: Expand includes before substitution

Validated: 2026-09-23 at `1b429269`. CI is green on every task commit of PR #211.

| Criterion | Result |
|---|---|
| Document phase with build artifacts: the prompt carries the diff and the rendered `doc_mappings`, with no literal `{{artifacts.build.diff}}` or `{{doc_mappings}}` | Met: `test_document_prompt_fills_included_build_diff` RED on the TASK-002 code, GREEN after TASK-003; scratch run below |
| Validate with `test_command: "uv run pytest"` and `lint_command: "ruff check ."`: both commands appear, no literal placeholders; with both unset, no empty `Execute:` | Met: `test_validate_prompt_fills_included_commands` (RED, then GREEN), `test_validate_prompt_without_commands_keeps_auto_detect` |
| Every LLM-facing placeholder in the five bundled phases survives verbatim | Met: `test_llm_facing_placeholders_survive[plan,build,validate,document,ship]`, which checks 15, 14, 34, 91 and 84 LLM-facing placeholders |
| `{{include:../../etc/passwd}}`, `{{shared:../x}}`, `{{file:../x}}` raise `*_PATH_TRAVERSAL` | Met: `TestDirectives::test_directive_path_traversal_raises[include,shared,file]` |
| A variable value that contains `{{file:…}}` or `{{include:…}}` is emitted literally | Met: `test_variable_value_directives_not_expanded`. On the TASK-002 code it rendered `see SECRET and INCLUDED` |
| `grep -rn "validate_artifact_references\|ARTIFACT_REF_PATTERN\|UNKNOWN_VARIABLE\|strict=" src/adw/commands src/adw/core/phase_runner.py` is empty | Met |
| Real `adw run --phase document --from-run` in a scratch repo with a fake `claude`: the prompt carries the source diff inside the instructions section; before/after snapshots below | Met: before 0, after 2 occurrences of the diff's first line after `### Instructions` |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 3706 passed, 5 skipped, 85.35% |

## Preflight and full suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
153 files already formatted
==> mypy
Success: no issues found in 153 source files
preflight: ok

$ uv run pytest -p no:cacheprovider
Required test coverage of 80% reached. Total coverage: 85.35%
================= 3706 passed, 5 skipped in 178.81s (0:02:58) ==================
```

## Greps

```
$ grep -rn "validate_artifact_references\|ARTIFACT_REF_PATTERN\|UNKNOWN_VARIABLE\|strict=" src/adw/commands src/adw/core/phase_runner.py
(no output)

$ grep -n "_process_includes\|_process_shared_inclusions\|_process_file_inclusions\|INCLUDE_NO_COMMAND_ROOT\|self.command_root\|self.shared_root" src/adw/commands/template.py
(no output)

$ grep -n "strict_artifacts\|Validate artifact references" docs/architecture/deep-dive/phase-runner.md
(no output)
```

## B5 regression tests

RED, on the TASK-002 code (`ad30bb25`, variables still substituted before includes):

```
FAILED integration/core/test_prompt_rendering.py::test_document_prompt_fills_included_build_diff
  assert 'DIFF-MARKER-7f3a' in '\n<workflow>\n  <!-- ===… (instructions section)
FAILED integration/core/test_prompt_rendering.py::test_validate_prompt_fills_included_commands
  assert '`uv run pytest`' in '# Validation Phase\n\nTest and review the implementation of the plan.…
FAILED unit/commands/test_template.py::TestSingleLevelSubstitution::test_included_content_is_filled
  AssertionError: assert 'Run {{some_v...{{story_key}}' == 'Run REPLACED...{{story_key}}'
FAILED unit/commands/test_template.py::TestSingleLevelSubstitution::test_includes_expanded_before_variables
  AssertionError: assert 'Cmd: {{test_command}}' == 'Cmd: uv run pytest'
FAILED unit/commands/test_template.py::TestSingleLevelSubstitution::test_variable_value_directives_not_expanded
  AssertionError: assert 'see SECRET and INCLUDED' == 'see {{file:s...clude:x.txt}}'
5 failed, 67 passed in 0.38s
```

RED for TASK-004, on the TASK-003 code (`280b3a89`):

```
FAILED unit/commands/test_template.py::TestDirectives::test_directive_without_root_raises[include]
  AssertionError: assert 'INCLUDE_NO_COMMAND_ROOT' == 'INCLUDE_NO_ROOT'
FAILED unit/commands/test_template.py::TestDirectives::test_included_directives_not_expanded
  AssertionError: assert 'SECRET' == '{{file:secret.txt}}'
2 failed, 7 passed
```

GREEN, at `1b429269`:

```
integration/core/test_prompt_rendering.py::test_document_prompt_fills_included_build_diff PASSED
integration/core/test_prompt_rendering.py::test_validate_prompt_fills_included_commands PASSED
integration/core/test_prompt_rendering.py::test_validate_prompt_without_commands_keeps_auto_detect PASSED
integration/core/test_prompt_rendering.py::test_llm_facing_placeholders_survive[plan] PASSED
integration/core/test_prompt_rendering.py::test_llm_facing_placeholders_survive[build] PASSED
integration/core/test_prompt_rendering.py::test_llm_facing_placeholders_survive[validate] PASSED
integration/core/test_prompt_rendering.py::test_llm_facing_placeholders_survive[document] PASSED
integration/core/test_prompt_rendering.py::test_llm_facing_placeholders_survive[ship] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_path_traversal_raises[include] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_path_traversal_raises[shared] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_path_traversal_raises[file] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_missing_file_raises[include] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_missing_file_raises[shared] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_missing_file_raises[file] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_without_root_raises[include] PASSED
unit/commands/test_template.py::TestDirectives::test_directive_without_root_raises[shared] PASSED
unit/commands/test_template.py::TestDirectives::test_included_directives_not_expanded PASSED
unit/commands/test_template.py::TestFillRule::test_unknown_top_level_name_passes_through_silently PASSED
unit/commands/test_template.py::TestFillRule::test_known_name_with_missing_path_passes_through_and_warns PASSED
unit/commands/test_template.py::TestFillRule::test_known_and_unknown_names_mixed PASSED
unit/commands/test_template.py::TestFillRule::test_top_level_name_is_the_first_segment PASSED
unit/commands/test_template.py::TestSingleLevelSubstitution::test_included_content_is_filled PASSED
unit/commands/test_template.py::TestSingleLevelSubstitution::test_includes_expanded_before_variables PASSED
unit/commands/test_template.py::TestSingleLevelSubstitution::test_variable_value_directives_not_expanded PASSED
… (3 more TestSingleLevelSubstitution cases)
27 passed in 0.18s
```

The placeholder guard is not vacuous. With `test_command` and `build_command` set, the ADW-owned names per phase are:

```
plan      LLM-facing 15  ADW-owned: context, feature_description, inputs.*, run_id
build     LLM-facing 14  ADW-owned: artifacts.plan.plan_output, context, inputs.*, project_config
validate  LLM-facing 34  ADW-owned: artifacts.build.diff, artifacts.plan.plan_output, context, inputs.*, lint_command, project_config, test_command
document  LLM-facing 91  ADW-owned: artifacts.build.{build_output,diff,diff_stats}, artifacts.validate.*, context, doc_mappings, feature_description, inputs.*
ship      LLM-facing 84  ADW-owned: artifacts.build.build_output, artifacts.document.pr_description, artifacts.validate.*, build_command, context, feature_description, inputs.*, run_id, ship_config
```

## Scratch-repo prompt capture

Everything ran under the session scratchpad (`$S`), with `HOME=$S/home`, `PATH=$S/bin:$PATH` and `ADW_MOCK_EXECUTOR` unset. "Before" is `git archive be1d5bf8` with its own `uv sync`. "After" is this checkout's `.venv` at the final code.

- `$S/bin/claude` writes its last argument to `$PROMPT_DIR/prompt-$$.md`, appends a line to `app.py` when the prompt starts with `# Build Phase`, and prints an assistant message and a success `result`. `$S/bin/gh` exits 1.
- The scratch repo has `.adw/project.yaml` (`test_command: "uv run pytest"`, worktrees off), `.adw/commands/validate/config.yaml` (`lint_command: "ruff check ."`), `.adw/commands/document/config.yaml` (one `doc_mappings` entry to `docs/features`), a `.gitignore` for `.adw/runs/`, and a committed `app.py`.

**Source run.** Copying the real run `01KF636397JZC18V4K8MGS59G7` did not work: `--from-run` failed with `Worktree for run '01KF636397JZC18V4K8MGS59G7' no longer exists at …/trees/01KF636397JZC18V4K8MGS59G7`. I used the plan's fallback and produced the source run in the scratch repo with the "before" code: `adw run --phase plan "Add a greeting to app.py"`, then `--phase build --from-run` and `--phase validate --from-run` on the same run. The last two were needed because document requires validate artifacts. Run `01M37TKHK570WRGYGQ5PHVN1EZ` has a 119-byte `build/diff.txt` whose first line is `diff --git a/app.py b/app.py`.

Each capture ran in a fresh copy of that repo state:

```
$ adw run --phase document --from-run 01M37TKHK570WRGYGQ5PHVN1EZ   # before: exit 0, after: exit 0 (PR creation fails on the fake gh, as intended)
$ adw run --phase validate --from-run 01M37TKHK570WRGYGQ5PHVN1EZ   # before: exit 0, after: exit 0

                   literal {{artifacts.build.diff}}|{{doc_mappings}}|{{test_command}}|{{lint_command}}
before-document    5
before-validate   10
after-document     0
after-validate     0

before-document: diff first line after "### Instructions": 0 occurrences
after-document:  diff first line after "### Instructions": 2 occurrences
before-validate: 'ruff check .' 0 times  ('uv run pytest' once, only inside the project_config dump)
after-validate:  'ruff check .' 1 time,  'uv run pytest' 2 times
```

`diff -u` of the instructions section (text after `### Instructions`), before against after, validate:

```diff
@@ -94,24 +94,20 @@
       <step name="detect-test-command">
-        <critical>Auto-detect the test command based on project structure</critical>
-        <action>Check if test command has been provided in the context. 
-        If not, try to the best of your abilities extract the test command based on the project structure and framework.</action>
-        <action>Store detected command as {{test_command}}</action>
-        <check if="no test command detected">
-          <action>Set {{test_command}} = null</action>
+        <critical>Use the configured test command; auto-detect only when none is configured</critical>
+        <action>Provided test command: `uv run pytest` (empty = not configured)</action>
+        <action>If the provided test command is not empty, set test_cmd to it.
+        Otherwise, try to the best of your abilities to extract the test command based on the project structure and framework, and set test_cmd to it.</action>
+        <check if="no test command provided or detected">
+          <action>Set test_cmd = null</action>
           <note>Will skip test phase if no test framework detected</note>
         </check>
       </step>
 
       <step name="detect-lint-command">
-        <action>Check if lint command has been provided in the context.
-        If not, set to null.</action>
-        <action>Store as {{lint_command}}</action>
-        <check if="no lint command detected">
-          <action>Set {{lint_command}} = null</action>
-          <note>Will skip lint phase if no linter configured</note>
-        </check>
+        <action>Provided lint command: `ruff check .` (empty = not configured)</action>
+        <action>If the provided lint command is not empty, set lint_cmd to it. Otherwise, set lint_cmd = null.</action>
+        <note>Will skip lint phase if no linter configured</note>
       </step>
@@ -120,7 +116,7 @@
-        <check if="{{lint_command}} is null">
+        <check if="lint_cmd is null">
@@ -135,7 +131,7 @@
-        <action>Execute: {{lint_command}}</action>
+        <action>Execute: lint_cmd</action>
   (and the same for the re-run, the test null check and both test Execute actions)
```

Document:

```diff
@@ -42,8 +42,20 @@
     <action>Extract list of changed files from context:
-      - Check {{artifacts.build.diff_stats}} for file change information
-      - Check {{artifacts.build.diff}} for actual changes
+      - Check {
+  "files_changed": 1,
+  "insertions": 1,
+  "deletions": 0,
+  "binary_files": 0
+} for file change information
+      - Check diff --git a/app.py b/app.py
+index b80e322..e8bb1d4 100644
+--- a/app.py
++++ b/app.py
+@@ -1 +1,2 @@
+ print("hi")
++built
+ for actual changes
@@ -117,10 +129,10 @@
-    <critical>doc_mappings is available via {{doc_mappings}} template variable (list of {source_pattern, docs_dir})</critical>
+    <critical>doc_mappings is available via [{'source_pattern': 'src/**', 'docs_dir': 'docs/features'}] template variable (list of {source_pattern, docs_dir})</critical>
-    <check if="{{doc_mappings}} is empty">
+    <check if="[{'source_pattern': 'src/**', 'docs_dir': 'docs/features'}] is empty">
@@ -808,7 +827,7 @@
-[1-2 sentence summary of what this PR accomplishes, derived from {{feature_description}}]
+[1-2 sentence summary of what this PR accomplishes, derived from Add a greeting to app.py]
```

## Lines of code

`find src -name '*.py' | xargs wc -l`:

- 43,445 lines at `be1d5bf8`, the plan's baseline
- 42,282 lines at `1212c5b4`, this branch's base. #208 removed the terminal dashboard in between.
- 41,983 lines at `1b429269`

This phase changes the count by −299. `template.py` goes from 803 to 518 lines, and `phase_runner.py` from 1,341 to 1,327.
