"""Artifact-related models for ADW.

This module contains Pydantic models for artifact data structures
used during phase execution and artifact capture.
"""

from pydantic import BaseModel, Field


class DiffStats(BaseModel):
    """Statistics from a git diff.

    This model captures aggregate statistics from git diff output,
    including file counts and line change counts.

    Attributes:
        files_changed: Number of files changed
        insertions: Number of lines added
        deletions: Number of lines removed
        binary_files: Number of binary files detected in diff

    Example:
        >>> stats = DiffStats(files_changed=3, insertions=42, deletions=13)
        >>> stats.summary()
        '3 files changed, +42, -13'
    """

    files_changed: int = Field(default=0, ge=0, description="Number of files changed")
    insertions: int = Field(default=0, ge=0, description="Number of lines added")
    deletions: int = Field(default=0, ge=0, description="Number of lines removed")
    binary_files: int = Field(
        default=0, ge=0, description="Number of binary files in diff"
    )

    def summary(self) -> str:
        """Generate a human-readable summary of the diff stats.

        Returns:
            Summary string in format: '3 files changed, +42, -13'
            If binary files present, appends: ' (2 binary)'
        """
        base = (
            f"{self.files_changed} files changed, +{self.insertions}, -{self.deletions}"
        )
        if self.binary_files > 0:
            return f"{base} ({self.binary_files} binary)"
        return base
