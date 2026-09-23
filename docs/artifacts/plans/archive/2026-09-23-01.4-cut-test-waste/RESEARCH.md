# Research: Cut test waste outside the dashboard

Curated findings only — no raw conversation transcripts. Measured at `f61f8873` on 2026-09-23.

## Baseline

- `uv run pytest --collect-only -q -o addopts=""`: **4,296 tests collected**.
- `uv run pytest`: **4,291 passed, 5 skipped in 163.00 s**; `TOTAL 13593 1855 3882 408 84%`, **84.33 %**.
- `uv run ruff check tests/` and `uv run ruff format --check tests/`: clean (229 files). `scripts/preflight.sh` lints only `src/`, so run these by hand.

## Test-count budget

The deletion targets named in the epic, as collected (parametrize expands some files):

| Target | Collected |
|---|---:|
| `tests/unit/ship/test_failure_diagnosis.py` (all `pass`) | 36 |
| `tests/unit/ship/test_command_execution.py` (all `pass`) | 16 |
| `tests/unit/ship/test_release_notes.py` (instructions.xml prose) | 42 |
| `tests/unit/ship/test_report_generation.py` (instructions.xml prose) | 44 |
| `tests/unit/commands/test_validate_prompt.py` (prompt.md prose) | 12 |
| `test_bundled_commands.py::TestShipPhaseInstructionsXml` | 11 |
| `tests/unit/core/test_constants.py` | 1 |
| `test_claude_code.py::TestClaudeCodeExecutorClass` | 4 |
| `test_claude_code.py::TestHookRunnerTimeoutResolution` | 4 |
| **Named targets** | **170** |

Adjustments:

| Change | Δ |
|---|---:|
| 3 `_resolve_timeout` precedence tests re-added in `hooks/test_runner.py` | +3 |
| `test_handles_json_array` | −1 |
| 6 existence tests in `TestBundledCommands` (`test_bundled_{plan,build,validate,document,ship}_exists`, `test_bundled_ship_has_instructions_xml`) | −6 |
| `TestFlatTemplateVariables` (3 of the 16 in `test_ship_phase_fixes.py`) | −3 |
| New bundled-phase check, one item per phase in `PHASE_SEQUENCE` | +5 |
| **Net** | **−172 → ~4,124** |

Fixture deduplication changes no test count.

## Key Files & Directories

- `tests/conftest.py`: the root fixtures. It keeps `isolated_home` (autouse), `git_repo` and `_cleanup_worktrees`. Six fixtures have no consumer; each name is either unused or shadowed by a local definition:

  | Fixture | Status |
  |---|---|
  | `tmp_adw_dir` | unused |
  | `sample_project_config` | unused |
  | `sample_config_yaml` | unused; the only reader of `fixtures/configs/minimal.yaml` |
  | `mock_executor` | shadowed in `unit/core/test_phase_runner.py` and `integration/test_document_phase.py` |
  | `sample_run_context` | shadowed in `integration/core/test_artifact_manager_integration.py` |
  | `fixtures_path` | shadowed in `integration/test_token_tracking.py` and `integration/test_hooks.py` |

  After the deletion, `MockExecutor`, `ProjectConfig`, `RunContext`, `ULID` and `datetime` are likely unused imports; ruff F401 flags them. The `ADW_MOCK_EXECUTOR` and `LINEAR_*` env setup at module top stays.
- `tests/fixtures/`: `llm/`, `configs/` and `runs/` are referenced only through `sample_config_yaml`. `claude_output/` (token tracking) and `hooks/` (hook tests) stay.
- `src/adw/defaults/commands/<phase>/`: each phase has `config.yaml` and `prompt.md`. The `instructions.xml` files:
  - `ship/instructions.xml`
  - `build/dev-story/instructions.xml`
  - `document/document-feature/instructions.xml`
  - `plan/create-story/instructions.xml`
  - `validate/code-review-loop/instructions.xml`

  All five, plus the shared `commands/workflow.xml`, parse with `xml.etree.ElementTree` today.
- `src/adw/commands/loader.py:40` `get_config_class(phase)`: maps a phase to its `CommandConfig` subclass. Production calls it from `phase_runner.py:719`/`786`, `extensions/ship.py:74`, `config/checker.py:300` and `dashboard/mutations.py:829`. The load pattern to copy is `phase_runner.py:710-719`: `yaml.safe_load` → `{}` if `None` → `model_validate`. Every config model sets `ConfigDict(extra="forbid")` (`models/command.py`), so an unknown key fails validation.
- `src/adw/core/constants.py:15` `PHASE_SEQUENCE`: `("plan", "build", "validate", "document", "ship")`.
- `src/adw/hooks/runner.py:64` `HookRunner._resolve_timeout`: precedence is parameter → `config.timeout_seconds` → `DEFAULT_HOOK_TIMEOUT` (60). It is reached in production from `run_hook` (`:165`), and only `TestHookRunnerTimeoutResolution` tests it.
- `tests/unit/hooks/test_runner.py`: `TestHookRunner` (line 16) and `TestFindHook` (line 199, which phase 1.2 deletes). It already imports `HookRunner` and `HookConfig`.

