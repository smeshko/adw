"""Unit tests for ProjectInitializer.

Tests for the minimal mode project initialization (ISS-028 additions).
"""

from pathlib import Path

from adw.config.initializer import ProjectInitializer


class TestProjectInitializerEnvTemplate:
    """Tests for .env.template creation in minimal init mode."""

    def test_creates_env_template_on_initialize(self, tmp_path: Path) -> None:
        """Initialize creates .env.template file with credential placeholders."""
        initializer = ProjectInitializer(tmp_path)
        initializer.initialize(project_type="python")

        env_template = tmp_path / ".adw" / ".env.template"
        assert env_template.exists()

        content = env_template.read_text()
        assert "LINEAR_API_KEY=" in content
        assert "LINEAR_TEAM_ID=" in content
        assert "Copy this file to .env" in content

    def test_env_template_contains_helpful_comments(self, tmp_path: Path) -> None:
        """.env.template includes documentation comments."""
        initializer = ProjectInitializer(tmp_path)
        initializer.initialize(project_type="python")

        env_template = tmp_path / ".adw" / ".env.template"
        content = env_template.read_text()

        # Should have instructions about where to find keys
        assert "Linear Settings" in content
        assert "Personal API keys" in content
        assert "gitignored" in content


class TestProjectInitializerGitignore:
    """Tests for .gitignore containing .env pattern."""

    def test_gitignore_includes_env_pattern(self, tmp_path: Path) -> None:
        """.gitignore excludes .env files from version control."""
        initializer = ProjectInitializer(tmp_path)
        initializer.initialize(project_type="python")

        gitignore = tmp_path / ".adw" / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert ".env" in content

    def test_gitignore_includes_runs_directory(self, tmp_path: Path) -> None:
        """.gitignore excludes runs/ directory."""
        initializer = ProjectInitializer(tmp_path)
        initializer.initialize(project_type="python")

        gitignore = tmp_path / ".adw" / ".gitignore"
        content = gitignore.read_text()

        assert "runs/" in content
