"""Tests for config models (ProjectConfig, LLMConfig, PhaseConfig)."""

import pytest
from pydantic import ValidationError

from adw.models import (
    GitConfig,
    HookConfig,
    LLMConfig,
    PhaseConfig,
    ProjectConfig,
    WorktreeConfig,
)


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_defaults(self) -> None:
        """LLMConfig has sensible defaults."""
        config = LLMConfig()
        assert config.path == "claude"
        assert config.timeout_seconds == 300
        assert config.max_retries == 3
        assert config.model is None

    def test_custom_values(self) -> None:
        """LLMConfig accepts custom values."""
        config = LLMConfig(
            path="/usr/local/bin/claude",
            timeout_seconds=600,
            max_retries=5,
            model="claude-3-opus",
        )
        assert config.path == "/usr/local/bin/claude"
        assert config.timeout_seconds == 600
        assert config.max_retries == 5
        assert config.model == "claude-3-opus"


class TestPhaseConfig:
    """Tests for PhaseConfig model."""

    def test_defaults(self) -> None:
        """PhaseConfig has sensible defaults."""
        config = PhaseConfig()
        assert config.enabled is True
        assert config.timeout_seconds is None
        assert config.pre_hook is None
        assert config.post_hook is None

    def test_with_hooks(self) -> None:
        """PhaseConfig with hooks configured."""
        config = PhaseConfig(
            enabled=True,
            timeout_seconds=120,
            pre_hook="npm run lint",
            post_hook="npm run format",
        )
        assert config.timeout_seconds == 120
        assert config.pre_hook == "npm run lint"
        assert config.post_hook == "npm run format"

    def test_disabled_phase(self) -> None:
        """PhaseConfig can disable a phase."""
        config = PhaseConfig(enabled=False)
        assert config.enabled is False


class TestHookConfig:
    """Tests for HookConfig model."""

    def test_defaults(self) -> None:
        """HookConfig has sensible defaults."""
        config = HookConfig()
        assert config.shell == "/bin/bash"
        assert config.timeout_seconds == 60

    def test_custom_shell(self) -> None:
        """HookConfig accepts custom shell."""
        config = HookConfig(
            shell="/bin/zsh",
            timeout_seconds=120,
        )
        assert config.shell == "/bin/zsh"
        assert config.timeout_seconds == 120


class TestGitConfig:
    """Tests for GitConfig model."""

    def test_defaults(self) -> None:
        """GitConfig has sensible defaults."""
        config = GitConfig()
        assert config.enabled is False
        assert config.branch_prefix == "feature/"
        assert config.auto_commit is True
        assert config.commit_template is None

    def test_enabled_with_custom_prefix(self) -> None:
        """GitConfig accepts custom prefix."""
        config = GitConfig(
            enabled=True,
            branch_prefix="feat/",
        )
        assert config.enabled is True
        assert config.branch_prefix == "feat/"

    def test_auto_commit_disabled(self) -> None:
        """GitConfig can disable auto-commit."""
        config = GitConfig(
            enabled=True,
            auto_commit=False,
        )
        assert config.enabled is True
        assert config.auto_commit is False

    def test_custom_commit_template(self) -> None:
        """GitConfig accepts custom commit template."""
        template = "{phase}: {feature} [{run_id}]"
        config = GitConfig(
            enabled=True,
            commit_template=template,
        )
        assert config.commit_template == template

    def test_skip_hooks_default_false(self) -> None:
        """GitConfig defaults skip_hooks to False."""
        config = GitConfig()
        assert config.skip_hooks is False

    def test_skip_hooks_enabled(self) -> None:
        """GitConfig can enable skip_hooks."""
        config = GitConfig(
            enabled=True,
            skip_hooks=True,
        )
        assert config.skip_hooks is True


