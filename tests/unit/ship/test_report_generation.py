"""Tests for ship report generation in ship phase instructions.

This story (15.7) implements ship report generation via LLM instructions in
instructions.xml Step 7. These tests validate the instruction structure and content
since the actual execution is LLM-driven.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


@pytest.fixture
def ship_instructions_path() -> Path:
    """Path to ship phase instructions.xml."""
    return Path(__file__).parents[3] / "src/adw/defaults/commands/ship/instructions.xml"


@pytest.fixture
def instructions_xml(ship_instructions_path: Path) -> ET.Element:
    """Parse ship instructions.xml as XML element tree."""
    tree = ET.parse(ship_instructions_path)
    return tree.getroot()


@pytest.fixture
def instructions_text(ship_instructions_path: Path) -> str:
    """Get full instructions.xml as raw text."""
    return ship_instructions_path.read_text()


class TestStep7Exists:
    """Tests validating Step 7: Ship Report Generation exists."""

    def test_has_step_7(self, instructions_xml: ET.Element) -> None:
        """Step 7 for ship report generation exists."""
        execution = instructions_xml.find("execution")
        steps = execution.findall("step") if execution is not None else []
        step_7 = next((s for s in steps if s.get("n") == "7"), None)
        assert step_7 is not None

    def test_step_7_goal_is_report_generation(
        self, instructions_xml: ET.Element
    ) -> None:
        """Step 7 goal mentions ship report generation."""
        execution = instructions_xml.find("execution")
        steps = execution.findall("step") if execution is not None else []
        step_7 = next((s for s in steps if s.get("n") == "7"), None)
        assert step_7 is not None
        goal = step_7.get("goal", "").lower()
        assert "report" in goal

    def test_step_7_is_marked_critical(self, instructions_text: str) -> None:
        """Step 7 contains critical directives for report generation."""
        step_7_start = instructions_text.find('<step n="7"')
        step_7_end = instructions_text.find("</step>", step_7_start)
        step_7_text = instructions_text[step_7_start:step_7_end]
        assert "<critical>" in step_7_text


class TestStep7Substeps:
    """Tests validating substeps in Step 7."""

    @pytest.fixture
    def step_7(self, instructions_xml: ET.Element) -> ET.Element:
        """Get Step 7 element."""
        execution = instructions_xml.find("execution")
        steps = execution.findall("step") if execution is not None else []
        step = next((s for s in steps if s.get("n") == "7"), None)
        assert step is not None, "Step 7 not found"
        return step

    def test_has_compile_status_fields_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling status fields."""
        substeps = step_7.findall("substep")
        status_fields = next(
            (s for s in substeps if "status-fields" in s.get("name", "")), None
        )
        assert status_fields is not None

    def test_has_compile_preflight_summary_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling pre-flight summary."""
        substeps = step_7.findall("substep")
        preflight = next(
            (s for s in substeps if "preflight" in s.get("name", "")), None
        )
        assert preflight is not None

    def test_has_compile_execution_log_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling execution log."""
        substeps = step_7.findall("substep")
        execution_log = next(
            (s for s in substeps if "execution-log" in s.get("name", "")), None
        )
        assert execution_log is not None

    def test_has_compile_release_notes_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling release notes."""
        substeps = step_7.findall("substep")
        release_notes = next(
            (s for s in substeps if "release-notes" in s.get("name", "")), None
        )
        assert release_notes is not None

    def test_has_compile_failure_analysis_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling failure analysis."""
        substeps = step_7.findall("substep")
        failure = next(
            (s for s in substeps if "failure-analysis" in s.get("name", "")), None
        )
        assert failure is not None

    def test_has_compile_verification_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for compiling verification recommendations."""
        substeps = step_7.findall("substep")
        verification = next(
            (s for s in substeps if "verification" in s.get("name", "")), None
        )
        assert verification is not None

    def test_has_generate_ship_report_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for generating ship report."""
        substeps = step_7.findall("substep")
        generate = next(
            (s for s in substeps if "ship-report" in s.get("name", "")), None
        )
        assert generate is not None

    def test_has_report_confirmation_substep(self, step_7: ET.Element) -> None:
        """Step 7 has substep for report confirmation."""
        substeps = step_7.findall("substep")
        confirmation = next(
            (s for s in substeps if "confirmation" in s.get("name", "")), None
        )
        assert confirmation is not None


