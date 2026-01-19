"""Tests for bundled default commands (Task 6).

Verifies that bundled commands are accessible and resolvable.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from adw.commands import CommandResolver


class TestBundledCommands:
    """Test bundled default commands."""

    @pytest.fixture
    def isolated_resolver(self, tmp_path: Path) -> CommandResolver:
        """Create a resolver with no project/user commands."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
        return resolver

    def test_bundled_plan_exists(self) -> None:
        """Bundled plan command should exist."""
        # Test by checking the file exists directly
        from importlib.resources import files

        plan_path = files("adw") / "defaults" / "commands" / "plan"
        # Check it exists (will raise if not)
        assert (Path(str(plan_path)) / "prompt.md").exists()

    def test_bundled_build_exists(self) -> None:
        """Bundled build command should exist."""
        from importlib.resources import files

        build_path = files("adw") / "defaults" / "commands" / "build"
        assert (Path(str(build_path)) / "prompt.md").exists()

    # ISS-019: test_bundled_verify_exists removed - verify phase no longer exists

    def test_bundled_validate_exists(self) -> None:
        """Bundled validate command should exist."""
        from importlib.resources import files

        validate_path = files("adw") / "defaults" / "commands" / "validate"
        assert (Path(str(validate_path)) / "prompt.md").exists()

    def test_bundled_document_exists(self) -> None:
        """Bundled document command should exist."""
        from importlib.resources import files

        document_path = files("adw") / "defaults" / "commands" / "document"
        assert (Path(str(document_path)) / "prompt.md").exists()

    def test_resolve_bundled_plan(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled plan command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("plan")

        assert result.name == "plan"
        assert result.tier == "bundled"

    def test_resolve_bundled_build(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled build command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("build")

        assert result.name == "build"
        assert result.tier == "bundled"

    def test_bundled_ship_exists(self) -> None:
        """Bundled ship command should exist."""
        from importlib.resources import files

        ship_path = files("adw") / "defaults" / "commands" / "ship"
        assert (Path(str(ship_path)) / "prompt.md").exists()

    def test_bundled_ship_has_instructions_xml(self) -> None:
        """Bundled ship command should have instructions.xml for LLM workflow."""
        from importlib.resources import files

        ship_path = files("adw") / "defaults" / "commands" / "ship"
        instructions_path = Path(str(ship_path)) / "instructions.xml"
        assert instructions_path.exists()

    def test_resolve_bundled_ship(self, tmp_path: Path) -> None:
        """Should be able to resolve bundled ship command."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("ship")

        assert result.name == "ship"
        assert result.tier == "bundled"


class TestShipPhaseInstructionsXml:
    """Tests for Story 15.2: Ship phase instructions.xml structure and content."""

    @pytest.fixture
    def instructions_xml_path(self) -> Path:
        """Get the path to ship/instructions.xml."""
        from importlib.resources import files

        ship_path = files("adw") / "defaults" / "commands" / "ship"
        return Path(str(ship_path)) / "instructions.xml"

    @pytest.fixture
    def instructions_content(self, instructions_xml_path: Path) -> str:
        """Load the instructions.xml content."""
        return instructions_xml_path.read_text()

    def test_instructions_xml_is_valid_xml(self, instructions_xml_path: Path) -> None:
        """Instructions.xml should be valid XML."""
        import xml.etree.ElementTree as ET

        # This will raise if XML is invalid
        ET.parse(instructions_xml_path)

    def test_instructions_has_workflow_root(self, instructions_xml_path: Path) -> None:
        """Instructions.xml should have <workflow> as root element."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(instructions_xml_path)
        root = tree.getroot()
        assert root.tag == "workflow"

    def test_instructions_has_step_1_context_gathering(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should have step 1 for context gathering."""
        import xml.etree.ElementTree as ET
        from io import StringIO

        tree = ET.parse(StringIO(instructions_content))
        root = tree.getroot()

        # Find step with n="1"
        execution = root.find(".//execution")
        assert execution is not None, "Should have <execution> element"

        step_1 = None
        for step in execution.findall(".//step"):
            if step.get("n") == "1":
                step_1 = step
                break

        assert step_1 is not None, "Should have step n='1'"
        assert (
            "context" in step_1.get("goal", "").lower()
            or "gather" in step_1.get("goal", "").lower()
        ), "Step 1 should be about context gathering"

    def test_instructions_has_step_2_preflight_analysis(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should have step 2 for pre-flight analysis."""
        import xml.etree.ElementTree as ET
        from io import StringIO

        tree = ET.parse(StringIO(instructions_content))
        root = tree.getroot()

        execution = root.find(".//execution")
        assert execution is not None

        step_2 = None
        for step in execution.findall(".//step"):
            if step.get("n") == "2":
                step_2 = step
                break

        assert step_2 is not None, "Should have step n='2'"
        assert (
            "analysis" in step_2.get("goal", "").lower()
            or "pre-flight" in step_2.get("goal", "").lower()
        ), "Step 2 should be about pre-flight analysis"

    def test_instructions_references_gh_pr_view(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should reference gh pr view command for PR info."""
        assert "gh pr view" in instructions_content
        assert "mergeable" in instructions_content.lower()
        assert (
            "mergeStateStatus" in instructions_content
            or "merge_state_status" in instructions_content
        )

    def test_instructions_has_version_detection(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should have version file detection logic."""
        assert "package.json" in instructions_content
        assert "pyproject.toml" in instructions_content
        assert "Cargo.toml" in instructions_content
        assert "VERSION" in instructions_content

    def test_instructions_has_risk_levels(self, instructions_content: str) -> None:
        """Instructions.xml should define risk levels LOW, MEDIUM, HIGH."""
        assert "LOW" in instructions_content
        assert "MEDIUM" in instructions_content
        assert "HIGH" in instructions_content
        assert (
            "risk_level" in instructions_content
            or "risk level" in instructions_content.lower()
        )

    def test_instructions_has_blocking_conditions(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should define blocking conditions."""
        assert "BLOCKED" in instructions_content
        assert "blocking" in instructions_content.lower()
        assert "PR_MERGE_APPROVED" in instructions_content

    def test_instructions_references_git_describe(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should reference git describe for version tags."""
        assert "git describe" in instructions_content
        assert "tags" in instructions_content.lower()

    def test_instructions_has_breaking_change_detection(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should detect breaking changes."""
        assert "breaking" in instructions_content.lower()
        assert "BREAKING" in instructions_content

    def test_instructions_has_security_analysis(
        self, instructions_content: str
    ) -> None:
        """Instructions.xml should analyze security-sensitive changes."""
        assert "security" in instructions_content.lower()
        assert (
            "auth" in instructions_content.lower()
            or "authentication" in instructions_content.lower()
        )
