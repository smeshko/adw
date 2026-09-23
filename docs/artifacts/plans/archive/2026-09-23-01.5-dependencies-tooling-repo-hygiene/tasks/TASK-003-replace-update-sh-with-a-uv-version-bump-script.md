# TASK-003: Replace update.sh with a uv version-bump script

Depends on: None
Suggested commit: `chore: replace update.sh with a uv version-bump script`

## Goal

`scripts/bump.sh [major|minor|patch]` bumps the version in `pyproject.toml` and `uv.lock` together and commits exactly those two files. It doesn't push or install. `AGENTS.md` and `README.md` document the bump and the `uv tool install --editable .` install. `update.sh` is deleted.

## Files

- `update.sh`: delete (`git rm`).
- `scripts/bump.sh`: new and executable (`chmod +x`). It follows `scripts/preflight.sh`'s shape: a header comment with usage, then `set -euo pipefail` and `cd "$(git rev-parse --show-toplevel)"`. The body:
  - `part="${1:-patch}"`. Anything other than `major|minor|patch` prints the usage line to stderr and exits 1.
  - Refuse to run with exit 1 and a message when `pyproject.toml` or `uv.lock` already has uncommitted changes: `git diff --quiet HEAD -- pyproject.toml uv.lock`. This keeps unrelated edits out of the bump commit.
  - `uv version --bump "$part"`, then `new="$(uv version --short)"`.
  - `git commit -m "chore: bump version to $new" -- pyproject.toml uv.lock`. The pathspec form commits only these two files, even when other changes are staged.
  - It has no `git push` and no install step.
- `AGENTS.md`, `## Commands`: add two bullets in the existing style:
  - Install the CLI: `uv tool install --editable .` from the main checkout. Then `adw --version` matches `pyproject.toml`, and edits take effect without reinstalling.
  - Bump the version: `scripts/bump.sh [major|minor|patch]`. It updates `pyproject.toml` and `uv.lock` and commits them. Ship it through a PR like any other change.
- `README.md`, `## Installation`: `uv tool install --editable .` for the `adw` CLI, and `uv sync` for development.

## Acceptance

- [ ] `update.sh` is gone, and `git grep -n "update.sh"` outside `docs/artifacts/` returns nothing.
- [ ] In a scratch clone, `scripts/bump.sh patch`:
  - makes one commit, `chore: bump version to <X.Y.Z+1>`
  - `git show --stat HEAD` lists only `pyproject.toml` and `uv.lock`
  - `grep '^version' pyproject.toml` and the `adw` entry in `uv.lock` both show the new version
  - `uv sync --locked` passes afterwards
- [ ] In the scratch clone, `scripts/bump.sh bogus` exits 1 with the usage line. With a dirty `pyproject.toml`, `scripts/bump.sh` exits 1 and makes no commit.
- [ ] Following the documented install into an isolated tool dir, `which adw` resolves to that dir, and `adw --version` prints the `pyproject.toml` version.
- [ ] `scripts/preflight.sh` passes.

Evidence:
- the scratch-clone transcript: bump, `git show --stat HEAD`, both version greps, `uv sync --locked`, and the two refusals
- the isolated-install transcript: `which adw`, `adw --version`, and `grep '^version' pyproject.toml`

## Steps

- [ ] Load the `writing-for-agents` skill before editing `AGENTS.md`.
- [ ] Write `scripts/bump.sh` and `chmod +x` it. `git rm update.sh`.
- [ ] Update `AGENTS.md` and `README.md`.
- [ ] Scratch-clone demo. `S` is the session scratchpad.
  - `git clone -q /Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-11 "$S/bump-demo"`.
  - Copy in the uncommitted `scripts/bump.sh`, then `git add` and `git commit -m wip` it inside the clone.
  - Run `scripts/bump.sh patch` and record the evidence.
  - Then `scripts/bump.sh bogus`. Then `echo >> pyproject.toml && scripts/bump.sh`, and confirm `git log -1` is unchanged.
- [ ] Isolated install demo:
  - `T="$S/uvtool"`
  - `UV_TOOL_DIR="$T/tools" UV_TOOL_BIN_DIR="$T/bin" uv tool install --editable .`
  - `PATH="$T/bin:$PATH" sh -c 'which adw && adw --version'`
  - Then uninstall with the same env vars, and `rm -rf "$T"`.
- [ ] `scripts/preflight.sh`.

## Notes

- Never run `scripts/bump.sh` in the worktree itself. Bumping the version is not part of this phase.
- The real install stays on conda until after merge (see `PLAN.md` → Post-merge). The isolated demo leaves `~/.local/bin` untouched.
