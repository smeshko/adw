"""Snapshot manager for state snapshots at phase boundaries.

This module provides the SnapshotManager class that creates, lists, and loads
state snapshots for debugging and recovery.

Key features:
- Atomic writes using temp file + rename pattern
- Sequential numbering (001, 002, etc.)
- Pre-phase and post-phase snapshot creation
- Performance monitoring (NFR4: <500ms)
"""

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from adw.exceptions import StateError
from adw.models import StateSnapshot

if TYPE_CHECKING:
    from adw.models import PhaseResult, RunContext

__all__ = ["SnapshotManager"]

# Performance threshold for snapshot creation (NFR4)
_SNAPSHOT_THRESHOLD_MS: int = 500

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages state snapshots at phase boundaries.

    Creates snapshots before and after each phase for:
    - Debugging failures by examining pre-failure state
    - Resuming from known-good states
    - Time-travel debugging (NFR13)

    Attributes:
        runs_dir: Path to the .adw/runs directory.

    Example:
        >>> from pathlib import Path
        >>> manager = SnapshotManager(Path("/my/project/.adw/runs"))
        >>> path = manager.create_pre_phase_snapshot(context, "plan")
        >>> snapshots = manager.list_snapshots(context.run_id)
    """

    def __init__(self, runs_dir: Path) -> None:
        """Initialize the SnapshotManager.

        Args:
            runs_dir: Path to the .adw/runs directory.
        """
        self.runs_dir = runs_dir
        self._sequence_cache: dict[str, int] = {}

    def create_pre_phase_snapshot(
        self,
        context: "RunContext",
        phase: str,
    ) -> Path:
        """Create snapshot before phase starts.

        Args:
            context: Current run context.
            phase: Phase about to start.

        Returns:
            Path to created snapshot file.

        Raises:
            StateError: If snapshot creation fails.
        """
        return self._create_snapshot(
            context=context,
            phase_result=None,
            phase=phase,
            timing="pre",
        )

    def create_post_phase_snapshot(
        self,
        context: "RunContext",
        phase: str,
        phase_result: "PhaseResult | None",
    ) -> Path:
        """Create snapshot after phase completes.

        Args:
            context: Current run context.
            phase: Phase that just completed.
            phase_result: Result of the phase, or None if interrupted.

        Returns:
            Path to created snapshot file.

        Raises:
            StateError: If snapshot creation fails.
        """
        return self._create_snapshot(
            context=context,
            phase_result=phase_result,
            phase=phase,
            timing="post",
        )

    def _create_snapshot(
        self,
        context: "RunContext",
        phase_result: "PhaseResult | None",
        phase: str,
        timing: str,
    ) -> Path:
        """Internal method to create a snapshot.

        Must complete within 500ms (NFR4).

        Args:
            context: Current run context.
            phase_result: Result of phase (None for pre-phase).
            phase: Phase name.
            timing: "pre" or "post".

        Returns:
            Path to created snapshot file.

        Raises:
            StateError: If snapshot creation fails.
        """
        start_time = time.monotonic()

        run_id = context.run_id
        snapshots_dir = self.runs_dir / run_id / "snapshots"

        # Ensure snapshots directory exists
        if not snapshots_dir.exists():
            raise StateError(
                code="SNAPSHOTS_DIR_NOT_FOUND",
                message=f"Snapshots directory not found: {snapshots_dir}",
                suggestion="Ensure run directory structure is created first",
                recoverable=False,
            )

        # Get next sequence number
        sequence = self._get_next_sequence(run_id, snapshots_dir)

        # Create snapshot
        label = f"{timing}_{phase}"
        snapshot = StateSnapshot(
            context=context,
            phase_result=phase_result,
            timestamp=datetime.now(UTC),
            label=label,
            sequence=sequence,
        )

        # Generate filename: 001_pre_plan.json
        filename = f"{sequence:03d}_{label}.json"
        snapshot_path = snapshots_dir / filename
        temp_path = snapshot_path.with_suffix(".tmp")

        try:
            # Atomic write with fsync
            with open(temp_path, "w") as f:
                f.write(snapshot.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            temp_path.rename(snapshot_path)

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="SNAPSHOT_WRITE_FAILED",
                message=f"Failed to write snapshot: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

        # Check performance requirement (NFR4)
        elapsed_ms = (time.monotonic() - start_time) * 1000
        if elapsed_ms > _SNAPSHOT_THRESHOLD_MS:
            logger.warning(
                "Snapshot creation exceeded %dms threshold",
                _SNAPSHOT_THRESHOLD_MS,
                extra={"elapsed_ms": elapsed_ms, "snapshot": filename},
            )

        return snapshot_path

    def _get_next_sequence(self, run_id: str, snapshots_dir: Path) -> int:
        """Get next sequence number for snapshots.

        Uses caching to avoid filesystem queries on subsequent calls.

        Args:
            run_id: The run ID.
            snapshots_dir: Path to snapshots directory.

        Returns:
            Next sequence number (1-based).
        """
        # Check cache first
        if run_id in self._sequence_cache:
            self._sequence_cache[run_id] += 1
            return self._sequence_cache[run_id]

        # Count existing snapshots
        if not snapshots_dir.exists():
            self._sequence_cache[run_id] = 1
            return 1

        existing = list(snapshots_dir.glob("*.json"))
        next_seq = len(existing) + 1
        self._sequence_cache[run_id] = next_seq
        return next_seq

    def list_snapshots(self, run_id: str) -> list[dict[str, str | int | Path]]:
        """List all snapshots for a run.

        Returns metadata about each snapshot without loading full content.

        Args:
            run_id: The run ID.

        Returns:
            List of snapshot metadata sorted by sequence.
            Each dict contains: sequence, timing, phase, path, filename.
        """
        snapshots_dir = self.runs_dir / run_id / "snapshots"
        if not snapshots_dir.exists():
            return []

        snapshots: list[dict[str, str | int | Path]] = []
        for path in sorted(snapshots_dir.glob("*.json")):
            # Parse filename: 001_pre_plan.json
            name = path.stem
            parts = name.split("_", 2)
            if len(parts) >= 3:
                snapshots.append(
                    {
                        "sequence": int(parts[0]),
                        "timing": parts[1],
                        "phase": parts[2],
                        "path": path,
                        "filename": path.name,
                    }
                )

        return sorted(snapshots, key=lambda s: int(str(s["sequence"])))

    def load_snapshot(self, run_id: str, sequence: int) -> StateSnapshot:
        """Load a specific snapshot by sequence number.

        Args:
            run_id: The run ID.
            sequence: Snapshot sequence number.

        Returns:
            Loaded StateSnapshot.

        Raises:
            StateError: If snapshot not found or corrupted.
        """
        snapshots = self.list_snapshots(run_id)
        matching = [s for s in snapshots if s["sequence"] == sequence]

        if not matching:
            raise StateError(
                code="SNAPSHOT_NOT_FOUND",
                message=f"Snapshot {sequence} not found for run {run_id}",
                suggestion="Use list_snapshots to see available snapshots",
                recoverable=False,
            )

        path_value = matching[0]["path"]
        path = path_value if isinstance(path_value, Path) else Path(str(path_value))

        try:
            content = path.read_text()
            return StateSnapshot.model_validate_json(content)
        except json.JSONDecodeError as e:
            raise StateError(
                code="SNAPSHOT_CORRUPTED",
                message=f"Snapshot {sequence} is corrupted: {e}",
                suggestion="Try loading an earlier snapshot",
                recoverable=True,
            ) from e
        except ValidationError as e:
            raise StateError(
                code="SNAPSHOT_CORRUPTED",
                message=f"Snapshot {sequence} is corrupted: {e}",
                suggestion="Try loading an earlier snapshot",
                recoverable=True,
            ) from e
