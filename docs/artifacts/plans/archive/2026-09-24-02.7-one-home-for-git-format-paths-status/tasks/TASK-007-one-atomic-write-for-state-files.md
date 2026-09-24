# TASK-007: One atomic_write for state files

Depends on: None
Suggested commit: `refactor(fs): one atomic_write for run and user state files`

## Goal

One `atomic_write(path, data)` replaces the three temp-then-rename copies. It is also used for the state files that are written in place today: the first `context.json`, `~/.adw/index.jsonl`, `~/.adw/projects.yaml` and the wizard's files. A write that fails partway leaves the old file intact and no temp file behind.

## Files

- `src/adw/fs.py` (new): `atomic_write(path: Path, data: str | bytes) -> None`.
  - It creates the temp file itself: `tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")`, then `fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)`.
    - The kernel applies the umask, so a new file gets the usual 0644.
    - `tempfile.NamedTemporaryFile` / `mkstemp` would create 0600 files, and `os.replace` would carry that mode onto `project.yaml`, `context.json` and `~/.adw/*` (validation round 1, #7).
  - It wraps the descriptor at once with `with os.fdopen(fd, "wb") as f:`, so it is closed on every path.
  - When `path` already exists, it calls `os.fchmod(f.fileno(), stat.S_IMODE(path.stat().st_mode))`, so a replaced file keeps its mode.
  - It writes `data`, encoding `str` as UTF-8, then flushes and calls `os.fsync(f.fileno())`.
  - Then it calls `os.replace(tmp, path)`.
  - On any exception (`BaseException`, so a Ctrl+C mid-write cleans up too) it unlinks the temp file with `missing_ok=True` and re-raises.
  - The parent directory must exist; callers already ensure that.
  - A symlinked target is replaced by a regular file, as with any rename-based write (PLAN.md Out of Scope).
- `src/adw/core/context_manager.py` (`save`, `:58`–`:112`): inside the existing `FileLock`, call `atomic_write(context_path, context.model_dump_json(indent=2))`. Keep `RUN_DIR_NOT_FOUND`, `LOCK_TIMEOUT` and `OSError` → `CONTEXT_WRITE_FAILED`. Delete the fixed `.context.json.tmp` path and its cleanup; `atomic_write` cleans up.
- `src/adw/core/snapshot_manager.py` (`_create_snapshot`, `:188`–`:209`): `atomic_write(snapshot_path, …)`, keeping `SNAPSHOT_WRITE_FAILED` and the slow-write warning.
- `src/adw/core/artifact_manager.py` (`store`, `:45`–`:92`): `atomic_write(artifact_path, content)` for `str` and `bytes` alike, keeping `ARTIFACT_WRITE_FAILED`. `store_json` goes through `store` unchanged.
- `src/adw/core/run_directory.py:106`–`:109`: the first `context.json` goes through `atomic_write`, and the literal `"context.json"` at `:89` becomes `CONTEXT_FILE`.
- `src/adw/core/index_manager.py:402`–`:410` (`_write_all_entries`): `atomic_write(self.index_path, "".join(e.model_dump_json() + "\n" for e in entries))`.
- `src/adw/core/project_registry.py:284`–`:299` (`_save_registry`): `atomic_write(self.registry_path, yaml.safe_dump(data, default_flow_style=False, sort_keys=False))`, keeping the `mkdir`.
- `src/adw/cli/wizard/summary.py` (`atomic_write_config`, `:289`–`:355` since #212): each file's `path.write_text(content)` becomes `atomic_write(path, content)`, at `:329`, and the restore at `:339`. The backup, restore and new-directory cleanup stay as they are, because they make the set of files transactional. The docstring says each file is replaced atomically and the set is rolled back as a whole.
- Tests:
  - `tests/unit/test_fs.py` (new):
    - `test_atomic_write_creates_and_replaces`: `str` and `bytes` round-trip, and an existing file is replaced.
    - `test_failed_write_keeps_the_old_file_and_leaves_no_temp`: patch `adw.fs.os.fsync` to raise `OSError`. The original content survives, and `list(tmp_path.iterdir())` holds only the target.
    - `test_failed_replace_keeps_the_old_file_and_leaves_no_temp`: patch `adw.fs.os.replace` to raise. Same assertions.
    - `test_keyboard_interrupt_mid_write_cleans_up`: `fsync` raises `KeyboardInterrupt`. The temp file is gone, and the exception propagates.
    - `test_atomic_write_keeps_the_existing_mode`: a target at 0640 is still 0640 after the replace.
    - `test_new_file_gets_the_umask_default`: under `os.umask(0o022)` (restored in `finally`), a new file is 0644.
  - `tests/unit/core/test_context_manager.py`: these tests pin today's mechanism:
    - the `Path.rename` count and the `.context.json.tmp` name at `:86`–`:92`
    - the rename-failure injection at `:348`–`:383`
    - the `os.fsync` call count at `:112`
    - the `builtins.open` temp-name match at `:450`–`:470`
    - the temp cleanup at `:159`, `:399` and `:423`

    They become behaviour tests: a failing `adw.fs.os.replace` leaves the old `context.json` intact, raises `CONTEXT_WRITE_FAILED`, and leaves no `*.tmp` in the run dir. Keep the lock tests (`:268`–`:337`).
  - `tests/unit/core/test_artifact_manager.py:368`–`:393`: `atomic_write` opens through `os.open` / `os.fdopen`, which bypass a patched `builtins.open`. Inject the failure with `patch("adw.fs.os.fsync", side_effect=OSError("disk full"))`, and still expect `ARTIFACT_WRITE_FAILED`.
  - `tests/unit/cli/wizard/test_summary.py` (`:465`, `:501`): the `patch.object(Path, "write_text", failing_write_text)` injections become a patch of `adw.cli.wizard.summary.atomic_write`.
    - The patch wraps a counter: only the second call raises `OSError("disk full")`. Every other call, including the rollback's restore write at `summary.py:339`, delegates to the real `adw.fs.atomic_write`.
    - The first file is really written, so the backup and restore path runs.
    - A bare `side_effect=[None, OSError]` would skip the first write and pass vacuously (validation round 1, #8).
    - The rollback assertions stay.
  - `tests/unit/core/test_index_manager.py` and `tests/unit/core/test_project_registry.py`: add `test_rewrite_failure_keeps_the_index` and `test_save_failure_keeps_the_registry`.
    - The index test patches `IndexEntry.model_dump_json` to raise on the second entry during `update_run`.
    - The registry test patches `yaml.safe_dump` in `adw.core.project_registry` to raise during `register`.
    - In both, the file on disk keeps its previous content.

## Acceptance

- [ ] `rg -n 'os\.fsync|\.tmp"|\.rename\(' src` prints only `src/adw/fs.py`.
- [ ] `rg -n 'atomic_write\(' src | rg -v 'def |atomic_write_config'` shows the seven call sites listed above, plus `summary.py`'s restore.
- [ ] The `test_fs.py`, context-manager, index and registry failure tests pass: a failed write leaves the old file intact and no temp file. The mode tests pass.
- [ ] `uv run pytest tests/unit/core tests/unit/cli/wizard tests/unit/test_fs.py tests/integration -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures (`ModuleNotFoundError: adw.fs`; the index and registry tests lose the file today, because `open("w")` truncates it before writing), then the GREEN tail, the `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Write `tests/unit/test_fs.py` and the index and registry failure tests; run them: they fail.

### GREEN
- [ ] Write `src/adw/fs.py`.
- [ ] Switch the seven callers; delete the three hand-rolled temp-then-rename blocks.
- [ ] Rewrite the mechanism-pinning context-manager tests as behaviour tests, and move the wizard failure injection to `atomic_write`; run the partial suite: green.

### REFACTOR
- [ ] Re-run the `rg` checks; `scripts/preflight.sh` passes.

## Notes

- The index and registry RED tests fail today because `open("w")` truncates the file before the serialiser raises. After the change the content is serialised before `atomic_write` touches the disk, so the old file survives.
- `atomic_write` uses `os.replace`, not `Path.rename`. Both are atomic on POSIX, and `os.replace` also overwrites on Windows.
- It doesn't fsync the parent directory (out of scope). A power loss right after the replace can still lose the rename, but never leaves a torn file.
