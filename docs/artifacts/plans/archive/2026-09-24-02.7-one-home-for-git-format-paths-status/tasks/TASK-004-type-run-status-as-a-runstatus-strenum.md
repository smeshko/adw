# TASK-004: Type run status as a RunStatus StrEnum

Depends on: None
Suggested commit: `refactor(models): type run status as a RunStatus StrEnum`

## Goal

Run status is one `RunStatus` StrEnum. `RunContext`, `IndexEntry`, every status write and every CLI and dashboard status set in `src` use it, and `PHASE_SEQUENCE` replaces the last two hand-written phase lists. Serialised JSON (`context.json`, `index.jsonl`, `--json` output) is unchanged.

## Files

- `src/adw/models/context.py`:
  - `class RunStatus(StrEnum)` with `RUNNING = "running"`, `COMPLETED`, `FAILED`, `INTERRUPTED`, `ABORTED`.
  - `RunContext.status: RunStatus = Field(default=RunStatus.RUNNING, …)`.
  - Fix the docstring's `status:` line, which lists only three values.
  - Export `RunStatus` from `models/__init__.py` next to `RunContext`.
- `src/adw/models/index.py`: `IndexEntry.status: RunStatus`, imported from `adw.models.context`.
- `src/adw/core/constants.py`: `TERMINAL_STATUSES: frozenset[RunStatus] = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.ABORTED, RunStatus.INTERRUPTED})`.
- Status writes use members. `model_copy(update={"status": …})` skips validation, so a plain string would stay a `str` in the field and make pydantic warn at serialisation:
  - `core/interruption.py`: `:165`, `:211`, `:273`
  - `core/run_lifecycle.py`: the 12 sites (`:209`, `:316`, `:329`, `:345`, `:395`, `:408`, `:415`, `:454`, `:467`, `:474`, `:517`, `:692`), including the `update_run(status=…)` calls
  - `core/orchestrator.py`: `:406`, `:415`, `:610`, `:639`, `:648`
  - `core/resume_manager.py`: `:94`, `:116`, `:253`, `:256`, `:298`
  - `core/index_manager.py:99`
  - `dashboard/mutations.py`: `:231`, `:259`, `:285` (drop the `# type: ignore[assignment]`) and `:292`
  - `cli/global_commands.py:859`
- `IndexManager.update_run` (`core/index_manager.py:110`–`:158`) validates its updates: `IndexEntry.model_validate({**entry.model_dump(), **updates})` replaces `entry.model_copy(update=updates)`.
  - A plain `status="completed"` from any caller becomes a member instead of a raw `str`.
  - An invalid value raises `ValidationError` instead of being written.
  - It is the one write path callers reach with `**Any`, which mypy can't check (validation round 1, #2).
- Status comparisons and sets use members. A member catches a typo where a string literal can't, and the acceptance grep checks all of them at once (round 1, #11 rejected the narrower "sets only" scope):
  - `core/run_lookup.py:98`: `incomplete_statuses = frozenset({RunStatus.RUNNING, RunStatus.FAILED, RunStatus.INTERRUPTED})`
  - `cli/global_commands.py:751`: `entry.status != RunStatus.RUNNING`
  - `core/stats_aggregator.py`: `:440`, `:441`, `:450`, `:463`, `:464`, `:472`, `:523`, `:525`
  - `cli/list.py:26` and `cli/global_commands.py:30`: delete `VALID_STATUSES`. Validate `--status` with `status not in RunStatus` (a StrEnum supports `in` on values in 3.13), and list the valid values as `", ".join(RunStatus)`.
  - `cli/pr.py:175`, `cli/abort.py:57`, `:66`, `cli/status_display.py:104`
  - `cli/logs.py` (`:581`, `:605`, `:622`) reads raw JSON: compare with `RunStatus.RUNNING` and keep the `""` fallback.
  - `dashboard/routes.py`: the `("failed", "aborted")` tuples at `:458`, `:630`, `:670` become one module-level `_FAILED_STATUSES = frozenset({RunStatus.FAILED, RunStatus.ABORTED})`, plus the run-level literals at `:98`, `:205`, `:456`, `:614`, `:628`, `:695`, `:986`, `:1438`
  - `dashboard/partials.py`: `:76`, `:754`, `:869`, `:887`, `:949`, `:1090`, `:1103`
  - `dashboard/partials.py:663`: the local `status = "completed"` is a phase-pipeline status, not a run status. Rename it to `phase_status` to match `routes.py`, which puts it outside the grep.
  - Prose that the grep would otherwise catch: run_lookup.py:86, snapshot_manager.py:122, index_manager.py:77 and partials.py:688. Reword these docstrings to name `RunStatus` members, e.g. "`RunStatus.COMPLETED` runs", instead of quoting `status="completed"`.
    - `partials.py:657`'s docstring tuple becomes prose as well.
    - The `models/index.py:39` docstring example writes `status=RunStatus.RUNNING`.
  - `run_lifecycle.py:345`, `:415` and `:474` pass `status="…"` to `_show_pipeline_summary`, and `partials.py:76` passes it to `get_recent_runs`. These pass members too.
  - Leave `cli/progress.py`'s colour chain to TASK-006.
- Phase lists:
  - `cli/wizard/phases.py:16`: delete `AVAILABLE_PHASES` and use `PHASE_SEQUENCE` (import from `adw.core.constants`) at `:80`, `:473`, `:485`, `:486` and `:492`. `:473` returns `list(PHASE_SEQUENCE)`, because callers and tests compare against lists and `PHASE_SEQUENCE` is a tuple.
  - `dashboard/partials.py:343`: delete `canonical_phases` and use `PHASE_SEQUENCE`.
  - `cli/app.py:177`: the `--phase` help reads `f"Execute single phase only ({', '.join(PHASE_SEQUENCE)})"`. It lists four phases today, but `validate_phase` accepts all five.
