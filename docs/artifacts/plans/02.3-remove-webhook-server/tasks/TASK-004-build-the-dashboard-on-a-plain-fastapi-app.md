# TASK-004: Build the dashboard on a plain FastAPI app

Depends on: TASK-001
Suggested commit: `refactor(dashboard): build the app without the shared server factory`

## Goal

`src/adw/server/` is gone, `create_dashboard_app` builds `FastAPI(...)` itself, and `adw dashboard web --help` no longer mentions a webhook server.

## Files

- `src/adw/server/`: delete it all with `git rm -r`.
- `src/adw/dashboard/server.py`:
  - drop `from adw.server.app import create_app as _create_base_app` (`:19`)
  - replace the `_create_base_app(...)` call (`:70-78`) with `FastAPI(title="ADW Dashboard", description="Web dashboard for ADW run monitoring", version="0.1.0", lifespan=_dashboard_lifespan)`, followed by `app.state.dashboard_host = host` and `app.state.dashboard_port = port`
  - reword the module docstring so it no longer names the shared factory
- `src/adw/cli/dashboard_web.py`: delete the docstring sentence "The dashboard runs independently of the webhook server (port 8000) and both can run concurrently without conflicts." (`:64-65`).
- `tests/unit/server/`: delete it all with `git rm -r`.
- `tests/unit/dashboard/test_server.py`: delete `test_health_includes_request_id` (`:55-60`).

## Acceptance

- [ ] `grep -rn "adw.server\|RequestIDMiddleware\|x-request-id\|_create_base_app" src tests` returns nothing.
- [ ] `tests/unit/dashboard/test_server.py` passes unchanged apart from the deleted test: title, host/port state, `/health`, `/`, HTMX partial, static files and CSRF.
- [ ] `uv run adw dashboard web --help` has no "webhook".
- [ ] `uv run pytest tests/unit/dashboard tests/unit/cli/test_dashboard_web.py -o addopts=""` passes.

Evidence: the grep, the pytest tail, and `adw dashboard web --help | grep -ci webhook` printing `0`.

## Steps

### RED
- [ ] No new test. The existing `test_server.py` cases already pin the behaviour that must survive: the title, state, lifespan-backed start, the routes and CSRF. Delete `test_health_includes_request_id`, which pins the header this task removes, and run `test_server.py` once to record the baseline.

### GREEN
- [ ] `git rm -r src/adw/server tests/unit/server`.
- [ ] Rewrite the app construction in `dashboard/server.py`.
- [ ] Fix the `dashboard_web.py` docstring.
- [ ] Run the partial suite and confirm it is green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes, with no unused imports left behind.

## Notes

- Leave the lifespan banner alone; phase 2.11 deletes it.
- `FastAPI` is already imported in `dashboard/server.py` for type hints.
