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
        assert "{{feature_description}}" in prompt_content
        assert "{{git_diff}}" in prompt_content
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
        assert instructions_file.exists(), f"Expected instructions at {instructions_file}"


class TestCodeReviewLoopHallucinationDetection:
    """Tests for ISS-022: Validate phase hallucination detection.

    These tests verify that instructions.xml has mandatory directives
    to detect and dismiss LLM hallucinations (false positive findings
    where Codex claims code that doesn't exist in the actual file).
    """

    @pytest.fixture
    def instructions_path(self) -> Path:
        """Return path to the code-review-loop instructions."""
        return (
            Path(__file__).parents[3]
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "validate"
            / "code-review-loop"
            / "instructions.xml"
        )

    @pytest.fixture
    def instructions_content(self, instructions_path: Path) -> str:
        """Load the instructions content."""
        return instructions_path.read_text()

    def test_instructions_mandates_file_reading(
        self, instructions_content: str
    ) -> None:
        """Instructions must have critical mandate to read files before validating.

        ISS-022: Claude was not reading files to verify Codex's code snippets.
        """
        # Must have critical directive about reading files (case-insensitive)
        content_lower = instructions_content.lower()
        assert "you must read the file" in content_lower
        assert "not optional" in content_lower

    def test_instructions_warns_about_hallucinations(
        self, instructions_content: str
    ) -> None:
        """Instructions must warn about LLM hallucinations.

        ISS-022: Claude was accepting Codex hallucinations without verification.
        """
        assert "LLM" in instructions_content or "hallucinate" in instructions_content.lower()
        assert "NEVER trust" in instructions_content or "verify" in instructions_content.lower()

    def test_instructions_has_compare_code_substep(
        self, instructions_content: str
    ) -> None:
        """Instructions must have compare-code substep for verification.

        ISS-022: Need to compare Codex's claimed code against actual file content.
        """
        assert 'substep name="compare-code"' in instructions_content

    def test_instructions_compares_claimed_vs_actual_code(
        self, instructions_content: str
    ) -> None:
        """Instructions must compare claimed code_snippet against actual_code.

        ISS-022: The key check is whether Codex's code_snippet matches reality.
        """
        assert "code_snippet" in instructions_content
        assert "actual_code" in instructions_content
        # Must explicitly compare them
        assert "Compare" in instructions_content

    def test_instructions_detects_hallucination_mismatch(
        self, instructions_content: str
    ) -> None:
        """Instructions must detect when code_snippet doesn't match actual file.

        ISS-022: This is the core hallucination detection - mismatched snippets.
        """
        # Must check for mismatch condition
        assert "does NOT appear" in instructions_content or "doesn't match" in instructions_content.lower()

    def test_instructions_classifies_hallucination_as_false_positive(
        self, instructions_content: str
    ) -> None:
        """Instructions must classify hallucinations as FALSE_POSITIVE.

        ISS-022: Hallucinated findings must be dismissed, not acted upon.
        """
        assert "FALSE_POSITIVE" in instructions_content
        # Must mention hallucination in dismissal reason
        assert "hallucination" in instructions_content.lower()

    def test_instructions_outputs_verification_results(
        self, instructions_content: str
    ) -> None:
        """Instructions must output verification results showing what was checked.

        ISS-022: Need visibility into verification process for debugging.
        """
        # Must output the claimed vs actual comparison
        assert "Claimed" in instructions_content
        assert "Actual" in instructions_content
        # Must show match/no match result
        assert "Match" in instructions_content

    def test_instructions_skips_validation_on_mismatch(
        self, instructions_content: str
    ) -> None:
        """Instructions must skip remaining validation when code doesn't match.

        ISS-022: No point validating issue logic if the code doesn't exist.
        """
        assert "Skip remaining validation" in instructions_content


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

    def test_config_has_phase_name(self, config_content: str) -> None:
        """Config should define the phase name."""
        assert "name:" in config_content
        assert "validate" in config_content.lower()
