# TASK-001: Build HookRunner from project.yaml hooks config

Depends on: None
Suggested commit: `fix(hooks): build the hook runner from project.yaml hooks config`

## Goal

`hooks.timeout_seconds` and `hooks.shell` from `.adw/project.yaml` reach the `HookRunner` that every phase uses (B10).

## Files

- `src/adw/cli/bootstrap.py:241`: `hook_runner = HookRunner(config=config.hooks if config else HookConfig())`. `HookConfig` stays imported for the fallback.
- `tests/unit/cli/test_bootstrap.py`: add `TestBootstrapHookWiring::test_runner_uses_project_hook_config`.
- `tests/integration/core/test_hook_config.py` (new): `test_project_hook_timeout_stops_post_hook`.
- `docs/architecture/deep-dive/phase-runner.md`: under hook execution, one line saying that the timeout and shell come from `project.yaml`'s `hooks:` (defaults: 60 s, `/bin/bash`).

## Acceptance

- [ ] `test_runner_uses_project_hook_config`:
  - Setup: in `tmp_path` (the cli conftest already chdirs there), write `.adw/project.yaml` with `name: demo`, `language: python` and `hooks: {timeout_seconds: 5, shell: /bin/sh}`, then call `create_orchestrator(with_progress=False)`.
  - Assert: `orchestrator._phase_runner.hook_runner.config == HookConfig(timeout_seconds=5, shell="/bin/sh")`.
- [ ] `test_project_hook_timeout_stops_post_hook`:
  - Setup:
    - In `git_repo`, commit these files:
      - `.adw/project.yaml`, with `worktree: {enabled: false}` and `hooks: {timeout_seconds: 1}`
      - `.adw/commands/plan/post.sh` containing `exec sleep 10`
      - `.gitignore` with `home/` and `.adw/runs/`
    - `monkeypatch.chdir(git_repo)`.
  - Run `create_orchestrator(with_progress=False).run_single_phase("plan", "timeout check", use_worktree=False)`.
  - Assert: it raises `HookError` with `code == "HOOK_TIMEOUT"`, and `time.monotonic()` measures the whole call at under 5 s.
- [ ] Both tests fail on today's code: the config comparison, and the timing (about 10 s).

Evidence:
- the RED run: the equality fails, and the integration test takes ~10 s, or times out at the 60 s default if the hook ignores the kill
- the GREEN run, including `--durations=5` output showing the integration test at about 1 s

## Steps

### RED
- [ ] Write `test_runner_uses_project_hook_config` next to `TestBootstrapShipWiring`, following its pattern with a real `project.yaml`.
- [ ] Write `test_project_hook_timeout_stops_post_hook` in a new `tests/integration/core/test_hook_config.py`, copying the fixture shape of `retry_project` in `tests/integration/core/test_phase_failure.py`: committed config, gitignored `home/` and `.adw/runs/`, and `monkeypatch.chdir`.
- [ ] Run both, and confirm the first fails and the second takes about 10 s and then fails its timing assertion.

### GREEN
- [ ] Change `bootstrap.py:241`.
- [ ] Run both tests green.

### REFACTOR
- [ ] Update the phase-runner deep-dive line.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `HookError` is `recoverable=False`, so the orchestrator's retry loop does not re-run a timed-out phase. The 5 s bound therefore holds for the whole call.
- The integration test uses the plan phase. Until TASK-003 deletes it, the bundled `plan/pre.sh` still runs first under pytest's venv `python3`. It needs a clean tree, which is why the committed `.gitignore` is there.
- The mocked `ProjectConfig`s in `test_bootstrap.py` (`MagicMock(spec=ProjectConfig)`) now pass a `MagicMock` as `hooks`. Nothing runs a hook in those tests, so they stay green. Don't add `hooks` to them.
