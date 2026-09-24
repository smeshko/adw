# Acceptance greps (branch feature/adw-23)

```
$ rg -U 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src
(exit 1)

$ rg -l 'import subprocess' src
src/adw/core/run_trigger.py
src/adw/git.py
(exit 0)

$ ls src/adw/hooks src/adw/worktree | grep -v __pycache__
src/adw/hooks:
__init__.py
environment.py
runner.py

src/adw/worktree:
__init__.py
concurrent.py
manager.py
(exit 0)

$ rg -n 'def _?(format_(duration|elapsed|tokens|cost|size|file_size|relative_time|duration_ms|duration_from_seconds)|relative_time)\b' src
src/adw/format.py:42:def format_duration(seconds: float | None) -> str:
src/adw/format.py:59:def format_tokens(count: int) -> str:
src/adw/format.py:78:def format_relative_time(when: datetime | None, *, now: datetime | None = None) -> str:
src/adw/format.py:102:def format_cost(amount: float) -> str:
src/adw/format.py:109:def format_size(size_bytes: int) -> str:
(exit 0)

$ rg -n 'STATUS_COLORS|STATUS_ICONS|_get_status_style' src
(exit 1)

$ rg -n ':,?\.2f\}' src
src/adw/format.py:105:        return f"-${-amount:,.2f}"
src/adw/format.py:106:    return f"${amount:,.2f}"
(exit 0)

$ rg -n 'badge-(warning|success|error|ghost)' src/adw/dashboard/templates/components/status_badge.html
(exit 1)

$ rg -n --type py "status[\"']?\]?\s*(==|!=|=|:)\s*[\"'](running|completed|failed|interrupted|aborted)[\"']" src | rg -v 'phase_status|phase\["status"\]|>>>|description='
(exit 1)

$ rg -n --type py "[(\[{]\s*[\"'](running|completed|failed|interrupted|aborted)[\"']\s*," src
(exit 1)

$ rg -n 'status: RunStatus' src/adw/models
src/adw/models/context.py:71:    status: RunStatus = Field(
src/adw/models/index.py:56:    status: RunStatus = Field(..., description="Current run status")
(exit 0)

$ rg -n 'os\.fsync|\.tmp"|\.rename\(' src
src/adw/fs.py:21:    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
src/adw/fs.py:29:            os.fsync(f.fileno())
(exit 0)

$ rg -n 'atomic_write\(' src | rg -v 'def |atomic_write_config'
src/adw/core/run_directory.py:111:                atomic_write(context_path, context.model_dump_json(indent=2))
src/adw/core/artifact_manager.py:74:            atomic_write(artifact_path, content)
src/adw/core/index_manager.py:413:        atomic_write(
src/adw/cli/wizard/summary.py:329:            atomic_write(full_path, content)
src/adw/cli/wizard/summary.py:339:                atomic_write(path, original_content)
src/adw/core/snapshot_manager.py:193:            atomic_write(snapshot_path, snapshot.model_dump_json(indent=2))
src/adw/core/project_registry.py:299:        atomic_write(
src/adw/core/context_manager.py:83:                atomic_write(context_path, context.model_dump_json(indent=2))
(exit 0)

$ rg -n '/ "runs"' src
src/adw/core/constants.py:42:    return project_root / ".adw" / "runs"
(exit 0)

$ rg -n 'VALID_STATUSES|AVAILABLE_PHASES|canonical_phases' src tests
(exit 1)

$ rg -n 'get_runs_dir|_get_runs_dir' src tests
(exit 1)

```
