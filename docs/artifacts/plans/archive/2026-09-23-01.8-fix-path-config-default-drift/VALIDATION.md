# Validation: Fix path, config and default drift

Validated: 2026-09-23 at `5e6ea3bc`. CI is green on the final task commit of PR #204. The TASK-003 and TASK-004 pushes went red on one integration test; `cb5f1c8b` fixed it (see TASK-003 below).

| Criterion | Result |
|---|---|
| Log search returns entries and the SSE log stream emits `live.log` lines for a real run | Met: 327 entries, `event:log-line` stream, below |
| `build_command: "echo built"` reaches the ship post-hook as `ADW_SHIP_BUILD_CMD` | Met: bootstrap wiring test, plus `ship-env.txt` from a mocked `adw run --phase ship` |
| `adw init --no-interactive` then `adw validate` passes in a scratch repo | Met: `0 errors, 0 warnings` |
| A wizard-generated `project.yaml` maps `ship` | Met: `test_accepted_defaults_yield_ship_mapping` |
| An `interrupted` run closes both SSE streams | Met: RED 2 s timeout → GREEN 0.04 s; real-run `curl` exits in 0.06–0.07 s |
| Run-detail cost equals analytics cost | Met: `test_run_detail_cost_matches_analytics`; real run `$1.21` on both pricing paths |
| Plan-level greps | Met, below |
| `scripts/preflight.sh`; `uv run pytest` green, coverage ≥ 80% | Met: 4297 passed, 5 skipped, 84.70% |

## Suite and lint

```
$ scripts/preflight.sh
==> ruff check        All checks passed!
==> ruff format --check   166 files already formatted
==> mypy              Success: no issues found in 166 source files
preflight: ok

$ uv run pytest
Required test coverage of 80% reached. Total coverage: 84.70%
== 4297 passed, 5 skipped in 211.16s (0:03:31) ==
```

## Greps

```
$ grep -rn '"In Review"' src/adw --include='*.py'
src/adw/models/config.py:365:    "validate": "In Review",        # DEFAULT_STATE_MAPPING
src/adw/models/config.py:366:    "document": "In Review",
src/adw/models/config.py:403:            validate: "In Review"   # TaskManagerConfig docstring example
src/adw/models/config.py:404:            document: "In Review"

$ grep -rn "0.000009\|_load_project_build_command\|DEFAULT_CONFIG_TEMPLATE\|DEFAULT_STATE_MAPPINGS" src
(empty)
$ grep -rn '"logs" / "live.log"' src
(empty)
$ grep -rnF '"live.log"' src/adw --include='*.py'
src/adw/core/constants.py:30:LIVE_LOG = "live.log"
$ grep -rn '".adw" / "runs"' src/adw/dashboard
(empty)
$ grep -c 'in TERMINAL_STATUSES' src/adw/dashboard/routes.py
2
$ grep -rn "def generate_gitignore\|def generate_env_template" src
src/adw/config/initializer.py:18:def generate_gitignore() -> str:
src/adw/config/initializer.py:35:def generate_env_template() -> str:
```

TASK-001's `grep -rn '"live.log"'` also matches `export_data["live_log"]` in `cli/logs.py`, because `.` is a regex wildcard. The fixed-string grep above is the intended check.

## RED → GREEN per task

| Task | RED on the unfixed code | GREEN |
|---|---|---|
| 001 live.log path (B4) | 8 failed: the 6 moved `_load_log_entries` fixtures and `test_reads_log_written_by_run` get `[]`; `test_log_stream_emits_live_log_lines` gets an empty body | 9 passed; task suites 736 passed |
| 002 ship build command (B3) | `TypeError: ShipExtension.__init__() got an unexpected keyword argument 'build_command'`; `KeyError: 'ADW_SHIP_BUILD_CMD'` | 254 passed (ship, bootstrap, orchestrator) |
| 003 minimal init (B11) | both new tests: `Value error, Missing required fields: name` | 573 passed (config, init, wizard) |
| 004 state mapping (B17) | `KeyError: 'ship'` on the loaded config | 1581 passed (wizard, task managers, config, dashboard) |
| 005 terminal statuses (B21) | both new tests: `TimeoutError` after 2.03 s and 2.00 s | 2 passed in 0.22 s (0.04 s call); dashboard 691 passed |
| 006 run-detail cost | `AttributeError: … no attribute 'get_phase_token_usage'` ×2; `'$3.00' not in` and `'$1.37' not in` the run-detail page | 904 passed (dashboard, stats aggregator) |

## Real run: log search and live stream (B4)

Dashboard started from this worktree against the real `~/.adw` index: `uv run adw dashboard web --port 8765 --no-browser`. Run `01KHAPGM6PRX55TZQF5V082DDH` (ADW-36) lives in the main checkout's `.adw/runs`, and its `live.log` has 1615 lines. The server was stopped afterwards; only GET requests were made.

- `GET /runs/<id>/logs` (HX-Request) renders **327 log entries**. `?q=Token` returns the five `Token stream begins (plan|build|validate|document|ship)` lines. Before this change, `_load_log_entries` read `runs/<id>/logs/live.log`, which no real run has, and returned nothing.
- Live stream:

```
$ curl -sN --max-time 10 http://127.0.0.1:8765/runs/01KHAPGM6PRX55TZQF5V082DDH/logs/stream | head -20
event:log-line
data:<div class="py-0.5">… <span class="font-semibold">INFO</span> 46c35e71 docs(story-ADW-36): add feature documentation and update conditional docs</div>

event:log-line
data:<div class="py-0.5">… <span class="font-semibold">INFO</span> e743c2e0 test(story-ADW-36): add tests for changed-count badges and indicators</div>
…  (7 log-line events in the first 20 lines)
```