## Fixture duplicate groups

Grouped by an MD5 of each fixture's AST: body without docstring, arguments and decorators. See Useful Commands.

**`git_repo`: 6 local definitions in 4 files, all differing from the root.**

| File | Scope | Differs from root by | Test dependency on the difference |
|---|---|---|---|
| `unit/worktree/test_branch.py:45, 116, 250` | 3 × class | README text "# Test"; no teardown | none |
| `integration/worktree/test_single_phase_preservation.py:24` | class | "Test User", README "# Test Project"; no teardown | asserts `README.md` exists in the worktree, which the root also creates |
| `integration/test_git_hooks.py:27` | module | "Test User", README "# Test Project\n" | tests overwrite `README.md` and assert the name only |
| `integration/test_git_diff.py:24` | module | repo at `tmp_path/test_repo`; commits `initial.txt` holding "initial content" | `test_capture_diff_with_modified_file` and `test_capture_diff_with_deleted_file` use `initial.txt`, and one asserts `"-initial content"` |

No test in `test_git_diff.py` takes both `git_repo` and `tmp_path`: `test_has_commits_false_for_empty_repo` and `test_capture_staged_diff_in_empty_repo` take only `tmp_path`. Moving the repo to `tmp_path` itself therefore collides with nothing. The root fixture's README content is `"# Test Repository"`, with no trailing newline.

**`sample_context`: 21 definitions, 14 distinct bodies.**

- `2b1f6c` ×8. Seven are class-level in `unit/core/test_snapshot_manager.py`, in classes `TestPrePhaseSnapshot`, `TestPostPhaseSnapshot`, `TestSequentialNumbering`, `TestSnapshotListing`, `TestSnapshotLoading`, `TestPerformance` and `TestSequenceCache`. The eighth is `integration/core/test_snapshot_integration.py:26`, a different package, so it stays. **The seven collapse to one module-level fixture.**
- `caa062` ×2: `unit/core/test_resume_manager.py:65` and `unit/models/test_resume.py:20`, in different packages. Both stay.
- 12 singletons stay, including `integration/core/test_snapshot_integration.py:142` (`0a3a52`).

**`executor`: 13 definitions, all `ClaudeCodeExecutor(LLMConfig(path="claude"))`.**

The AST hash separates `test_claude_code.py:1666`, but only because it inlines the config variable; it is the same object.

- 11 are class-level in `unit/executors/test_claude_code.py`, in classes `TestClaudeCodeExecutorExecute`, `TestSubprocessExecution`, `TestRealTimeStreaming`, `TestOutputParsing`, `TestErrorHandling`, `TestFinalOutputParsing`, `TestAdditionalParsingCoverage`, `TestDurationOnFailure`, `TestExceptionCleanup`, `TestWorktreeWorkingDirectory` and `TestExtractToolCall`. **They collapse to one module-level fixture.**
- 2 are class-level in `tests/integration/`: `test_claude_code_executor.py:39` (`TestClaudeCodeIntegration`) and `test_token_tracking.py:22` (`TestTokenTrackingIntegration`). **Both move to a new `tests/integration/conftest.py`.**

`tests/integration/__init__.py`, `tests/unit/core/__init__.py` and `tests/unit/executors/__init__.py` exist, so test modules are package-qualified and a same-named file elsewhere cannot collide.

## `TestAdditionalParsingCoverage`: branch-coverage diff

`uv run pytest tests/unit/executors tests/integration -o addopts="" --cov=adw.executors.claude_code --cov-branch`, run with and without the class deselected:

- With the class: `233 29 94 13 85%`.
- Without it: `233 31 94 17 83%`. It newly misses `417-418`, `461->404`, `467->404` and `477->404`.

| Test | Unique branch in `_parse_output` |
|---|---|
| `test_handles_non_dict_json` | 417-418: JSON that isn't a dict becomes content |
| `test_handles_json_array` | 417-418, the same branch (**redundant**) |
| `test_result_message_with_text` | 461->404: result text outside an assistant message |
| `test_content_block_delta_non_text_delta` | 467->404: a non-`text_delta` delta is ignored |
| `test_message_delta_without_usage` | 477->404: `message_delta` with no usage |