class TestStructuredStatusFields:
    """Tests validating structured status fields in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_deployment_status_field_documented(self, step_7_text: str) -> None:
        """DEPLOYMENT_STATUS field is documented."""
        assert "DEPLOYMENT_STATUS" in step_7_text

    def test_pr_merge_approved_field_documented(self, step_7_text: str) -> None:
        """PR_MERGE_APPROVED field is documented."""
        assert "PR_MERGE_APPROVED" in step_7_text

    def test_version_deployed_field_documented(self, step_7_text: str) -> None:
        """VERSION_DEPLOYED field is documented."""
        assert "VERSION_DEPLOYED" in step_7_text

    def test_pr_number_field_documented(self, step_7_text: str) -> None:
        """PR_NUMBER field is documented."""
        assert "PR_NUMBER" in step_7_text

    def test_status_fields_at_top_directive(self, step_7_text: str) -> None:
        """Directive to put status fields at top of report."""
        assert "top" in step_7_text.lower() and "status" in step_7_text.lower()

    def test_exact_format_directive(self, step_7_text: str) -> None:
        """Directive for exact format (FIELD: value)."""
        assert (
            "FIELD_NAME: value" in step_7_text or "field: value" in step_7_text.lower()
        )


class TestPreFlightSummarySection:
    """Tests validating pre-flight summary in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_risk_level_included(self, step_7_text: str) -> None:
        """Pre-flight summary includes risk level."""
        assert "risk_level" in step_7_text

    def test_risk_justification_included(self, step_7_text: str) -> None:
        """Pre-flight summary includes risk justification."""
        assert "risk_justification" in step_7_text

    def test_breaking_changes_included(self, step_7_text: str) -> None:
        """Pre-flight summary includes breaking changes."""
        assert "breaking_changes" in step_7_text

    def test_security_changes_included(self, step_7_text: str) -> None:
        """Pre-flight summary includes security changes."""
        assert "security" in step_7_text.lower()

    def test_pr_state_included(self, step_7_text: str) -> None:
        """Pre-flight summary includes PR state."""
        assert "mergeable" in step_7_text


class TestExecutionLogSection:
    """Tests validating execution log in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_version_bump_command_logged(self, step_7_text: str) -> None:
        """Execution log includes version bump command."""
        assert "version_bump_command" in step_7_text

    def test_build_command_logged(self, step_7_text: str) -> None:
        """Execution log includes build command."""
        assert "build_command" in step_7_text

    def test_publish_command_logged(self, step_7_text: str) -> None:
        """Execution log includes publish command."""
        assert "publish_command" in step_7_text

    def test_exit_codes_logged(self, step_7_text: str) -> None:
        """Execution log includes exit codes."""
        assert "exit_code" in step_7_text.lower()

    def test_no_commands_case_handled(self, step_7_text: str) -> None:
        """Execution log handles case when no commands configured."""
        assert "commands_skipped" in step_7_text

    def test_post_publish_hooks_logged(self, step_7_text: str) -> None:
        """Execution log includes post-publish hook results."""
        assert "hook_warnings" in step_7_text


class TestReleaseNotesSection:
    """Tests validating release notes in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_release_notes_content_included(self, step_7_text: str) -> None:
        """Release notes content is included when available."""
        assert "release_notes_content" in step_7_text

    def test_release_notes_skipped_fallback(self, step_7_text: str) -> None:
        """Fallback for when release notes are skipped."""
        assert "skipped" in step_7_text.lower()

    def test_artifact_reference_included(self, step_7_text: str) -> None:
        """Reference to release_notes.md artifact is included."""
        assert "release_notes.md" in step_7_text


class TestFailureAnalysisSection:
    """Tests validating failure analysis in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_conditional_on_failed_status(self, step_7_text: str) -> None:
        """Failure analysis is conditional on FAILED status."""
        assert "FAILED" in step_7_text

    def test_failed_command_included(self, step_7_text: str) -> None:
        """Failure analysis includes failed command."""
        assert "failed_command" in step_7_text

    def test_error_output_included(self, step_7_text: str) -> None:
        """Failure analysis includes error output."""
        assert "error_output" in step_7_text

    def test_diagnosis_included(self, step_7_text: str) -> None:
        """Failure analysis includes diagnosis."""
        assert "diagnosis" in step_7_text

    def test_remediation_included(self, step_7_text: str) -> None:
        """Failure analysis includes remediation steps."""
        assert "remediation" in step_7_text


class TestVerificationSection:
    """Tests validating verification recommendations in Step 7."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_success_verification_documented(self, step_7_text: str) -> None:
        """Verification for SUCCESS case is documented."""
        assert "SUCCESS" in step_7_text

    def test_blocked_verification_documented(self, step_7_text: str) -> None:
        """Verification for BLOCKED case is documented."""
        assert "BLOCKED" in step_7_text

    def test_failed_verification_documented(self, step_7_text: str) -> None:
        """Verification for FAILED case is documented."""
        assert "FAILED" in step_7_text

    def test_registry_verification_mentioned(self, step_7_text: str) -> None:
        """Registry verification is mentioned for publish success."""
        assert "registry" in step_7_text.lower()

    def test_tag_verification_mentioned(self, step_7_text: str) -> None:
        """Tag verification is mentioned for version bump."""
        assert "tag" in step_7_text.lower()


