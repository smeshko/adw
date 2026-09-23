"""Core constants for ADW pipeline execution.

This module defines immutable constants used throughout the ADW orchestration
system. The most critical constant is PHASE_SEQUENCE, which defines the fixed
order of phase execution (5 phases).
"""

from pathlib import Path

# Fixed phase sequence - order is critical
# Phases execute in this exact order: Plan → Build → Validate → Document → Ship
# Using a tuple ensures the sequence cannot be accidentally modified.
# Evidence gathering and platform detection run at the start of the validate
# phase. The ship phase handles LLM-driven deployment: an optional version
# bump, build and publish commands, and PR merge automation.
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "validate",
    "document",
    "ship",
)

# Artifact path patterns for consistent path construction
# Format: .adw/runs/{run_id}/artifacts/{phase}/{artifact_name}
PR_DESCRIPTION_ARTIFACT = "artifacts/document/pr_description.md"

# Run directory layout: .adw/runs/{run_id}/{LIVE_LOG, CONTEXT_FILE}
LIVE_LOG = "live.log"
CONTEXT_FILE = "context.json"

# Run statuses after which a run never changes again
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"completed", "failed", "aborted", "interrupted"}
)


def project_runs_dir(project_root: Path) -> Path:
    """Return the runs directory of the project rooted at ``project_root``."""
    return project_root / ".adw" / "runs"
