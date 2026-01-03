"""Tests for alternative suggestions module.

Verifies that suggestions are properly formatted for user output
including alternatives and override instructions.
"""

import pytest


class TestSuggestionFormatter:
    """Tests for SuggestionFormatter class."""

    def test_format_single_match(self) -> None:
        """Test formatting a single pattern match."""
        from adw.security.patterns import PatternMatch
        from adw.security.suggestions import SuggestionFormatter

        match = PatternMatch(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            severity="critical",
            category="destructive",
            alternative="Use specific paths: rm -rf ./node_modules",
            allowed=False,
        )
        formatter = SuggestionFormatter()
        result = formatter.format_single(match)

        assert "Recursive delete" in result
        assert "rm -rf ./node_modules" in result

    def test_format_includes_severity(self) -> None:
        """Test that formatted output includes severity."""
        from adw.security.patterns import PatternMatch
        from adw.security.suggestions import SuggestionFormatter

        match = PatternMatch(
            pattern=r"chmod\s+777",
            description="World-writable permissions",
            severity="warning",
            category="permission",
            alternative="Use chmod 755 instead",
            allowed=False,
        )
        formatter = SuggestionFormatter()
        result = formatter.format_single(match)

        assert "warning" in result.lower() or "WARNING" in result

    def test_format_includes_override_instruction(self) -> None:
        """Test that formatted output includes override instruction."""
        from adw.security.patterns import PatternMatch
        from adw.security.suggestions import SuggestionFormatter

        match = PatternMatch(
            pattern=r"git\s+push\s+--force",
            description="Force push",
            severity="warning",
            category="git_dangerous",
            alternative="Use --force-with-lease",
            allowed=False,
        )
        formatter = SuggestionFormatter()
        result = formatter.format_single(match)

        assert "--allow-dangerous" in result

    def test_format_multiple_matches(self) -> None:
        """Test formatting multiple pattern matches."""
        from adw.security.patterns import PatternMatch
        from adw.security.suggestions import SuggestionFormatter

        matches = [
            PatternMatch(
                pattern=r"rm\s+-rf",
                description="Recursive delete",
                severity="critical",
                category="destructive",
                alternative="Use specific paths",
                allowed=False,
            ),
            PatternMatch(
                pattern=r"chmod\s+777",
                description="World-writable",
                severity="warning",
                category="permission",
                alternative="Use chmod 755",
                allowed=False,
            ),
        ]
        formatter = SuggestionFormatter()
        result = formatter.format_multiple(matches)

        assert "Recursive delete" in result
        assert "World-writable" in result

    def test_format_empty_list(self) -> None:
        """Test formatting empty list returns empty string."""
        from adw.security.suggestions import SuggestionFormatter

        formatter = SuggestionFormatter()
        result = formatter.format_multiple([])

        assert result == ""

    def test_get_override_instruction(self) -> None:
        """Test getting the override instruction."""
        from adw.security.suggestions import get_override_instruction

        instruction = get_override_instruction()
        assert "--allow-dangerous" in instruction
        assert "adw" in instruction.lower()


class TestCategoryExamples:
    """Tests for category-specific examples."""

    def test_get_destructive_examples(self) -> None:
        """Test getting examples for destructive category."""
        from adw.security.suggestions import get_category_examples

        examples = get_category_examples("destructive")
        assert len(examples) > 0
        assert any("rm" in ex.lower() for ex in examples)

    def test_get_permission_examples(self) -> None:
        """Test getting examples for permission category."""
        from adw.security.suggestions import get_category_examples

        examples = get_category_examples("permission")
        assert len(examples) > 0
        assert any("chmod" in ex.lower() for ex in examples)

    def test_get_git_dangerous_examples(self) -> None:
        """Test getting examples for git_dangerous category."""
        from adw.security.suggestions import get_category_examples

        examples = get_category_examples("git_dangerous")
        assert len(examples) > 0
        assert any("git" in ex.lower() for ex in examples)

    def test_get_secret_access_examples(self) -> None:
        """Test getting examples for secret_access category."""
        from adw.security.suggestions import get_category_examples

        examples = get_category_examples("secret_access")
        assert len(examples) > 0
        assert any(".env" in ex.lower() for ex in examples)

    def test_unknown_category_returns_empty(self) -> None:
        """Test unknown category returns empty list."""
        from adw.security.suggestions import get_category_examples

        examples = get_category_examples("unknown")
        assert examples == []