Screenshots of `/runs/<id>` and `/runs/<id>/logs` were taken with headless Chrome, because the Chrome extension was not connected. They are kept out of the repo, which is public, because the log page is full of local absolute paths. The run-detail shot shows the pipeline, Tokens `101K`, Cost `$1.21`, and phase costs `$0.25 / $0.60 / $0.25 / $0.05 / $0.07`.

## Interrupted run closes both streams (B21)

The same real run was copied into a scratch project with `context.json` `status` set to `interrupted`. A second dashboard, on port 8766 with a temp `HOME`, had a one-entry `index.jsonl` for it.

```
$ curl -sN --max-time 15 http://127.0.0.1:8766/runs/01KHAPGM6PRX55TZQF5V082DDH/events
curl exit=0 (0 = server closed the stream; 28 = our 15 s timeout)  elapsed=0.06s
events: 1 event:phase-update  1 event:run-failed

$ curl -sN --max-time 15 http://127.0.0.1:8766/runs/01KHAPGM6PRX55TZQF5V082DDH/logs/stream
curl exit=0 (0 = server closed the stream; 28 = our 15 s timeout)  elapsed=0.07s
events: 151 event:log-line
```

## Ship hook env (B3)

A scratch git repo with a temp `HOME` and no `.adw/commands/ship/config.yaml` exercises B3's early-return case.

- `.adw/project.yaml`: `name: demo`, `language: python`, `build_command: "echo built"`. `ProjectConfig` requires `language` as well as `name`.
- A project-tier `.adw/commands/ship/post.sh`: `env | grep '^ADW_SHIP_' | sort > ship-env.txt`. It runs after the bundled ship post-hook.
- The bundled ship pre-hook needs a PR, and auto-PR needs a pushed branch, so the repo got:
  - a local bare repo as `origin`
  - a fake `gh` on `PATH` that answers `auth status`, `pr create` (prints `https://example.invalid/pr/1`) and `pr view`, and refuses everything else

  The mocked ship output carries no `PR_MERGE_APPROVED: true`, so nothing is merged.
- `ADW_MOCK_EXECUTOR=1 adw run --no-worktree "noop"` builds the source run. Its document phase leaves ship skipped, because the mock's document output is not a parseable PR description.
- `adw run --phase ship --from-run <that run> --no-worktree` then runs ship:

```
exit=0
$ cat ship-env.txt
ADW_SHIP_BUILD_CMD=echo built
```

On the old code, `get_hook_env` returned `{}` whenever the ship config was absent, and the build command was read from `<root>/project.yaml`.

## Init + validate (B11)

Fresh scratch git repo with a `pyproject.toml` and a temp `HOME`:

```
$ adw init --no-interactive
… ADW initialized …
$ grep '^name:' .adw/project.yaml
name: init-demo
$ adw validate
  .adw/project.yaml ....................... OK
  plan / build / validate / document / ship  OK
  Result: 0 errors, 0 warnings — configuration is valid
```

## Cost agreement

- `test_run_detail_cost_matches_analytics`: one registered project, one run, and two response files carrying `total_cost_usd` 0.42 and 0.95. Both `GET /runs/<id>` and `GET /analytics` show `$1.37`. The old formula would have shown `$0.61` for that run's 68,244 context tokens.
- Real run `01KHAPGM6PRX55TZQF5V082DDH`: its project has many runs, so the analytics project row can't be compared one to one. The analytics pricing path, `calculate_cost(_parse_llm_response_files(run_dir))`, gives `$1.21` (25,578 in, 75,628 out, no `actual_cost_usd`). That is the run-detail value shown above. The old formula gave `$0.91`.

## Where the implementation differs from the plan

- **Branch.** The plan uses the worktree's own branch, `feature/adw-14`, fast-forwarded to `origin/staging`. That follows phase 1.1, which used `feature/adw-7`.
- **TASK-002.**
  - The wiring test's `project.yaml` also sets `language`.
  - Six existing bootstrap tests use `MagicMock(spec=ProjectConfig)`, and those mocks needed `build_command = None`.
- **TASK-003.**
  - `test_yaml_generator.py:193` asserts the phase-config header, which stays, so it was left as is.
  - `cli/wizard/__init__.py` now imports `generate_gitignore` from `adw.config.initializer`. mypy `--strict` rejects the implicit re-export through `summary.py`.
  - CI caught `tests/integration/cli/test_init_integration.py::test_generated_config_has_test_command`. A generic project's unset `test_command` is now commented out rather than written as an empty key. The test now uses a Python project and asserts `pytest` (`cb5f1c8b`).
- **TASK-004.**
  - `test_state_mapping_with_custom_values` also feeds 6 prompts now.
  - A `sync.py` docstring that said runs rest at "In Review" now says `ship -> Done`.
- **TASK-005.** An `AsyncMock` sleep never yields to the event loop, so `wait_for` could not fire and the RED run hung. The tests patch `asyncio.sleep` with a zero-delay real sleep instead.
- **TASK-006.**
  - `mutations.abort_run` is a second caller of `_build_run_detail_context`, so it also takes `stats_aggregator` through `Depends`.
  - The mock aggregators in four dashboard test helpers return `{}` / `0.0`: `test_run_detail`, `test_active_failed_runs`, `test_abort` and `test_mutations`.
  - `sum_token_usage()` in `stats_aggregator` is the one field-wise sum, used by `_parse_llm_response_files` and run detail.
