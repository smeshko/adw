"""Default security patterns for blocking dangerous commands.

This module defines the comprehensive set of blocked command patterns that
are enabled by default in ADW. These patterns cover:

- Destructive operations (rm -rf, format, dd)
- Permission changes (chmod 777, chown root)
- Dangerous git operations (force push, hard reset)
- Secret file access (.env, credentials)

Each pattern includes metadata for generating helpful error messages with
suggested alternatives.

Usage:
    >>> from adw.security.defaults import DEFAULT_SHELL_PATTERNS
    >>> for pattern in DEFAULT_SHELL_PATTERNS:
    ...     print(f"{pattern.category}: {pattern.description}")
"""

from adw.models.security import BlockedPattern

# =============================================================================
# DESTRUCTIVE COMMAND PATTERNS
#
# These patterns block operations that can cause irreversible data loss.
# Severity: critical (always block unless --allow-dangerous)
# =============================================================================

DESTRUCTIVE_PATTERNS: list[BlockedPattern] = [
    BlockedPattern(
        pattern=r"rm\s+(-[rRfFiI]+\s+)*(/|~|\.\.?)(?:\s|$)",
        description="Recursive delete of root, home, or current/parent directory",
        severity="critical",
        category="destructive",
        alternative="Use specific paths: rm -rf ./node_modules or rm -rf /tmp/cache",
    ),
    BlockedPattern(
        pattern=r"rm\s+-[rRfF]*[rR][fF]*\s+\*",
        description="Recursive delete with wildcard in current directory",
        severity="critical",
        category="destructive",
        alternative="Be explicit: rm -rf ./specific-dir/* or list files first with ls",
    ),
    BlockedPattern(
        pattern=r"mkfs\.",
        description="Format filesystem command",
        severity="critical",
        category="destructive",
        alternative="Requires manual execution with explicit confirmation",
    ),
    BlockedPattern(
        pattern=r"dd\s+.*of\s*=\s*/dev/(?:sd|hd|nvme|vd)",
        description="Direct disk write with dd command",
        severity="critical",
        category="destructive",
        alternative="Verify target device carefully; this operation is irreversible",
    ),
    BlockedPattern(
        pattern=r":\s*>\s*/",
        description="Truncate files in root directory",
        severity="critical",
        category="destructive",
        alternative="Use specific file paths, not root directory",
    ),
]

# =============================================================================
# PERMISSION PATTERNS
#
# These patterns block permission changes that could compromise security.
# Severity: warning (block with clear alternative)
# =============================================================================

PERMISSION_PATTERNS: list[BlockedPattern] = [
    BlockedPattern(
        pattern=r"chmod\s+777\s+",
        description="Setting world-writable permissions (chmod 777)",
        severity="warning",
        category="permission",
        alternative="Use chmod 755 for dirs or chmod 644 for files instead",
    ),
    BlockedPattern(
        pattern=r"chmod\s+-R\s+777",
        description="Recursive world-writable permissions",
        severity="critical",
        category="permission",
        alternative="Use chmod -R 755 for directories or chmod -R 644 for files",
    ),
    BlockedPattern(
        pattern=r"chown\s+(-R\s+)?root:",
        description="Changing ownership to root",
        severity="warning",
        category="permission",
        alternative="Use current user ownership or a dedicated service account",
    ),
]

# =============================================================================
# GIT DANGEROUS PATTERNS
#
# These patterns block git operations that can cause data loss or affect
# shared repositories.
# Severity: warning (can be overridden with caution)
# =============================================================================

GIT_DANGEROUS_PATTERNS: list[BlockedPattern] = [
    BlockedPattern(
        pattern=r"git\s+push\s+.*--force(?:\s|$)",
        description="Force push to remote repository",
        severity="warning",
        category="git_dangerous",
        alternative="Use --force-with-lease for safer force push",
    ),
    BlockedPattern(
        pattern=r"git\s+push\s+-f(?:\s|$)",
        description="Force push (short flag)",
        severity="warning",
        category="git_dangerous",
        alternative="Use --force-with-lease for safer force push",
    ),
    BlockedPattern(
        pattern=r"git\s+push\s+.*(?:main|master)\s+--force",
        description="Force push to main/master branch",
        severity="critical",
        category="git_dangerous",
        alternative="Create a PR instead of force pushing to main/master",
    ),
    BlockedPattern(
        pattern=r"git\s+reset\s+--hard",
        description="Hard reset (discards uncommitted changes)",
        severity="warning",
        category="git_dangerous",
        alternative="Use git stash first, or git reset --soft to preserve changes",
    ),
    BlockedPattern(
        pattern=r"git\s+clean\s+-[dDfFxX]*[fF]",
        description="Force clean untracked files",
        severity="warning",
        category="git_dangerous",
        alternative="Use git clean -n (dry run) first to preview what will be deleted",
    ),
    BlockedPattern(
        pattern=r"git\s+branch\s+-[dD]\s+(?:main|master|develop)(?:\s|$)",
        description="Delete main/master/develop branch",
        severity="critical",
        category="git_dangerous",
        alternative="Protected branches should not be deleted locally",
    ),
]