- Tests:
  - `tests/unit/models/test_context.py` (or the existing context test module):
    - Add `test_context_json_status_round_trips`: a `context.json` string as written today (`"status": "interrupted"`) loads through `RunContext.model_validate_json` and gives `status is RunStatus.INTERRUPTED`. `json.loads(ctx.model_dump_json(indent=2))["status"] == "interrupted"`. Compare parsed JSON, because unindented `model_dump_json()` writes no spaces.
    - Add `test_status_rejects_unknown_value`: `RunContext(..., status="paused")` raises `ValidationError`.
  - `tests/unit/core/test_index_manager.py`: add `test_update_run_validates_status`.
    - `update_run(run_id, status="completed")` stores `RunStatus.COMPLETED`, with no warning under the `-W` filter below.
    - `update_run(run_id, status="paused")` raises `ValidationError` and leaves the index unchanged.
  - Test-side string writes that bypass validation become members. These are the `model_copy(update={"status": …})` calls:
    - `tests/unit/core/test_resume_manager.py:125`
    - `tests/unit/cli/test_abort.py:66`
    - `tests/integration/core/test_interruption_integration.py:112`, `:171` and `:352`
    - `tests/integration/core/test_orchestrator_integration.py:356`

    The last four are multi-line and are followed by a real save, which warns (validation round 2, #5). `rg -U -n 'model_copy\(\s*update=\{[^}]*"status":\s*"' tests` finds them all. It may also list sites that never serialise: `test_context.py:382`, `test_index.py:264`, and `test_resume_manager.py:284` and `:344`. Convert those too, for consistency. The 16 `update_run(..., status="…")` calls in tests (`test_index_manager.py`, `test_global_commands_integration.py`, `test_feature_description.py:202`) can stay, because `update_run` now validates.
  - `tests/unit/cli/wizard/test_phases.py:32`: delete the assertion of the exact `AVAILABLE_PHASES` list (an ADR-001 enum-existence test). Point its other uses at `list(PHASE_SEQUENCE)`: `:14`, `:68` and `:133`–`:135`.
  - Update any test that imports `VALID_STATUSES` or asserts the old `Valid values:` order. `rg -n "VALID_STATUSES|AVAILABLE_PHASES|canonical_phases" tests` finds them.

## Acceptance

- [ ] `RunContext.status` and `IndexEntry.status` are `RunStatus`. `test_context_json_status_round_trips` and `test_status_rejects_unknown_value` pass.
- [ ] These print nothing, apart from `cli/progress.py:309`–`:313`, which TASK-006 replaces. The first covers writes and `==`/`!=` comparisons; the second covers hand-written tuples and sets:
  - `rg -n --type py "status[\"']?\]?\s*(==|!=|=|:)\s*[\"'](running|completed|failed|interrupted|aborted)[\"']" src | rg -v 'phase_status|phase\["status"\]|>>>|description='`
  - `rg -n --type py "[(\[{]\s*[\"'](running|completed|failed|interrupted|aborted)[\"']\s*," src`
- [ ] `rg -n "VALID_STATUSES|AVAILABLE_PHASES|canonical_phases" src tests` prints nothing, and `rg -U -n 'model_copy\(\s*update=\{[^}]*"status":\s*"' tests` prints nothing.
- [ ] `uv run pytest tests/unit tests/integration -o addopts="" -q -W "error:Pydantic serializer warnings"` passes. The filter matches the warning message; a module filter is regex-escaped by pytest and never matches (round 1, #2). Positive control, recorded in the evidence and not committed: temporarily revert `interruption.py:165`'s `RunStatus.ABORTED` to `"aborted"`, show that `tests/integration/cli/test_abort_integration.py` fails under the filter, then restore it. The other `interruption.py` writes save inside `except Exception: pass`, so they can't serve as a control.
- [ ] `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_context_json_status_round_trips` (`ImportError: RunStatus`). `test_status_rejects_unknown_value` passes before and after, since the `Literal` already rejects `"paused"`; it guards the switch. Then the GREEN pytest tail with warnings as errors, the `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Add the two context tests and `test_update_run_validates_status`; run them: the round-trip test fails importing `RunStatus`, and the `update_run` test stores a raw `"paused"`.

### GREEN
- [ ] Add `RunStatus`, and type `RunContext` and `IndexEntry` with it; retype `TERMINAL_STATUSES`.
- [ ] Replace every status write, comparison and set listed above; replace the two phase lists and the help text.
- [ ] Update the tests found by `rg`; run the suite with pydantic warnings as errors: green.

### REFACTOR
- [ ] Re-run both `rg` checks; `scripts/preflight.sh` passes.

## Notes

- `str(RunStatus.RUNNING)` and f-strings give `"running"`: StrEnum's `__str__` is the value, unlike the `(str, Enum)` style of `PhaseStatus`. Rich markup such as `f"[{color}]{status}[/]"` is unchanged.
- `json.dumps(entry.model_dump())` keeps working, because a StrEnum member is a `str`. `model_dump_json()` writes the value.
- `IndexManager.get_recent_runs(status: str | None)` keeps its `str` parameter. Comparing it with a `RunStatus` field works on values.
- The warnings-as-errors run can miss a string write inside an `except Exception` block (`phase_runner.py:1217`, `ExtensionRegistry`), because the raised warning is swallowed there. The plain full suite's "no warnings" summary line stays the final gate (TASK-009).
