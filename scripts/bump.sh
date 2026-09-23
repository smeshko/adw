#!/usr/bin/env bash
#
# Bump the adw version in pyproject.toml and uv.lock, and commit both.
# It doesn't push or install: ship the commit through a PR.
#
# Usage: scripts/bump.sh [major|minor|patch]   (default: patch)

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

usage="usage: scripts/bump.sh [major|minor|patch]"

part="${1:-patch}"
case "$part" in
    major | minor | patch) ;;
    *)
        echo "$usage" >&2
        exit 1
        ;;
esac

if ! git diff --quiet HEAD -- pyproject.toml uv.lock; then
    echo "bump: pyproject.toml or uv.lock has uncommitted changes; commit or revert them first" >&2
    exit 1
fi

uv version --bump "$part"
new="$(uv version --short)"

git commit -m "chore: bump version to $new" -- pyproject.toml uv.lock
