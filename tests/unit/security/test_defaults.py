"""Tests for security default pattern definitions.

Verifies that:
- Default patterns are properly defined and compiled
- Pattern metadata is complete for all patterns
- Categories are correctly assigned
- All expected dangerous commands are covered
"""

import re

import pytest


class TestDefaultShellPatterns:
    """Tests for DEFAULT_SHELL_PATTERNS configuration."""

    def test_default_shell_patterns_not_empty(self) -> None:
        """Verify DEFAULT_SHELL_PATTERNS is defined and not empty."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        assert len(DEFAULT_SHELL_PATTERNS) > 0

    def test_all_patterns_are_blocked_pattern_instances(self) -> None:
        """Verify all patterns are BlockedPattern instances."""
        from adw.models.security import BlockedPattern
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        for pattern in DEFAULT_SHELL_PATTERNS:
            assert isinstance(pattern, BlockedPattern)

    def test_patterns_are_valid_regex(self) -> None:
        """Verify all patterns compile as valid regex."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        for blocked in DEFAULT_SHELL_PATTERNS:
            # Should not raise on compile
            re.compile(blocked.pattern)

    def test_rm_rf_root_pattern_exists(self) -> None:
        """Verify rm -rf / is blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        # At least one pattern should match rm -rf /
        test_command = "rm -rf /"
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "rm -rf / should be blocked"

    def test_rm_rf_home_pattern_exists(self) -> None:
        """Verify rm -rf ~ is blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        test_command = "rm -rf ~"
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "rm -rf ~ should be blocked"

    def test_rm_rf_dot_pattern_exists(self) -> None:
        """Verify rm -rf . is blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        test_command = "rm -rf ."
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "rm -rf . should be blocked"

    def test_chmod_777_pattern_exists(self) -> None:
        """Verify chmod 777 is blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        test_command = "chmod 777 /etc/passwd"
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "chmod 777 should be blocked"

    def test_git_force_push_pattern_exists(self) -> None:
        """Verify git push --force is blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        test_command = "git push --force origin main"
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "git push --force should be blocked"

    def test_env_file_write_pattern_exists(self) -> None:
        """Verify writes to .env are blocked."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        patterns = [p.pattern for p in DEFAULT_SHELL_PATTERNS]
        test_command = 'echo "SECRET=value" > .env'
        matched = any(re.search(p, test_command) for p in patterns)
        assert matched, "Writing to .env should be blocked"


class TestDefaultFilePatterns:
    """Tests for DEFAULT_FILE_PATTERNS configuration."""

    def test_default_file_patterns_not_empty(self) -> None:
        """Verify DEFAULT_FILE_PATTERNS is defined and not empty."""
        from adw.security.defaults import DEFAULT_FILE_PATTERNS

        assert len(DEFAULT_FILE_PATTERNS) > 0

    def test_env_file_blocked(self) -> None:
        """Verify .env file access is blocked."""
        from adw.security.defaults import DEFAULT_FILE_PATTERNS

        patterns = [p.pattern for p in DEFAULT_FILE_PATTERNS]
        matched = any(re.search(p, ".env") for p in patterns)
        assert matched, ".env should be blocked"

    def test_env_example_not_blocked(self) -> None:
        """Verify .env.example is NOT blocked (allowed exception)."""
        from adw.security.defaults import ALLOWED_ENV_PATTERNS, DEFAULT_FILE_PATTERNS

        # Check if it matches any blocked pattern
        blocked_patterns = [p.pattern for p in DEFAULT_FILE_PATTERNS]
        blocked = any(re.search(p, ".env.example") for p in blocked_patterns)

        # Check if it matches allowed pattern
        allowed = any(re.search(p, ".env.example") for p in ALLOWED_ENV_PATTERNS)

        # Either not blocked, or explicitly allowed
        assert not blocked or allowed, ".env.example should be allowed"


class TestPatternMetadata:
    """Tests for PATTERN_METADATA completeness."""

    def test_pattern_metadata_not_empty(self) -> None:
        """Verify PATTERN_METADATA is defined and not empty."""
        from adw.security.defaults import PATTERN_METADATA

        assert len(PATTERN_METADATA) > 0

    def test_all_shell_patterns_have_metadata(self) -> None:
        """Verify every shell pattern has corresponding metadata."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS, PATTERN_METADATA

        for blocked in DEFAULT_SHELL_PATTERNS:
            assert blocked.pattern in PATTERN_METADATA, (
                f"Pattern {blocked.pattern} missing from PATTERN_METADATA"
            )

    def test_metadata_has_required_fields(self) -> None:
        """Verify metadata entries have description and alternative."""
        from adw.security.defaults import PATTERN_METADATA

        for pattern, metadata in PATTERN_METADATA.items():
            assert "description" in metadata, f"Pattern {pattern} missing description"
            assert "alternative" in metadata, f"Pattern {pattern} missing alternative"


class TestPatternCategories:
    """Tests for pattern category assignments."""

    def test_destructive_category_exists(self) -> None:
        """Verify destructive category patterns exist."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        destructive_patterns = [p for p in DEFAULT_SHELL_PATTERNS if p.category == "destructive"]
        assert len(destructive_patterns) > 0, "Should have destructive category patterns"

    def test_permission_category_exists(self) -> None:
        """Verify permission category patterns exist."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        permission_patterns = [p for p in DEFAULT_SHELL_PATTERNS if p.category == "permission"]
        assert len(permission_patterns) > 0, "Should have permission category patterns"

    def test_git_dangerous_category_exists(self) -> None:
        """Verify git_dangerous category patterns exist."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS

        git_patterns = [p for p in DEFAULT_SHELL_PATTERNS if p.category == "git_dangerous"]
        assert len(git_patterns) > 0, "Should have git_dangerous category patterns"

    def test_secret_access_category_exists(self) -> None:
        """Verify secret_access category patterns exist."""
        from adw.security.defaults import DEFAULT_SHELL_PATTERNS, DEFAULT_FILE_PATTERNS

        all_patterns = DEFAULT_SHELL_PATTERNS + DEFAULT_FILE_PATTERNS
        secret_patterns = [p for p in all_patterns if p.category == "secret_access"]
        assert len(secret_patterns) > 0, "Should have secret_access category patterns"

    def test_all_patterns_have_valid_category(self) -> None:
        """Verify all patterns have one of the valid categories."""
        from adw.security.defaults import DEFAULT_FILE_PATTERNS, DEFAULT_SHELL_PATTERNS

        valid_categories = {"destructive", "permission", "git_dangerous", "secret_access"}
        all_patterns = DEFAULT_SHELL_PATTERNS + DEFAULT_FILE_PATTERNS

        for pattern in all_patterns:
            assert pattern.category in valid_categories, (
                f"Pattern {pattern.pattern} has invalid category: {pattern.category}"
            )
