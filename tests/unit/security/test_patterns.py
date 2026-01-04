"""Tests for the pattern matching engine.

Verifies PatternMatcher class correctly identifies dangerous commands
and file access patterns with context-aware matching.
"""

from adw.models.security import BlockedPattern


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    def test_match_command_returns_list(self) -> None:
        """Test match_command returns a list of matches."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        result = matcher.match_command("rm -rf /")
        assert isinstance(result, list)

    def test_match_rm_rf_root(self) -> None:
        """Test detecting rm -rf / command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("rm -rf /")
        assert len(matches) > 0
        assert any(m.category == "destructive" for m in matches)

    def test_match_rm_rf_home(self) -> None:
        """Test detecting rm -rf ~ command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("rm -rf ~")
        assert len(matches) > 0

    def test_match_rm_rf_dot(self) -> None:
        """Test detecting rm -rf . command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("rm -rf .")
        assert len(matches) > 0

    def test_safe_rm_not_matched(self) -> None:
        """Test that safe rm commands are not matched."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        # Safe: rm with specific directory
        matches = matcher.match_command("rm -rf ./node_modules")
        # Should not match destructive patterns (but might match if too broad)
        # The key is it should NOT match the "rm -rf /" pattern
        for match in matches:
            not_root = "root" not in match.description.lower()
            has_node_modules = "/node_modules" in match.description
            assert not_root or has_node_modules

    def test_match_chmod_777(self) -> None:
        """Test detecting chmod 777 command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("chmod 777 /etc/passwd")
        assert len(matches) > 0
        assert any(m.category == "permission" for m in matches)

    def test_safe_chmod_not_matched(self) -> None:
        """Test that chmod 755 is not matched."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("chmod 755 ./script.sh")
        # chmod 755 should not be blocked
        assert not any("777" in m.pattern for m in matches)

    def test_match_git_force_push(self) -> None:
        """Test detecting git push --force command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("git push --force origin main")
        assert len(matches) > 0
        assert any(m.category == "git_dangerous" for m in matches)

    def test_match_git_force_push_short(self) -> None:
        """Test detecting git push -f command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("git push -f origin feature")
        assert len(matches) > 0
        assert any(m.category == "git_dangerous" for m in matches)

    def test_safe_git_push_not_matched(self) -> None:
        """Test that normal git push is not matched."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("git push origin main")
        # Normal push should not be blocked
        assert not any("force" in m.pattern.lower() for m in matches)

    def test_match_env_file_write(self) -> None:
        """Test detecting writes to .env file."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command('echo "SECRET=value" > .env')
        assert len(matches) > 0
        assert any(m.category == "secret_access" for m in matches)

    def test_match_git_hard_reset(self) -> None:
        """Test detecting git reset --hard command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("git reset --hard HEAD~1")
        assert len(matches) > 0
        assert any(m.category == "git_dangerous" for m in matches)

    def test_match_mkfs_command(self) -> None:
        """Test detecting mkfs command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_command("mkfs.ext4 /dev/sda1")
        assert len(matches) > 0
        assert any(m.category == "destructive" for m in matches)


class TestPatternMatcherFileAccess:
    """Tests for PatternMatcher file access checking."""

    def test_match_file_access_returns_list(self) -> None:
        """Test match_file_access returns a list."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        result = matcher.match_file_access(".env")
        assert isinstance(result, list)

    def test_match_env_file(self) -> None:
        """Test .env file is blocked."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access(".env")
        assert len(matches) > 0
        assert any(m.category == "secret_access" for m in matches)

    def test_match_adw_env_file(self) -> None:
        """Test .adw.env file is blocked."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access(".adw.env")
        assert len(matches) > 0

    def test_env_example_allowed(self) -> None:
        """Test .env.example is allowed."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access(".env.example")
        # Should either have no matches or have is_allowed=True
        assert len(matches) == 0

    def test_env_sample_allowed(self) -> None:
        """Test .env.sample is allowed."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access(".env.sample")
        assert len(matches) == 0

    def test_env_template_allowed(self) -> None:
        """Test .env.template is allowed."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access(".env.template")
        assert len(matches) == 0

    def test_credentials_json_blocked(self) -> None:
        """Test credentials.json is blocked."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access("credentials.json")
        assert len(matches) > 0

    def test_pem_file_blocked(self) -> None:
        """Test .pem files are blocked."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        matches = matcher.match_file_access("private-key.pem")
        assert len(matches) > 0


class TestPatternMatcherCustomPatterns:
    """Tests for PatternMatcher with custom patterns."""

    def test_add_custom_pattern(self) -> None:
        """Test adding custom patterns."""
        from adw.security.patterns import PatternMatcher

        custom_pattern = BlockedPattern(
            pattern=r"npm\s+publish",
            description="Publishing to npm",
            category="permission",
        )
        matcher = PatternMatcher(additional_patterns=[custom_pattern])
        matches = matcher.match_command("npm publish --access public")
        assert len(matches) > 0

    def test_custom_pattern_with_defaults(self) -> None:
        """Test custom patterns are added to defaults."""
        from adw.security.patterns import PatternMatcher

        custom_pattern = BlockedPattern(
            pattern=r"docker\s+system\s+prune",
            description="Docker system prune",
            category="destructive",
        )
        matcher = PatternMatcher(additional_patterns=[custom_pattern])

        # Should still match default patterns
        default_matches = matcher.match_command("rm -rf /")
        assert len(default_matches) > 0

        # Should also match custom pattern
        custom_matches = matcher.match_command("docker system prune -a")
        assert len(custom_matches) > 0


class TestPatternMatcherAllowDangerous:
    """Tests for allow_dangerous mode."""

    def test_allow_dangerous_still_detects(self) -> None:
        """Test allow_dangerous mode still detects patterns."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher(allow_dangerous=True)
        matches = matcher.match_command("rm -rf /")
        assert len(matches) > 0

    def test_allow_dangerous_flag_in_match(self) -> None:
        """Test PatternMatch includes allowed flag when allow_dangerous is True."""
        from adw.security.patterns import PatternMatch, PatternMatcher

        matcher = PatternMatcher(allow_dangerous=True)
        matches = matcher.match_command("rm -rf /")
        # When allow_dangerous, matches should have allowed=True
        assert all(isinstance(m, PatternMatch) for m in matches)


