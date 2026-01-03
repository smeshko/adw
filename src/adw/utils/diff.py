"""JSON diff utility for comparing state snapshots.

This module provides functions for computing differences between JSON-like
dictionaries, useful for state inspection and debugging.
"""

from typing import Any

__all__ = ["json_diff", "DiffResult"]


class DiffResult:
    """Result of a JSON diff operation.

    Attributes:
        added: Dict of added paths to values.
        removed: Dict of removed paths to values.
        changed: Dict of changed paths to (old, new) tuples.
    """

    def __init__(self) -> None:
        """Initialize empty diff result."""
        self.added: dict[str, Any] = {}
        self.removed: dict[str, Any] = {}
        self.changed: dict[str, tuple[Any, Any]] = {}

    def __bool__(self) -> bool:
        """Return True if there are any differences."""
        return bool(self.added or self.removed or self.changed)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"DiffResult(added={len(self.added)}, "
            f"removed={len(self.removed)}, changed={len(self.changed)})"
        )

    def to_changes_list(self) -> list[tuple[str, str, str]]:
        """Convert to list of (type, path, value) tuples.

        Returns:
            List suitable for display, with '+' for added, '-' for removed,
            '~' for changed.
        """
        changes: list[tuple[str, str, str]] = []

        for path, value in sorted(self.added.items()):
            changes.append(("+", path, repr(value)))

        for path, value in sorted(self.removed.items()):
            changes.append(("-", path, repr(value)))

        for path, (old_val, new_val) in sorted(self.changed.items()):
            changes.append(("~", path, f"{repr(old_val)} → {repr(new_val)}"))

        return changes


def json_diff(old: dict[str, Any], new: dict[str, Any]) -> DiffResult:
    """Compute differences between two JSON-like dictionaries.

    Args:
        old: Original dictionary.
        new: Modified dictionary.

    Returns:
        DiffResult with added, removed, and changed items.

    Example:
        >>> result = json_diff({"a": 1}, {"a": 2, "b": 3})
        >>> result.changed
        {'a': (1, 2)}
        >>> result.added
        {'b': 3}
    """
    result = DiffResult()
    _diff_recursive(old, new, "", result)
    return result


def _diff_recursive(
    old: dict[str, Any],
    new: dict[str, Any],
    path: str,
    result: DiffResult,
) -> None:
    """Recursively compute diff between dictionaries.

    Args:
        old: Original dictionary.
        new: Modified dictionary.
        path: Current path prefix.
        result: DiffResult to populate.
    """
    all_keys = set(old.keys()) | set(new.keys())

    for key in sorted(all_keys):
        current_path = f"{path}.{key}" if path else str(key)

        if key not in old:
            # Addition
            result.added[current_path] = new[key]
        elif key not in new:
            # Removal
            result.removed[current_path] = old[key]
        elif old[key] != new[key]:
            # Potential change - check type
            old_val = old[key]
            new_val = new[key]

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # Recurse into nested dicts
                _diff_recursive(old_val, new_val, current_path, result)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                # Handle arrays
                _diff_arrays(old_val, new_val, current_path, result)
            else:
                # Simple value change
                result.changed[current_path] = (old_val, new_val)


def _diff_arrays(
    old: list[Any],
    new: list[Any],
    path: str,
    result: DiffResult,
) -> None:
    """Compute diff between arrays.

    For simplicity, we compare by index. Added/removed elements at the end
    are tracked separately.

    Args:
        old: Original list.
        new: Modified list.
        path: Current path prefix.
        result: DiffResult to populate.
    """
    max_len = max(len(old), len(new))

    for i in range(max_len):
        index_path = f"{path}[{i}]"

        if i >= len(old):
            # New element added
            result.added[index_path] = new[i]
        elif i >= len(new):
            # Element removed
            result.removed[index_path] = old[i]
        elif old[i] != new[i]:
            # Element changed
            old_val = old[i]
            new_val = new[i]

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # Recurse into nested dicts
                _diff_recursive(old_val, new_val, index_path, result)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                # Recurse into nested arrays
                _diff_arrays(old_val, new_val, index_path, result)
            else:
                result.changed[index_path] = (old_val, new_val)
