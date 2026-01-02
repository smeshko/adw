"""Artifact management for ADW phase outputs.

This module provides the ArtifactManager class that handles storage and retrieval
of phase artifacts:

.adw/runs/<run_id>/artifacts/<phase>/<artifact_name>

Example:
    - artifacts/build/diff.txt
    - artifacts/verify/evidence.json
"""

import json
import os
from pathlib import Path
from typing import Any

from adw.exceptions import StateError


class ArtifactManager:
    """Manages phase artifact storage and retrieval.

    Artifacts are stored at:
    .adw/runs/<run_id>/artifacts/<phase>/<name>

    Example:
        >>> from pathlib import Path
        >>> manager = ArtifactManager(Path(".adw/runs"))
        >>> manager.store("01RUN", "build", "diff.txt", "file content")
        >>> content = manager.get("01RUN", "build", "diff.txt")

    Attributes:
        runs_dir: Path to the .adw/runs directory.
    """

    def __init__(self, runs_dir: Path) -> None:
        """Initialize the ArtifactManager.

        Args:
            runs_dir: Path to the runs directory (.adw/runs).
        """
        self.runs_dir = runs_dir

    def store(
        self,
        run_id: str,
        phase: str,
        name: str,
        content: str | bytes,
    ) -> Path:
        """Store an artifact.

        Uses atomic write pattern (temp file + fsync + rename) to ensure
        data integrity on power failure or crash.

        Args:
            run_id: The run ID.
            phase: Phase that produced the artifact (e.g., "build", "verify").
            name: Artifact filename.
            content: Artifact content (text or binary).

        Returns:
            Path to the stored artifact.

        Raises:
            StateError: If write fails due to permissions or disk issues.
        """
        artifacts_dir = self.runs_dir / run_id / "artifacts" / phase
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = artifacts_dir / name
        temp_path = artifact_path.with_suffix(artifact_path.suffix + ".tmp")

        try:
            mode = "w" if isinstance(content, str) else "wb"
            with open(temp_path, mode) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            temp_path.rename(artifact_path)
            return artifact_path

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="ARTIFACT_WRITE_FAILED",
                message=f"Failed to write artifact {phase}/{name}: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

    def get(
        self,
        run_id: str,
        phase: str,
        name: str,
        *,
        binary: bool = False,
    ) -> str | bytes | None:
        """Retrieve an artifact.

        Args:
            run_id: The run ID.
            phase: Phase that produced the artifact.
            name: Artifact filename.
            binary: If True, read as binary content.

        Returns:
            Artifact content, or None if not found.
        """
        artifact_path = self.runs_dir / run_id / "artifacts" / phase / name

        if not artifact_path.exists():
            return None

        try:
            if binary:
                return artifact_path.read_bytes()
            return artifact_path.read_text()
        except OSError:
            return None

    def store_json(
        self,
        run_id: str,
        phase: str,
        name: str,
        data: Any,
    ) -> Path:
        """Store JSON artifact with automatic serialization.

        Args:
            run_id: The run ID.
            phase: Phase that produced the artifact.
            name: Artifact filename (should end in .json).
            data: JSON-serializable data.

        Returns:
            Path to the stored artifact.
        """
        content = json.dumps(data, indent=2, default=str)
        return self.store(run_id, phase, name, content)

    def get_json(
        self,
        run_id: str,
        phase: str,
        name: str,
    ) -> Any | None:
        """Retrieve and parse JSON artifact.

        Args:
            run_id: The run ID.
            phase: Phase that produced the artifact.
            name: Artifact filename.

        Returns:
            Parsed JSON data, or None if not found or invalid JSON.
        """
        content = self.get(run_id, phase, name)
        if content is None:
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def list_artifacts(
        self,
        run_id: str,
        phase: str | None = None,
    ) -> list[dict[str, Any]]:
        """List artifacts for a run.

        Args:
            run_id: The run ID.
            phase: Optional phase filter. If None, list all phases.

        Returns:
            List of artifact metadata dictionaries with keys:
            - phase: Phase name
            - name: Artifact filename
            - path: Full path to artifact
            - size: File size in bytes
            - modified: Modification time (Unix timestamp)
        """
        artifacts_dir = self.runs_dir / run_id / "artifacts"
        if not artifacts_dir.exists():
            return []

        results: list[dict[str, Any]] = []

        if phase:
            phase_dirs = [artifacts_dir / phase]
        else:
            phase_dirs = [d for d in artifacts_dir.iterdir() if d.is_dir()]

        for phase_dir in phase_dirs:
            if not phase_dir.exists():
                continue
            phase_name = phase_dir.name
            for artifact_path in sorted(phase_dir.iterdir()):
                if artifact_path.is_file():
                    stat = artifact_path.stat()
                    results.append(
                        {
                            "phase": phase_name,
                            "name": artifact_path.name,
                            "path": artifact_path,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )

        return sorted(results, key=lambda a: (a["phase"], a["name"]))

    def get_artifact_paths(self, run_id: str) -> dict[str, list[str]]:
        """Get all artifact paths grouped by phase.

        This is useful for tracking artifact paths in RunContext without
        storing the full content.

        Args:
            run_id: The run ID.

        Returns:
            Dictionary mapping phase name to list of artifact filenames.
        """
        artifacts = self.list_artifacts(run_id)
        paths: dict[str, list[str]] = {}
        for artifact in artifacts:
            phase = artifact["phase"]
            if phase not in paths:
                paths[phase] = []
            paths[phase].append(artifact["name"])
        return paths
