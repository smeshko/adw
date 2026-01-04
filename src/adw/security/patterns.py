"""Default security patterns for blocking dangerous operations.

This module defines the default blocked patterns for shell commands,
file access, and allowed exceptions for safe files.
"""

import re
from typing import Final

# Shell command patterns that should be blocked
BLOCKED_SHELL_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"rm\s+(-[rRfF]+\s+)*[/~\.]", "Recursive delete command targeting root, home, or current directory"),
    (r"chmod\s+777", "Insecure file permissions (world-writable)"),
    (r"git\s+push\s+.*--force", "Force push can destroy git history"),
    (r"git\s+push\s+.*-f\b", "Force push can destroy git history"),
    (r">\s*\.env\b", "Redirect output to .env file"),
    (r"mkfs\.", "Filesystem format command"),
    (r"dd\s+if=.*of=/dev/", "Direct disk write operation"),
    (r":\(\)\{\s*:\|\s*:\s*&\s*\}\s*;:", "Fork bomb pattern"),
]

# File patterns that should be blocked from reading/writing
BLOCKED_FILE_PATTERNS: Final[list[tuple[str, str]]] = [
    (r"^\.env$", "Environment file containing secrets"),
    (r"^\.adw\.env$", "ADW environment file containing secrets"),
    (r"/\.env$", "Environment file in subdirectory"),
    (r"/\.adw\.env$", "ADW environment file in subdirectory"),
    (r"\.pem$", "PEM certificate/key file"),
    (r"\.key$", "Private key file"),
    (r"id_rsa", "SSH private key"),
    (r"id_ed25519", "SSH private key"),
    (r"credentials\.json$", "Credentials file"),
    (r"\.aws/credentials$", "AWS credentials file"),
]

# File patterns that are exceptions to blocked patterns (safe to access)
ALLOWED_FILE_PATTERNS: Final[list[str]] = [
    r"\.env\.example$",
    r"\.env\.sample$",
    r"\.env\.template$",
    r"\.env\.local\.example$",
]

# Pre-compiled patterns for performance
_COMPILED_SHELL_PATTERNS: list[tuple[re.Pattern[str], str]] = []
_COMPILED_FILE_PATTERNS: list[tuple[re.Pattern[str], str]] = []
_COMPILED_ALLOWED_PATTERNS: list[re.Pattern[str]] = []


def _compile_patterns() -> None:
    """Compile all patterns once for performance.

    This function populates the module-level compiled pattern caches on first call.
    Subsequent calls are no-ops unless _reset_compiled_patterns() is called first.

    Side Effects:
        Modifies global variables:
        - _COMPILED_SHELL_PATTERNS
        - _COMPILED_FILE_PATTERNS
        - _COMPILED_ALLOWED_PATTERNS
    """
    global _COMPILED_SHELL_PATTERNS, _COMPILED_FILE_PATTERNS, _COMPILED_ALLOWED_PATTERNS

    if not _COMPILED_SHELL_PATTERNS:
        _COMPILED_SHELL_PATTERNS = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in BLOCKED_SHELL_PATTERNS
        ]

    if not _COMPILED_FILE_PATTERNS:
        _COMPILED_FILE_PATTERNS = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in BLOCKED_FILE_PATTERNS
        ]

    if not _COMPILED_ALLOWED_PATTERNS:
        _COMPILED_ALLOWED_PATTERNS = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ALLOWED_FILE_PATTERNS
        ]


def _reset_compiled_patterns() -> None:
    """Reset compiled pattern caches for testing.

    This function clears all compiled pattern caches, forcing
    recompilation on the next call to _compile_patterns().
    Primarily useful for testing.
    """
    global _COMPILED_SHELL_PATTERNS, _COMPILED_FILE_PATTERNS, _COMPILED_ALLOWED_PATTERNS
    _COMPILED_SHELL_PATTERNS = []
    _COMPILED_FILE_PATTERNS = []
    _COMPILED_ALLOWED_PATTERNS = []


def match_shell_pattern(command: str) -> tuple[str, str] | None:
    """Check if a shell command matches any blocked pattern.
    
    Args:
        command: The shell command to check.
        
    Returns:
        Tuple of (pattern, description) if blocked, None otherwise.
    """
    _compile_patterns()
    
    for pattern, description in _COMPILED_SHELL_PATTERNS:
        if pattern.search(command):
            return (pattern.pattern, description)
    
    return None


def match_file_pattern(file_path: str) -> tuple[str, str] | None:
    """Check if a file path matches any blocked pattern.
    
    Args:
        file_path: The file path to check.
        
    Returns:
        Tuple of (pattern, description) if blocked, None otherwise.
    """
    _compile_patterns()
    
    # Check if file is in the allowed list first
    for pattern in _COMPILED_ALLOWED_PATTERNS:
        if pattern.search(file_path):
            return None
    
    # Check blocked patterns
    for pattern, description in _COMPILED_FILE_PATTERNS:
        if pattern.search(file_path):
            return (pattern.pattern, description)
    
    return None


def is_allowed_env_file(file_path: str) -> bool:
    """Check if a file is an allowed .env file (example, sample, template).
    
    Args:
        file_path: The file path to check.
        
    Returns:
        True if the file is an allowed env file, False otherwise.
    """
    _compile_patterns()
    
    for pattern in _COMPILED_ALLOWED_PATTERNS:
        if pattern.search(file_path):
            return True
    
    return False