class TestWorktreeConfig:
    """Tests for WorktreeConfig model."""

    def test_defaults(self) -> None:
        """WorktreeConfig has sensible defaults."""
        config = WorktreeConfig()
        assert config.enabled is True
        assert config.base_dir == "trees"
        assert config.preserve_on_failure is True
        assert config.cleanup_branch_on_remove is False

    def test_disabled(self) -> None:
        """WorktreeConfig can be disabled."""
        config = WorktreeConfig(enabled=False)
        assert config.enabled is False

    def test_custom_base_dir(self) -> None:
        """WorktreeConfig accepts custom base_dir."""
        config = WorktreeConfig(base_dir=".worktrees")
        assert config.base_dir == ".worktrees"

    def test_preserve_on_failure_false(self) -> None:
        """WorktreeConfig can disable preserve_on_failure."""
        config = WorktreeConfig(preserve_on_failure=False)
        assert config.preserve_on_failure is False

    def test_cleanup_branch_on_remove_true(self) -> None:
        """WorktreeConfig can enable branch cleanup."""
        config = WorktreeConfig(cleanup_branch_on_remove=True)
        assert config.cleanup_branch_on_remove is True

    def test_all_custom_values(self) -> None:
        """WorktreeConfig accepts all custom values."""
        config = WorktreeConfig(
            enabled=False,
            base_dir="my-worktrees",
            preserve_on_failure=False,
            cleanup_branch_on_remove=True,
        )
        assert config.enabled is False
        assert config.base_dir == "my-worktrees"
        assert config.preserve_on_failure is False
        assert config.cleanup_branch_on_remove is True

    def test_preserve_artifacts_defaults(self) -> None:
        """WorktreeConfig has default preserve_artifacts list."""
        config = WorktreeConfig()
        assert config.preserve_artifacts == ["context.json", "logs", "artifacts", "llm"]

    def test_preserve_artifacts_custom(self) -> None:
        """WorktreeConfig accepts custom preserve_artifacts list."""
        config = WorktreeConfig(
            preserve_artifacts=["context.json", "logs", "custom.json"]
        )
        assert config.preserve_artifacts == ["context.json", "logs", "custom.json"]

    def test_artifact_manifest_file_default(self) -> None:
        """WorktreeConfig has default artifact_manifest_file."""
        config = WorktreeConfig()
        assert config.artifact_manifest_file == "worktree-artifacts.json"

    def test_artifact_manifest_file_custom(self) -> None:
        """WorktreeConfig accepts custom artifact_manifest_file."""
        config = WorktreeConfig(artifact_manifest_file="custom-manifest.json")
        assert config.artifact_manifest_file == "custom-manifest.json"

    def test_port_range_defaults(self) -> None:
        """WorktreeConfig has default port range settings."""
        config = WorktreeConfig()
        assert config.port_range.backend_start == 9100
        assert config.port_range.frontend_start == 9200
        assert config.max_concurrent == 15

    def test_custom_port_range(self) -> None:
        """WorktreeConfig accepts custom port range."""
        from adw.models.config import PortRangeConfig

        config = WorktreeConfig(
            port_range=PortRangeConfig(
                backend_start=8000,
                frontend_start=8100,
            ),
            max_concurrent=10,
        )
        assert config.port_range.backend_start == 8000
        assert config.port_range.frontend_start == 8100
        assert config.max_concurrent == 10


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_from_yaml_minimal(self) -> None:
        """ProjectConfig loads from minimal YAML."""
        yaml_content = """
name: my-project
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.name == "my-project"
        assert config.language == "python"
        assert config.framework is None
        assert config.platform == "cli"

    def test_from_yaml_complete(self) -> None:
        """ProjectConfig loads from complete YAML."""
        yaml_content = """
