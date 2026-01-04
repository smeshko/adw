"""Evidence gathering package for ADW.

This package contains modules for:
- Platform detection (determining if project is CLI, WEB, or BACKEND)
- Evidence capture strategies (terminal output, screenshots, API responses)
"""

from adw.evidence.detector import PlatformDetector

__all__ = [
    "PlatformDetector",
]