`integration/test_token_tracking.py` covers none of these branches, contrary to the epic's premise.

## `pass` placeholders

The AST scan (Useful Commands) for test functions whose body, docstring aside, is only `pass` finds `test_failure_diagnosis.py` (36) and `test_command_execution.py` (16), 52 in total, both in `tests/unit/ship/`.

The other `grep -rn "^\s*pass$" tests/unit` hits are not test bodies, and they stay:

```
tests/unit/webhook/providers/test_base.py:78       stub method
tests/unit/core/test_context_manager.py:463        except block
tests/unit/core/test_run_directory.py:140          with/except block
tests/unit/task_managers/test_base.py:53,59,65,68,71   stub Protocol implementations
tests/unit/executors/test_protocol.py:35           `class BadExecutor: pass`
tests/unit/commands/test_template.py:534           except block
tests/unit/logging/test_manager.py:63              stub method
```

Line numbers can shift once the other tasks land. Re-run the grep in TASK-007 and check that each hit is still one of these.

## Constraints

- Test-only phase: the one non-test change is ADR-001. No `src/` file changes.
- `tests/unit/ship/test_ship_phase_fixes.py` resolves nothing through `Path(__file__)`, so the move to `tests/unit/core/` needs no path fixes.
- `test_ship_phase_fixes.py`'s `TestFlatTemplateVariables` builds a local `dict` and asserts on it; no production code runs. The other classes, `TestShipConfigFormat`, `TestHookChaining` and `TestShipCommandEnvVars`, exercise `ShipExtension`, `ShipCommandConfig` and `CommandResolver`, and they stay.
- ADR-001 (`docs/architecture/adrs/ADR-001-test-reduction-strategy.md`) has a 7-row "Categories to Eliminate" table (Category | Description | Example) at lines 22-32, then "Categories to KEEP".

## Useful Commands

```bash
# Collected count (before/after)
uv run pytest --collect-only -q -o addopts="" | tail -1

# pass-only test bodies across tests/ (expect "total 0" after TASK-002)
uv run python - <<'EOF'
import ast, pathlib, collections
c = collections.Counter()
for p in sorted(pathlib.Path("tests").rglob("test_*.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant):
                b = b[1:]
            if all(isinstance(x, ast.Pass) for x in b):
                c[str(p)] += 1
for k, v in c.items():
    print(v, k)
print("total", sum(c.values()))
EOF

# Duplicate fixture groups (body+args+decorators hash)
uv run python - git_repo sample_context executor <<'EOF'
import ast, pathlib, hashlib, collections, sys
names = set(sys.argv[1:]); groups = collections.defaultdict(list)
for p in sorted(pathlib.Path("tests").rglob("*.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names \
                and any("fixture" in ast.unparse(d) for d in n.decorator_list):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant):
                b = b[1:]
            src = "\n".join(map(ast.unparse, b)) + "|args=" + ",".join(a.arg for a in n.args.args) \
                + "|dec=" + ";".join(map(ast.unparse, n.decorator_list))
            groups[(n.name, hashlib.md5(src.encode()).hexdigest()[:6])].append(f"{p}:{n.lineno}")
for (n, h), locs in sorted(groups.items()):
    print(n, h, len(locs))
    for loc in locs:
        print("   ", loc)
EOF

# Branch coverage of claude_code.py with/without a class
uv run pytest tests/unit/executors tests/integration -o addopts="" -q \
  --cov=adw.executors.claude_code --cov-branch --cov-report=term-missing \
  [--deselect tests/unit/executors/test_claude_code.py::TestAdditionalParsingCoverage]

# Lint gates (preflight covers src/ only)
scripts/preflight.sh && uv run ruff check tests/ && uv run ruff format --check tests/
```

## Uncertainty

- **Where `get_config_class` lives at implementation time:** `adw.commands.loader` today, and `adw.models.command` after phase 1.2. Resolved: import from whichever exists, per TASK-001's note.
- **Whether `TestHookRunnerTimeoutResolution` is still relevant** (the epic asks). Resolved: yes. `_resolve_timeout` is on the production path, and nothing else tests it. Phase 1.9 (B10) relies on this precedence when it wires `config.hooks`.
- **Whether any of `TestAdditionalParsingCoverage` is covered elsewhere.** Resolved by the coverage diff above: only `test_handles_json_array` is redundant.

## References

- [Epic 01, phase 1.4](../../epics/01-cleanup-safety-dead-code-bugs.md)
- [ADR-001 test reduction strategy](../../../architecture/adrs/ADR-001-test-reduction-strategy.md)
- [Plan 01.1](../01.1-isolate-test-suite/PLAN.md): introduced the root `isolated_home` fixture and the per-package `chdir` conftests.
