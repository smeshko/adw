"""ULID generation utilities for ADW run identification.

This module provides ULID (Universally Unique Lexicographically Sortable
Identifier) generation for run IDs. ULIDs are preferred over UUIDs because:

- Sortable by creation time (unlike UUIDs)
- Timestamp embedded (debuggable)
- URL-safe, filesystem-safe
- No collisions in practice

Example:
    >>> from adw.utils.ulid import generate_run_id
    >>> run_id = generate_run_id()
    >>> print(run_id)  # e.g., "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
"""

from ulid import ULID


def generate_run_id() -> str:
    """Generate a new run ID in ULID format.

    Returns:
        A 26-character ULID string that is:
        - Lexicographically sortable by creation time
        - Uses Crockford's Base32 alphabet
        - Filesystem and URL safe

    Example:
        >>> run_id = generate_run_id()
        >>> len(run_id)
        26
        >>> run_id.isalnum()
        True
    """
    return str(ULID())
