"""Validation state persistence manager.

This module provides the ValidationStateManager class that handles
persistence of validation loop state for resume capability.

State is stored in the .adw/runs/<run_id>/validation/ directory:
- state.json: Current loop state (iteration, status, timestamps)
- issues.json: All issues with current status
- triage.json: All triage decisions with reasons
- fix-history.json: Fix attempt history

Key features:
- Atomic writes using temp file + rename pattern
- JSON format for human readability and debugging
- Graceful handling of missing or corrupted files
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adw.validation.models import ValidationIssue, ValidationState

__all__ = ["ValidationStateManager"]

logger = logging.getLogger(__name__)


class ValidationStateManager:
    """Manages validation state persistence for resume capability.

    Stores validation state in the run's validation directory:
    .adw/runs/<run_id>/validation/

    Files:
    - state.json: Loop state (iteration, status, timestamps)
    - issues.json: All issues with their current status
    - triage.json: Triage decisions with reasons
    - fix-history.json: History of fix attempts

    Attributes:
        run_id: The run ID this manager is associated with.
        validation_dir: Path to the validation state directory.

    Example:
        >>> from pathlib import Path
        >>> manager = ValidationStateManager("01HQ123", Path(".adw/runs/01HQ123"))
        >>> manager.save_state(state)
        >>> loaded = manager.load_state()
    """

    def __init__(self, run_id: str, base_path: Path) -> None:
        """Initialize the ValidationStateManager.

        Args:
            run_id: The run ID for state association.
            base_path: Base path to the run directory (.adw/runs/<run_id>).
        """
        self.run_id = run_id
        self.validation_dir = base_path / "validation"
        # Create validation directory if it doesn't exist
        self.validation_dir.mkdir(parents=True, exist_ok=True)

    @property
    def state_file(self) -> Path:
        """Path to the state.json file."""
        return self.validation_dir / "state.json"

    @property
    def issues_file(self) -> Path:
        """Path to the issues.json file."""
        return self.validation_dir / "issues.json"

    @property
    def triage_file(self) -> Path:
        """Path to the triage.json file."""
        return self.validation_dir / "triage.json"

    @property
    def fix_history_file(self) -> Path:
        """Path to the fix-history.json file."""
        return self.validation_dir / "fix-history.json"

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file atomically using temp file + rename pattern.

        Ensures data durability by:
        1. Writing to a temporary file
        2. Calling fsync for durability
        3. Atomically renaming to target path

        Args:
            path: Target file path.
            content: Content to write.

        Raises:
            OSError: If write or rename fails.
        """
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # Use replace() for cross-platform atomic overwrite
            # (rename() fails on Windows if destination exists)
            temp_path.replace(path)
            logger.debug("Atomic write completed", extra={"path": str(path)})
        except OSError:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    def save_issues(self, issues: list[ValidationIssue]) -> None:
        """Save all issues to issues.json.

        Args:
            issues: List of ValidationIssue objects to persist.
        """
        data = [issue.to_dict() for issue in issues]
        content = json.dumps(data, indent=2, default=str)
        self._atomic_write(self.issues_file, content)
        logger.info(
            "Issues saved",
            extra={"count": len(issues), "path": str(self.issues_file)},
        )

    def load_issues(self) -> list[ValidationIssue]:
        """Load issues from issues.json.

        Returns:
            List of ValidationIssue objects, or empty list if file
            doesn't exist or is corrupted.
        """
        from adw.validation.models import ValidationIssue

        if not self.issues_file.exists():
            logger.debug("Issues file not found, returning empty list")
            return []

        try:
            data = json.loads(self.issues_file.read_text())
            issues = [ValidationIssue.from_dict(item) for item in data]
            logger.info(
                "Issues loaded",
                extra={"count": len(issues), "path": str(self.issues_file)},
            )
            return issues
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(
                "Failed to load issues",
                extra={"error": str(e), "path": str(self.issues_file)},
            )
            return []

    def save_triage(self, decisions: list[dict[str, Any]]) -> None:
        """Save triage decisions to triage.json.

        Args:
            decisions: List of triage decision dictionaries containing:
                - issue_id: The issue ID
                - decision: FIX, DISMISS, or DEFER
                - reason: Reason for the decision
                - auto_decided: Whether decision was automatic
                - timestamp: When the decision was made
        """
        # Add timestamp to each decision if not present
        for decision in decisions:
            if "timestamp" not in decision:
                decision["timestamp"] = datetime.now(UTC).isoformat()

        content = json.dumps(decisions, indent=2)
        self._atomic_write(self.triage_file, content)
        logger.info(
            "Triage decisions saved",
            extra={"count": len(decisions), "path": str(self.triage_file)},
        )

    def load_triage(self) -> dict[str, dict[str, Any]]:
        """Load triage decisions as issue_id -> decision mapping.

        Returns:
            Dictionary mapping issue IDs to their triage decisions,
            or empty dict if file doesn't exist or is corrupted.
        """
        if not self.triage_file.exists():
            logger.debug("Triage file not found, returning empty dict")
            return {}

        try:
            data = json.loads(self.triage_file.read_text())
            # Validate that data is a list of dicts with issue_id
            if not isinstance(data, list):
                raise TypeError(f"Expected list, got {type(data).__name__}")
            result = {d["issue_id"]: d for d in data}
            logger.info(
                "Triage decisions loaded",
                extra={"count": len(result), "path": str(self.triage_file)},
            )
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                "Failed to load triage decisions",
                extra={"error": str(e), "path": str(self.triage_file)},
            )
            return {}

    def save_fix_history(self, history: list[dict[str, Any]]) -> None:
        """Save fix iteration history to fix-history.json.

        Args:
            history: List of fix iteration records containing:
                - iteration: Iteration number
                - issues_fixed: Number of issues fixed
                - issues_remaining: Number of issues remaining
                - issues_deferred: Number of issues deferred
                - files_modified: List of modified files
                - timestamp: When the iteration completed
        """
        # Add timestamp to each record if not present
        for record in history:
            if "timestamp" not in record:
                record["timestamp"] = datetime.now(UTC).isoformat()

        content = json.dumps(history, indent=2)
        self._atomic_write(self.fix_history_file, content)
        logger.info(
            "Fix history saved",
            extra={"count": len(history), "path": str(self.fix_history_file)},
        )

    def load_fix_history(self) -> list[dict[str, Any]]:
        """Load fix iteration history from fix-history.json.

        Returns:
            List of fix iteration records, or empty list if file
            doesn't exist or is corrupted.
        """
        if not self.fix_history_file.exists():
            logger.debug("Fix history file not found, returning empty list")
            return []

        try:
            data = json.loads(self.fix_history_file.read_text())
            logger.info(
                "Fix history loaded",
                extra={"count": len(data), "path": str(self.fix_history_file)},
            )
            return data
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to load fix history",
                extra={"error": str(e), "path": str(self.fix_history_file)},
            )
            return []

    def save_state(self, state: "dict[str, Any] | ValidationState") -> None:
        """Save validation loop state to state.json.

        Automatically updates last_updated timestamp. Uses atomic write
        (write to temp file, then rename) for crash safety.

        Args:
            state: Either a ValidationState model or a dict containing:
                - run_id: The run ID
                - current_iteration: Current iteration number
                - total_iterations: Max iterations configured
                - loop_state: Loop status information
                - started_at: When validation started
                - last_updated: (auto-set) When state was saved
        """
        from adw.validation.models import ValidationState

        # Convert ValidationState to dict if needed
        if isinstance(state, ValidationState):
            state_dict = state.to_dict()
        else:
            state_dict = state

        # Ensure run_id matches and update timestamp
        state_dict["run_id"] = self.run_id
        state_dict["last_updated"] = datetime.now(UTC).isoformat()

        content = json.dumps(state_dict, indent=2, default=str)
        self._atomic_write(self.state_file, content)
        logger.info(
            "State saved",
            extra={
                "iteration": state_dict.get("current_iteration"),
                "path": str(self.state_file),
            },
        )

    def load_state(self) -> dict[str, Any] | None:
        """Load validation loop state from state.json.

        Returns:
            State dictionary or None if file doesn't exist or is corrupted.
        """
        if not self.state_file.exists():
            logger.debug("State file not found")
            return None

        try:
            data = json.loads(self.state_file.read_text())
            logger.info(
                "State loaded",
                extra={
                    "iteration": data.get("current_iteration"),
                    "path": str(self.state_file),
                },
            )
            return data
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to load state",
                extra={"error": str(e), "path": str(self.state_file)},
            )
            return None

    def load_state_model(self) -> "ValidationState | None":
        """Load validation loop state as a ValidationState model.

        Returns:
            ValidationState model or None if file doesn't exist or is corrupted.
        """
        from adw.validation.models import ValidationState

        data = self.load_state()
        if data is None:
            return None

        try:
            return ValidationState.from_dict(data)
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse state as ValidationState",
                extra={"error": str(e), "path": str(self.state_file)},
            )
            return None

    def can_resume(self) -> bool:
        """Check if validation can be resumed from saved state.

        Validates:
        - State file exists and is valid JSON
        - run_id matches current run
        - current_iteration > 0 (some progress made)

        Returns:
            True if validation can be resumed, False otherwise.
        """
        state = self.load_state()
        if state is None:
            return False

        # Verify run_id matches
        if state.get("run_id") != self.run_id:
            logger.warning(
                "State run_id mismatch",
                extra={
                    "state_run_id": state.get("run_id"),
                    "current_run_id": self.run_id,
                },
            )
            return False

        # Verify some progress was made
        current_iteration = state.get("current_iteration", 0)
        if current_iteration <= 0:
            logger.debug("No progress to resume (iteration <= 0)")
            return False

        return True

    def resume(self) -> "ValidationState":
        """Resume validation from saved state.

        Validates state integrity and returns the ValidationState model.
        Should only be called after can_resume() returns True.

        Returns:
            ValidationState model with the resumed state.

        Raises:
            ValueError: If state cannot be resumed (use can_resume() first).
        """
        from adw.validation.models import ValidationState

        if not self.can_resume():
            raise ValueError(
                f"Cannot resume validation for run {self.run_id}: "
                "state file missing, corrupted, or run_id mismatch"
            )

        state = self.load_state_model()
        if state is None:
            raise ValueError(
                f"Cannot resume validation for run {self.run_id}: "
                "failed to parse state as ValidationState"
            )

        logger.info(
            "Resuming validation from saved state",
            extra={
                "run_id": self.run_id,
                "iteration": state.current_iteration,
                "issues_remaining": state.loop_state.issues_remaining,
            },
        )

        return state

    def clear(self) -> None:
        """Clear all validation state files.

        Called on successful completion to clean up state.
        """
        files = [
            self.state_file,
            self.issues_file,
            self.triage_file,
            self.fix_history_file,
        ]
        for file_path in files:
            if file_path.exists():
                file_path.unlink()
                logger.debug("Removed state file", extra={"path": str(file_path)})

        logger.info("Validation state cleared")
