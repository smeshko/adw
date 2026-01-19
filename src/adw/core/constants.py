"""Core constants for ADW pipeline execution.

This module defines immutable constants used throughout the ADW orchestration
system. The most critical constant is PHASE_SEQUENCE, which defines the fixed
order of phase execution (5 phases).
"""

# Fixed phase sequence - order is critical
# Phases execute in this exact order: Plan → Build → Validate → Document → Ship
# Using a tuple ensures the sequence cannot be accidentally modified.
# NOTE: The "verify" phase was removed in ISS-019 - evidence gathering and
# platform detection now occur at the start of the validate phase.
# NOTE: The "ship" phase was added in Story 15.1 - LLM-driven deployment with
# optional version bump, build, publish commands, and PR merge automation.
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
