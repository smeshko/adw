"""Unit tests for the validation prompt structure.

Tests that the validation prompt:
1. Loads correctly from the defaults
2. Contains required sections for workflow integration
3. References the code-review-loop workflow
"""

from pathlib import Path

import pytest


class TestValidatePromptStructure:
    """Tests for validate/prompt.md structure and content."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        """Return path to the validation prompt file."""
        return (
            Path(__file__).parents[3]
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "validate"
            / "prompt.md"
        )

    @pytest.fixture
    def prompt_content(self, prompt_path: Path) -> str:
        """Load the validation prompt content."""
        return prompt_path.read_text()

    def test_prompt_file_exists(self, prompt_path: Path) -> None:
        """Validation prompt file should exist in defaults."""
        assert prompt_path.exists(), f"Expected validate prompt at {prompt_path}"

    def test_prompt_has_validation_phase_header(self, prompt_content: str) -> None:
        """Prompt should start with '# Validation Phase' header."""
        assert "# Validation Phase" in prompt_content

    def test_prompt_has_context_section(self, prompt_content: str) -> None:
        """Prompt should have a Context section with template variables."""
        assert "## Context" in prompt_content
        assert "{{context}}" in prompt_content
        assert "{{artifacts.build.diff}}" in prompt_content
        assert "{{project_config}}" in prompt_content

    def test_prompt_has_instructions_section(self, prompt_content: str) -> None:
        """Prompt should have an Instructions section."""
        assert "## Instructions" in prompt_content

    def test_prompt_references_workflow_engine(self, prompt_content: str) -> None:
        """Prompt should reference the shared workflow engine."""
        assert "{{shared:workflow.xml}}" in prompt_content

    def test_prompt_references_code_review_loop_workflow(
        self, prompt_content: str
    ) -> None:
        """Prompt should reference the code-review-loop workflow config."""
        assert "code-review-loop/workflow.yaml" in prompt_content

    def test_prompt_references_code_review_loop_instructions(
        self, prompt_content: str
    ) -> None:
        """Prompt should reference the code-review-loop instructions."""
        assert "code-review-loop/instructions.xml" in prompt_content

    def test_prompt_has_critical_steps(self, prompt_content: str) -> None:
        """Prompt should have critical execution steps."""
        assert "<steps" in prompt_content
        assert "CRITICAL" in prompt_content


class TestCodeReviewLoopWorkflow:
    """Tests for the code-review-loop workflow files."""

    @pytest.fixture
    def workflow_dir(self) -> Path:
        """Return path to the code-review-loop directory."""
        return (
            Path(__file__).parents[3]
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "validate"
            / "code-review-loop"
        )

    def test_workflow_yaml_exists(self, workflow_dir: Path) -> None:
        """Workflow YAML file should exist."""
        workflow_file = workflow_dir / "workflow.yaml"
        assert workflow_file.exists(), f"Expected workflow at {workflow_file}"

    def test_instructions_xml_exists(self, workflow_dir: Path) -> None:
        """Instructions XML file should exist."""
        instructions_file = workflow_dir / "instructions.xml"
        assert instructions_file.exists(), (
            f"Expected instructions at {instructions_file}"
        )


class TestValidateConfigYaml:
    """Tests for the validate command config.yaml."""

    @pytest.fixture
    def config_path(self) -> Path:
        """Return path to the validate config file."""
        return (
            Path(__file__).parents[3]
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "validate"
            / "config.yaml"
        )

    @pytest.fixture
    def config_content(self, config_path: Path) -> str:
        """Load the config content."""
        return config_path.read_text()

    def test_config_file_exists(self, config_path: Path) -> None:
        """Config file should exist."""
        assert config_path.exists(), f"Expected config at {config_path}"

    def test_config_references_validate_phase(self, config_content: str) -> None:
        """Config should reference the validate phase."""
        assert "validate" in config_content.lower()
