"""Unit tests for the unified validation prompt (Story 16.2).

Tests that the validation prompt:
1. Loads correctly from the defaults
2. Contains all required sections
3. Supports variable substitution
4. Defines the expected output schema
"""

from pathlib import Path

import pytest

from adw.commands import TemplateEngine


class TestValidatePromptStructure:
    """Tests for validate/prompt.md structure and content."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        """Return path to the validation prompt file."""
        return Path(__file__).parents[3] / "src" / "adw" / "defaults" / "commands" / "validate" / "prompt.md"

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

    def test_prompt_has_your_task_section(self, prompt_content: str) -> None:
        """Prompt should have a 'Your Task' section."""
        assert "## Your Task" in prompt_content

    def test_prompt_has_run_tests_instruction(self, prompt_content: str) -> None:
        """Prompt should instruct LLM to run tests."""
        assert "Run Tests" in prompt_content

    def test_prompt_has_run_linters_instruction(self, prompt_content: str) -> None:
        """Prompt should instruct LLM to run linters."""
        assert "Run Linters" in prompt_content

    def test_prompt_has_code_review_instruction(self, prompt_content: str) -> None:
        """Prompt should instruct LLM to perform code review."""
        assert "Code Review" in prompt_content

    def test_prompt_has_output_format_section(self, prompt_content: str) -> None:
        """Prompt should have an Output Format section."""
        assert "## Output Format" in prompt_content

    def test_prompt_has_rules_section(self, prompt_content: str) -> None:
        """Prompt should have a Rules section."""
        assert "## Rules" in prompt_content

    def test_prompt_has_single_fix_attempt_rule(self, prompt_content: str) -> None:
        """Prompt should enforce single fix attempt (AC: max one fix attempt)."""
        assert "Single Fix Attempt" in prompt_content

    def test_prompt_has_no_looping_rule(self, prompt_content: str) -> None:
        """Prompt should forbid looping (AC: no fix-test-fix loops)."""
        assert "No Looping" in prompt_content

    def test_prompt_has_all_or_nothing_rule(self, prompt_content: str) -> None:
        """Prompt should enforce all-or-nothing fixes (AC: non-fixable = no fixes)."""
        assert "All or Nothing" in prompt_content

    def test_prompt_has_examples_section(self, prompt_content: str) -> None:
        """Prompt should have an Examples section."""
        assert "## Examples" in prompt_content


class TestValidatePromptOutputSchema:
    """Tests for the output schema defined in the validation prompt."""

    @pytest.fixture
    def prompt_content(self) -> str:
        """Load the validation prompt content."""
        prompt_path = Path(__file__).parents[3] / "src" / "adw" / "defaults" / "commands" / "validate" / "prompt.md"
        return prompt_path.read_text()

    def test_schema_has_passed_field(self, prompt_content: str) -> None:
        """Schema should define 'passed' boolean field."""
        assert '"passed":' in prompt_content
        assert "**`passed`**" in prompt_content

    def test_schema_has_tests_passed_field(self, prompt_content: str) -> None:
        """Schema should define 'tests_passed' boolean field."""
        assert '"tests_passed":' in prompt_content
        assert "**`tests_passed`**" in prompt_content

    def test_schema_has_code_review_passed_field(self, prompt_content: str) -> None:
        """Schema should define 'code_review_passed' boolean field."""
        assert '"code_review_passed":' in prompt_content
        assert "**`code_review_passed`**" in prompt_content

    def test_schema_has_issues_fixed_field(self, prompt_content: str) -> None:
        """Schema should define 'issues_fixed' array field."""
        assert '"issues_fixed":' in prompt_content
        assert "**`issues_fixed`**" in prompt_content

    def test_schema_has_issues_remaining_field(self, prompt_content: str) -> None:
        """Schema should define 'issues_remaining' array field."""
        assert '"issues_remaining":' in prompt_content
        assert "**`issues_remaining`**" in prompt_content

    def test_schema_has_summary_field(self, prompt_content: str) -> None:
        """Schema should define 'summary' string field."""
        assert '"summary":' in prompt_content
        assert "**`summary`**" in prompt_content


class TestValidatePromptAutoFixRules:
    """Tests for auto-fix determination rules in the validation prompt."""

    @pytest.fixture
    def prompt_content(self) -> str:
        """Load the validation prompt content."""
        prompt_path = Path(__file__).parents[3] / "src" / "adw" / "defaults" / "commands" / "validate" / "prompt.md"
        return prompt_path.read_text()

    def test_has_auto_fixable_section(self, prompt_content: str) -> None:
        """Prompt should define auto-fixable issues."""
        assert "Auto-fixable issues" in prompt_content or "auto-fixable" in prompt_content.lower()

    def test_has_non_auto_fixable_section(self, prompt_content: str) -> None:
        """Prompt should define non-auto-fixable issues."""
        assert "Non-auto-fixable issues" in prompt_content or "non-auto-fixable" in prompt_content.lower()

    def test_fixable_includes_null_checks(self, prompt_content: str) -> None:
        """Auto-fixable should include null/undefined checks."""
        assert "null" in prompt_content.lower()

    def test_fixable_includes_error_handling(self, prompt_content: str) -> None:
        """Auto-fixable should include error handling."""
        assert "error handling" in prompt_content.lower()

    def test_fixable_includes_type_annotations(self, prompt_content: str) -> None:
        """Auto-fixable should include type annotations."""
        assert "type annotation" in prompt_content.lower()

    def test_non_fixable_includes_design_decisions(self, prompt_content: str) -> None:
        """Non-auto-fixable should include design decisions."""
        assert "design decision" in prompt_content.lower()

    def test_non_fixable_includes_architecture(self, prompt_content: str) -> None:
        """Non-auto-fixable should include architecture changes."""
        assert "architecture" in prompt_content.lower()

    def test_non_fixable_includes_requirements(self, prompt_content: str) -> None:
        """Non-auto-fixable should include unclear requirements."""
        assert "requirement" in prompt_content.lower()


class TestValidatePromptVariableSubstitution:
    """Tests for variable substitution in the validation prompt."""

    @pytest.fixture
    def prompt_content(self) -> str:
        """Load the validation prompt content."""
        prompt_path = Path(__file__).parents[3] / "src" / "adw" / "defaults" / "commands" / "validate" / "prompt.md"
        return prompt_path.read_text()

    def test_can_render_with_template_engine(self, prompt_content: str) -> None:
        """Template engine should be able to render the prompt."""
        engine = TemplateEngine()
        context = {
            "feature_description": "Add user authentication",
            "git_diff": "diff --git a/src/auth.py b/src/auth.py\n+def login(user):\n+    pass",
            "project_config": '{"validation": {"test_command": "pytest"}}',
        }
        rendered = engine.render(prompt_content, context)

        # Variables should be substituted
        assert "Add user authentication" in rendered
        assert "diff --git" in rendered
        assert "test_command" in rendered

        # No unsubstituted template variables for the ones we provided
        assert "{{feature_description}}" not in rendered
        assert "{{git_diff}}" not in rendered
        assert "{{project_config}}" not in rendered

    def test_renders_empty_values_gracefully(self, prompt_content: str) -> None:
        """Template engine should handle empty values."""
        engine = TemplateEngine()
        context = {
            "feature_description": "",
            "git_diff": "",
            "project_config": "",
        }
        rendered = engine.render(prompt_content, context)

        # Should render without errors
        assert "# Validation Phase" in rendered
        # Empty values become empty strings
        assert "{{feature_description}}" not in rendered
        assert "{{project_config}}" not in rendered


class TestValidatePromptExamples:
    """Tests for examples in the validation prompt."""

    @pytest.fixture
    def prompt_content(self) -> str:
        """Load the validation prompt content."""
        prompt_path = Path(__file__).parents[3] / "src" / "adw" / "defaults" / "commands" / "validate" / "prompt.md"
        return prompt_path.read_text()

    def test_has_passing_example(self, prompt_content: str) -> None:
        """Prompt should include example of all tests passing."""
        # Check for a passing scenario example
        assert '"passed": true' in prompt_content

    def test_has_failing_example(self, prompt_content: str) -> None:
        """Prompt should include example of failed validation."""
        # Check for a failing scenario example
        assert '"passed": false' in prompt_content

    def test_has_issues_fixed_example(self, prompt_content: str) -> None:
        """Prompt should include example with issues being fixed."""
        # Check for example showing fixed issues
        assert "issues_fixed" in prompt_content
        assert "Fixed" in prompt_content or "fixed" in prompt_content

    def test_has_issues_remaining_example(self, prompt_content: str) -> None:
        """Prompt should include example with remaining issues."""
        # Check for example showing remaining issues
        assert "issues_remaining" in prompt_content
