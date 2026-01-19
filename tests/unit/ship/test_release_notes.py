"""Tests for release notes generation in ship phase instructions.

This story (15.4) implements release notes generation via LLM instructions in
instructions.xml. These tests validate the instruction structure and content
since the actual execution is LLM-driven.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

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


class TestInstructionsXmlStructure:
    """Tests validating the structure of ship/instructions.xml."""

    def test_instructions_xml_is_valid_xml(self, ship_instructions_path: Path) -> None:
        """Ship instructions.xml parses as valid XML."""
        try:
            ET.parse(ship_instructions_path)
        except ET.ParseError as e:
            pytest.fail(f"instructions.xml is not valid XML: {e}")

    def test_has_workflow_root(self, instructions_xml: ET.Element) -> None:
        """Instructions has workflow as root element."""
        assert instructions_xml.tag == "workflow"

    def test_has_execution_section(self, instructions_xml: ET.Element) -> None:
        """Instructions has execution section."""
        execution = instructions_xml.find("execution")
        assert execution is not None

    def test_has_step_4_release_notes(self, instructions_xml: ET.Element) -> None:
        """Step 4 for release notes generation exists."""
        execution = instructions_xml.find("execution")
        steps = execution.findall("step") if execution is not None else []
        step_4 = next((s for s in steps if s.get("n") == "4"), None)
        assert step_4 is not None
        assert "release notes" in step_4.get("goal", "").lower()


class TestReleaseNotesStep:
    """Tests validating Step 4: Release Notes Generation."""

    @pytest.fixture
    def step_4(self, instructions_xml: ET.Element) -> ET.Element:
        """Get Step 4 element."""
        execution = instructions_xml.find("execution")
        steps = execution.findall("step") if execution is not None else []
        step = next((s for s in steps if s.get("n") == "4"), None)
        assert step is not None, "Step 4 not found"
        return step

    def test_has_version_header_substep(self, step_4: ET.Element) -> None:
        """Step 4 has substep for version header determination."""
        substeps = step_4.findall("substep")
        version_header = next(
            (s for s in substeps if "version-header" in s.get("name", "")), None
        )
        assert version_header is not None

    def test_has_categorize_commits_substep(self, step_4: ET.Element) -> None:
        """Step 4 has substep for commit categorization."""
        substeps = step_4.findall("substep")
        categorize = next(
            (s for s in substeps if "categorize" in s.get("name", "")), None
        )
        assert categorize is not None

    def test_has_clean_commit_messages_substep(self, step_4: ET.Element) -> None:
        """Step 4 has substep for commit message cleaning."""
        substeps = step_4.findall("substep")
        clean = next((s for s in substeps if "clean" in s.get("name", "")), None)
        assert clean is not None

    def test_has_changelog_format_substep(self, step_4: ET.Element) -> None:
        """Step 4 has substep for Keep a Changelog format."""
        substeps = step_4.findall("substep")
        changelog = next(
            (s for s in substeps if "changelog" in s.get("name", "")), None
        )
        assert changelog is not None

    def test_has_save_artifact_substep(self, step_4: ET.Element) -> None:
        """Step 4 has substep for saving release notes artifact."""
        substeps = step_4.findall("substep")
        artifact = next(
            (s for s in substeps if "artifact" in s.get("name", "")), None
        )
        assert artifact is not None


class TestCommitCategories:
    """Tests validating commit categorization in Step 4."""

    @pytest.fixture
    def step_4_text(self, ship_instructions_path: Path) -> str:
        """Get Step 4 content as raw text for pattern matching."""
        content = ship_instructions_path.read_text()
        # Find step 4 section
        start = content.find('<step n="4"')
        if start == -1:
            return ""
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 else content[start:]

    @pytest.mark.parametrize(
        "prefix",
        [
            "feat:",
            "feature:",
            "add:",
            "refactor:",
            "update:",
            "change:",
            "improve:",
            "fix:",
            "bugfix:",
            "patch:",
            "resolve:",
            "docs:",
            "doc:",
            "chore:",
            "ci:",
            "test:",
            "style:",
            "build:",
        ],
    )
    def test_commit_prefix_documented(self, step_4_text: str, prefix: str) -> None:
        """All conventional commit prefixes are documented in categorization rules."""
        # Check prefix appears in the categorization section
        assert prefix in step_4_text, f"Prefix '{prefix}' not found in Step 4"


class TestVersionHeaderLogic:
    """Tests validating version header logic in Step 4."""

    @pytest.fixture
    def step_4_text(self, ship_instructions_path: Path) -> str:
        """Get Step 4 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="4"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_version_bump_check_exists(self, step_4_text: str) -> None:
        """Version header substep checks for version_bump_executed."""
        assert "version_bump_executed" in step_4_text

    def test_new_version_variable_used(self, step_4_text: str) -> None:
        """Version header uses new_version variable when available."""
        assert "new_version" in step_4_text

    def test_unreleased_fallback_exists(self, step_4_text: str) -> None:
        """Version header falls back to 'Unreleased' when no version bump."""
        assert "Unreleased" in step_4_text

    def test_release_date_included(self, step_4_text: str) -> None:
        """Version header includes release_date variable."""
        assert "release_date" in step_4_text


class TestMessageCleaningRules:
    """Tests validating commit message cleaning rules in Step 4."""

    @pytest.fixture
    def step_4_text(self, ship_instructions_path: Path) -> str:
        """Get Step 4 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="4"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_remove_prefix_rule_documented(self, step_4_text: str) -> None:
        """Message cleaning includes rule to remove conventional commit prefix."""
        # Check for rule about removing prefix
        assert "Remove conventional commit prefix" in step_4_text or "Rule 1" in step_4_text

    def test_capitalize_rule_documented(self, step_4_text: str) -> None:
        """Message cleaning includes rule to capitalize first letter."""
        assert "Capitalize" in step_4_text or "capitalize" in step_4_text

    def test_first_line_rule_documented(self, step_4_text: str) -> None:
        """Message cleaning includes rule to use first line only."""
        assert "first line" in step_4_text


class TestChangelogFormat:
    """Tests validating Keep a Changelog format output in Step 4."""

    @pytest.fixture
    def step_4_text(self, ship_instructions_path: Path) -> str:
        """Get Step 4 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="4"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    @pytest.mark.parametrize(
        "section",
        ["### Added", "### Changed", "### Fixed", "### Documentation", "### Other"],
    )
    def test_changelog_section_exists(self, step_4_text: str, section: str) -> None:
        """Keep a Changelog sections are defined in format substep."""
        assert section in step_4_text

    def test_empty_section_omission_documented(self, step_4_text: str) -> None:
        """Instructions document that empty sections should be omitted."""
        assert "empty" in step_4_text.lower() or "NOT empty" in step_4_text


class TestArtifactOutput:
    """Tests validating artifact output in Step 4."""

    @pytest.fixture
    def step_4_text(self, ship_instructions_path: Path) -> str:
        """Get Step 4 content as raw text."""
        content = ship_instructions_path.read_text()
        start = content.find('<step n="4"')
        end = content.find("</step>", start)
        return content[start : end + 7] if end != -1 and start != -1 else ""

    def test_artifact_path_specified(self, step_4_text: str) -> None:
        """Release notes artifact path is specified."""
        assert "release_notes.md" in step_4_text

    def test_artifacts_dir_variable_used(self, step_4_text: str) -> None:
        """Artifact output uses artifacts_dir variable."""
        assert "artifacts_dir" in step_4_text