# =============================================================================
# SECRET ACCESS PATTERNS
#
# These patterns block access to secret files and credential storage.
# Severity: warning (logged, helpful alternatives provided)
# =============================================================================

SECRET_ACCESS_PATTERNS: list[BlockedPattern] = [
    BlockedPattern(
        pattern=r">\s*\.env\b(?!\.example|\.sample|\.template)",
        description="Redirect output to .env file",
        severity="warning",
        category="secret_access",
        alternative="Edit .env manually or use environment variable management tools",
    ),
    BlockedPattern(
        pattern=r"echo\s+.*>\s*\.env\b(?!\.example|\.sample|\.template)",
        description="Echo to .env file",
        severity="warning",
        category="secret_access",
        alternative="Add secrets manually to .env or use a secrets manager",
    ),
    BlockedPattern(
        pattern=r"cat\s+.*>\s*\.env\b(?!\.example|\.sample|\.template)",
        description="Cat to .env file",
        severity="warning",
        category="secret_access",
        alternative="Copy .env.example to .env and edit manually",
    ),
    BlockedPattern(
        pattern=r"tee\s+.*\.env\b(?!\.example|\.sample|\.template)",
        description="Tee to .env file",
        severity="warning",
        category="secret_access",
        alternative="Edit .env file directly using a text editor",
    ),
]

# =============================================================================
# FILE ACCESS PATTERNS
#
# These patterns block access to sensitive files.
# Severity: warning (with allowed exceptions)
# =============================================================================

FILE_ACCESS_PATTERNS: list[BlockedPattern] = [
    BlockedPattern(
        pattern=r"^\.env$",
        description="Direct .env file access",
        severity="warning",
        category="secret_access",
        alternative="Use environment variables directly via $VAR_NAME or os.environ",
    ),
    BlockedPattern(
        pattern=r"^\.adw\.env$",
        description="ADW environment file access",
        severity="warning",
        category="secret_access",
        alternative="Configure ADW settings in project.yaml instead",
    ),
    BlockedPattern(
        pattern=r"credentials\.json$",
        description="Credentials file access",
        severity="warning",
        category="secret_access",
        alternative="Use environment variables or a secrets manager",
    ),
    BlockedPattern(
        pattern=r"\.pem$",
        description="PEM key file access",
        severity="warning",
        category="secret_access",
        alternative="Reference keys by path in environment variables",
    ),
]

# =============================================================================
# ALLOWED PATTERNS (EXCEPTIONS)
#
# These patterns match files that look like secrets but are actually safe.
# Used to allow .env.example, .env.sample, .env.template
# =============================================================================

ALLOWED_ENV_PATTERNS: list[str] = [
    r"\.env\.example$",
    r"\.env\.sample$",
    r"\.env\.template$",
    r"\.env\.local\.example$",
    r"\.env\.development\.example$",
    r"\.env\.test$",  # Test env files are typically safe
]

# =============================================================================
# AGGREGATED PATTERN LISTS
#
# Convenience exports combining patterns by type
# =============================================================================

DEFAULT_SHELL_PATTERNS: list[BlockedPattern] = (
    DESTRUCTIVE_PATTERNS
    + PERMISSION_PATTERNS
    + GIT_DANGEROUS_PATTERNS
    + SECRET_ACCESS_PATTERNS
)

DEFAULT_FILE_PATTERNS: list[BlockedPattern] = FILE_ACCESS_PATTERNS

# =============================================================================
# PATTERN METADATA
#
# Dictionary mapping patterns to their descriptions and alternatives.
# Used for generating detailed error messages.
# =============================================================================

PATTERN_METADATA: dict[str, dict[str, str]] = {}

# Build metadata dictionary from all patterns
for pattern_list in [DEFAULT_SHELL_PATTERNS, DEFAULT_FILE_PATTERNS]:
    for blocked in pattern_list:
        PATTERN_METADATA[blocked.pattern] = {
            "description": blocked.description,
            "alternative": blocked.alternative,
            "severity": blocked.severity,
            "category": blocked.category,
        }
