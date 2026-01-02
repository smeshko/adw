"""Unit tests for escape_feature_description function.

Tests for special character escaping in feature descriptions.
"""

import pytest

from adw.commands.template import escape_feature_description


class TestEscapeFeatureDescription:
    """Tests for escape_feature_description function."""

    def test_escapes_double_quotes(self) -> None:
        """Test that double quotes are escaped."""
        result = escape_feature_description('Add "quoted" text')
        assert '\\"' in result
        assert 'quoted' in result

    def test_escapes_backslashes(self) -> None:
        """Test that backslashes are doubled."""
        result = escape_feature_description("Path C:\\Users\\test")
        assert "\\\\" in result

    def test_escapes_dollar_signs(self) -> None:
        """Test that dollar signs are escaped."""
        result = escape_feature_description("Add $VAR support")
        assert "\\$VAR" in result
        assert "$" not in result.replace("\\$", "")

    def test_escapes_backticks(self) -> None:
        """Test that backticks are escaped."""
        result = escape_feature_description("Run `command` inline")
        assert "\\`" in result

    def test_handles_plain_text(self) -> None:
        """Test that plain text without special chars is unchanged."""
        description = "Add user authentication feature"
        result = escape_feature_description(description)
        assert result == description

    def test_handles_empty_string(self) -> None:
        """Test that empty string returns empty string."""
        result = escape_feature_description("")
        assert result == ""

    def test_handles_multiple_special_chars(self) -> None:
        """Test escaping multiple special characters together."""
        result = escape_feature_description('Run "$HOME/bin" with `pwd`')
        assert "\\$HOME" in result
        assert '\\"/bin\\"' in result or '\\"' in result
        assert "\\`pwd\\`" in result

    def test_backslash_escaped_first(self) -> None:
        """Test that backslashes are escaped before other chars.

        This prevents double-escaping issues where \" becomes \\\".
        """
        result = escape_feature_description('Add "\\ path"')
        # Should be: Add \"\\\\ path\" (escaped quote, escaped backslash)
        assert '\\\\"' not in result  # No triple backslash before quote
        assert '\\\\ ' in result  # Double backslash for the actual backslash

    def test_preserves_unicode(self) -> None:
        """Test that unicode characters are preserved."""
        description = "Add 日本語 support and emoji 🚀"
        result = escape_feature_description(description)
        assert "日本語" in result
        assert "🚀" in result

    def test_preserves_newlines(self) -> None:
        """Test that newlines are preserved."""
        description = "Line 1\nLine 2"
        result = escape_feature_description(description)
        assert "\n" in result

    def test_common_git_commit_style(self) -> None:
        """Test escaping git commit style descriptions."""
        result = escape_feature_description("feat(auth): add OAuth2 login")
        # Parentheses and colons should be preserved
        assert "feat(auth):" in result

    def test_shell_command_injection_patterns(self) -> None:
        """Test that shell injection patterns are escaped."""
        # These patterns should be safely escaped
        result = escape_feature_description("$(rm -rf /)")
        assert "\\$(rm -rf /)" in result

        result = escape_feature_description("`rm -rf /`")
        assert "\\`rm -rf /\\`" in result
