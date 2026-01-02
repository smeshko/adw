"""Core constants for ADW pipeline execution.

This module defines immutable constants used throughout the ADW orchestration
system. The most critical constant is PHASE_SEQUENCE, which defines the fixed
order of phase execution.
"""

# Fixed phase sequence - order is critical
# Phases execute in this exact order: Plan → Build → Verify → Validate → Document
# Using a tuple ensures the sequence cannot be accidentally modified.
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "verify",
    "validate",
    "document",
)
