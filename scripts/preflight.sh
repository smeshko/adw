#!/usr/bin/env bash
#
# Fast pre-PR checks: the lint, format and type gates CI runs, without the
# ~3 min test suite (run that with `uv run pytest`).
#
# Usage: scripts/preflight.sh

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "==> ruff check"
uv run ruff check src/ tests/

echo "==> ruff format --check"
uv run ruff format --check src/ tests/

echo "==> mypy"
uv run mypy src/adw

echo "preflight: ok"
