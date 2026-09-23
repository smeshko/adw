# Decisions — 01.5 Dependencies, tooling and repo hygiene

## 1. `uvicorn[standard]` → `uvicorn`

Date: 2026-09-23

### Options Considered

1. Plain `uvicorn`: drop the `standard` extra.
2. Keep `uvicorn[standard]`.

### Dependencies

- The extra adds `httptools`, `uvloop`, `watchfiles` and `websockets`. Nothing else in `uv.lock` depends on them, and nothing in `src` imports them.
- The dashboard streams SSE through `StreamingResponse` over plain HTTP, so it needs no websockets.
- `reload=True` is the only uvicorn feature beyond `run()` that ADW uses: `adw dashboard web --reload` and `adw webhook … --reload`. Without `watchfiles`, uvicorn 0.40 falls back to `StatReload`.

### Selected Option

Option 1.

### Rationale

Four compiled dependencies buy faster file-watching on a dev-only `--reload` flag and a faster HTTP parser for a local dashboard. Neither is worth the install weight. Reload keeps working, only by polling.

### Rejected Options

- Option 2: carries four unused-by-default dependencies to keep a marginal reload speed-up.

## 2. Replace `update.sh` with a thin uv wrapper

Date: 2026-09-23

### Options Considered

1. Delete `update.sh`, and document `uv version --bump major|minor|patch` and `uv tool install --editable .` in `AGENTS.md`.
2. Replace it with a thin script, `scripts/bump.sh`, that runs `uv version --bump`, then commits `pyproject.toml` and `uv.lock`, with no push and no install.

### Dependencies

- `update.sh` bumps only `pyproject.toml`, so `uv.lock` keeps the old `adw` version. It also pushes directly, bypassing PR and CI, and runs `pip install -e .` into whatever pip is first on PATH.
- The repo has 65 `chore: bump version to X` commits, so bumping is a routine step.

### Selected Option

Option 2 (user's choice).

### Rationale

Bumps stay a one-word routine that always produces the same commit message and always includes `uv.lock`. Pushing and installing move out of the script: pushing goes through the normal PR flow, and installing is a documented one-time `uv tool install --editable .`, since an editable install never needs re-running after a bump.

### Rejected Options

- Option 1: the commit step, and remembering to stage `uv.lock`, would be manual each time.

## 3. Tag-stripping scope: src and tests, every tag family

Date: 2026-09-23

### Options Considered

1. `src/adw`, only `Story`/`ISS`/`Epic`. This is exactly the epic's AC grep: 203 lines.
2. `src/adw`, adding `UX`/`FR`/`NFR`/`AC` tags: 235 lines.
3. `src/adw` and `tests`, every tag family: 462 lines.

### Dependencies

- The tags point at planning docs that `dee39197` removed from the repo, so no reader can resolve them.
- The tests hold as many tags as src.

### Selected Option

Option 3 (user's choice).

### Rationale

One pass leaves no dangling reference in the code at all, and the whole-tree grep can serve as an acceptance check. The src and test edits land as separate commits (TASK-004 and TASK-005), so each diff stays reviewable.

### Rejected Options

- Options 1 and 2: they leave half the dangling references behind.
- The audit bug IDs `(B1)`–`(B21)` are excluded under every option. The epic-level AC traces regression tests through them.