name: my-api
language: python
framework: fastapi
platform: api
test_command: pytest
build_command: python -m build
llm:
  path: /usr/local/bin/claude
  timeout_seconds: 600
  max_retries: 5
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.name == "my-api"
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.platform == "api"
        assert config.test_command == "pytest"
        assert config.build_command == "python -m build"
        assert config.llm.path == "/usr/local/bin/claude"
        assert config.llm.timeout_seconds == 600
        assert config.llm.max_retries == 5

    def test_from_yaml_missing_name(self) -> None:
        """ProjectConfig validates required name field."""
        yaml_content = """
language: python
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        assert "Missing required fields: name" in str(exc_info.value)

    def test_from_yaml_missing_language(self) -> None:
        """ProjectConfig validates required language field."""
        yaml_content = """
name: my-project
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        assert "Missing required fields: language" in str(exc_info.value)

    def test_from_yaml_missing_both_required(self) -> None:
        """ProjectConfig validates both required fields."""
        yaml_content = """
framework: fastapi
platform: api
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        error_str = str(exc_info.value)
        assert "name" in error_str
        assert "language" in error_str

    def test_defaults_for_optional_fields(self) -> None:
        """ProjectConfig uses defaults for optional fields."""
        yaml_content = """
name: minimal
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)

        # Check defaults
        assert config.platform == "cli"
        assert config.test_command is None
        assert config.build_command is None
        assert config.framework is None

        # Check nested defaults
        assert config.llm.path == "claude"
        assert config.llm.timeout_seconds == 300
        assert config.hooks.shell == "/bin/bash"
        assert config.git.enabled is False
        assert config.git.branch_prefix == "feature/"

    def test_with_git_config(self) -> None:
        """ProjectConfig with git integration enabled."""
        yaml_content = """
name: git-enabled
language: python
git:
  enabled: true
  branch_prefix: "feat/"
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.git.enabled is True
        assert config.git.branch_prefix == "feat/"

    def test_with_git_commit_config(self) -> None:
        """ProjectConfig with git auto-commit configuration."""
        yaml_content = """
name: git-commit-enabled
language: python
git:
  enabled: true
  auto_commit: true
  commit_template: "{phase}: {feature}"
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.git.enabled is True
        assert config.git.auto_commit is True
        assert config.git.commit_template == "{phase}: {feature}"

    def test_with_git_auto_commit_disabled(self) -> None:
        """ProjectConfig with auto-commit disabled."""
        yaml_content = """
name: git-no-commit
language: python
git:
  enabled: true
  auto_commit: false
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.git.enabled is True
        assert config.git.auto_commit is False

    def test_with_worktree_config(self) -> None:
        """ProjectConfig with worktree isolation enabled."""
        yaml_content = """
name: worktree-enabled
language: python
worktree:
  enabled: true
  base_dir: ".worktrees"
  preserve_on_failure: false
  cleanup_branch_on_remove: true
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.worktree.enabled is True
        assert config.worktree.base_dir == ".worktrees"
        assert config.worktree.preserve_on_failure is False
        assert config.worktree.cleanup_branch_on_remove is True

    def test_worktree_defaults_in_project_config(self) -> None:
        """ProjectConfig has worktree with default values."""
        yaml_content = """
name: minimal-project
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.worktree.enabled is True
        assert config.worktree.base_dir == "trees"
        assert config.worktree.preserve_on_failure is True
        assert config.worktree.cleanup_branch_on_remove is False

    def test_with_phase_config(self) -> None:
        """ProjectConfig with phase-specific configuration."""
        yaml_content = """
name: phased
language: python
phases:
  plan:
    enabled: true
    timeout_seconds: 120
  code:
    enabled: true
    pre_hook: npm run lint
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert "plan" in config.phases
        assert config.phases["plan"].timeout_seconds == 120
        assert config.phases["code"].pre_hook == "npm run lint"

    def test_empty_yaml_fails(self) -> None:
        """Empty YAML raises ValidationError."""
        with pytest.raises(ValidationError):
            ProjectConfig.from_yaml("")

    def test_validation_error_messages_clear(self) -> None:
        """Validation errors have clear field-level messages."""
        yaml_content = """
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)

        # Check that the error message mentions the missing fields
        error_str = str(exc_info.value)
        assert "name" in error_str
        assert "language" in error_str