class TestArtifactConfiguration:
    """Tests validating artifact configuration for ship report."""

    @pytest.fixture
    def config_path(self) -> Path:
        """Path to ship phase config.yaml."""
        return Path(__file__).parents[3] / "src/adw/defaults/commands/ship/config.yaml"

    @pytest.fixture
    def config_text(self, config_path: Path) -> str:
        """Get config.yaml as raw text."""
        return config_path.read_text()

    def test_ship_report_artifact_defined(self, config_text: str) -> None:
        """ship_report artifact is defined in config."""
        assert "ship_report" in config_text

    def test_ship_report_pattern_defined(self, config_text: str) -> None:
        """ship_report pattern is ship_report.md."""
        assert "ship_report.md" in config_text

    def test_ship_report_is_required(self, config_text: str) -> None:
        """ship_report artifact is marked as required."""
        # Find ship_report section and check required: true
        ship_report_start = config_text.find("name: ship_report")
        release_notes_start = config_text.find("name: release_notes")
        ship_report_section = config_text[ship_report_start:release_notes_start]
        assert "required: true" in ship_report_section

    def test_release_notes_artifact_defined(self, config_text: str) -> None:
        """release_notes artifact is defined in config."""
        assert "release_notes" in config_text

    def test_release_notes_pattern_defined(self, config_text: str) -> None:
        """release_notes pattern is release_notes.md."""
        assert "release_notes.md" in config_text

    def test_release_notes_is_optional(self, config_text: str) -> None:
        """release_notes artifact is marked as optional."""
        release_notes_start = config_text.find("name: release_notes")
        release_notes_section = config_text[release_notes_start:]
        assert "required: false" in release_notes_section


class TestReportTemplate:
    """Tests validating the ship report template structure."""

    @pytest.fixture
    def step_7_text(self, ship_instructions_path: Path) -> str:
        """Get Step 7 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="7"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_report_has_title(self, step_7_text: str) -> None:
        """Ship report template includes title."""
        assert "# Ship Phase Report" in step_7_text

    def test_report_has_preflight_section(self, step_7_text: str) -> None:
        """Ship report template includes Pre-Flight Summary section."""
        assert "## Pre-Flight Summary" in step_7_text

    def test_report_has_execution_log_section(self, step_7_text: str) -> None:
        """Ship report template includes Execution Log section."""
        assert "## Execution Log" in step_7_text

    def test_report_has_release_notes_section(self, step_7_text: str) -> None:
        """Ship report template includes Release Notes section."""
        assert "## Release Notes" in step_7_text

    def test_report_has_verification_section(self, step_7_text: str) -> None:
        """Ship report template includes Verification Recommendations section."""
        assert "## Verification" in step_7_text

    def test_report_has_failure_analysis_conditional(self, step_7_text: str) -> None:
        """Ship report template includes conditional Failure Analysis section."""
        assert "## Failure Analysis" in step_7_text


class TestMetricsUpdated:
    """Tests validating that metrics section includes Step 7 items."""

    @pytest.fixture
    def metrics_text(self, ship_instructions_path: Path) -> str:
        """Get metrics section as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find("<metrics>")
        end = content.find("</metrics>")
        return content[start : end + 10] if end != -1 and start != -1 else ""

    def test_step_7_success_metric_exists(self, metrics_text: str) -> None:
        """Success metrics include Step 7 report generation."""
        assert "Step 7" in metrics_text

    def test_ship_report_artifact_metric_exists(self, metrics_text: str) -> None:
        """Success metrics include ship_report.md artifact."""
        assert "ship_report.md" in metrics_text

    def test_report_sections_metric_exists(self, metrics_text: str) -> None:
        """Success metrics mention report sections."""
        assert (
            "pre-flight" in metrics_text.lower() or "preflight" in metrics_text.lower()
        )

    def test_failure_metric_for_missing_report(self, metrics_text: str) -> None:
        """Failure metrics include missing report generation."""
        failure_start = metrics_text.find("<failure>")
        failure_section = metrics_text[failure_start:] if failure_start != -1 else ""
        assert "Step 7" in failure_section or "ship_report" in failure_section