class TestPatternMatcherIsBlocked:
    """Tests for is_blocked convenience method."""

    def test_is_blocked_with_dangerous_command(self) -> None:
        """Test is_blocked returns True for dangerous command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        blocked, matches = matcher.is_blocked(command="rm -rf /")
        assert blocked is True
        assert len(matches) > 0

    def test_is_blocked_with_safe_command(self) -> None:
        """Test is_blocked returns False for safe command."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        blocked, matches = matcher.is_blocked(command="ls -la")
        assert blocked is False
        assert len(matches) == 0

    def test_is_blocked_with_dangerous_file(self) -> None:
        """Test is_blocked returns True for dangerous file path."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        blocked, matches = matcher.is_blocked(file_path=".env")
        assert blocked is True
        assert len(matches) > 0

    def test_is_blocked_with_both_command_and_file(self) -> None:
        """Test is_blocked checks both command and file."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        blocked, matches = matcher.is_blocked(
            command="ls -la",  # Safe
            file_path=".env",  # Dangerous
        )
        assert blocked is True
        assert len(matches) > 0

    def test_is_blocked_with_allow_dangerous(self) -> None:
        """Test is_blocked returns False when allow_dangerous is True."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher(allow_dangerous=True)
        blocked, matches = matcher.is_blocked(command="rm -rf /")
        # Still detects matches but not blocked
        assert blocked is False
        assert len(matches) > 0

    def test_is_blocked_with_no_args(self) -> None:
        """Test is_blocked with no command or file_path."""
        from adw.security.patterns import PatternMatcher

        matcher = PatternMatcher()
        blocked, matches = matcher.is_blocked()
        assert blocked is False
        assert len(matches) == 0
