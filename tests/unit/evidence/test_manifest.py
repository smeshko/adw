"""Tests for evidence manifest generation.

This module tests:
- ManifestGenerator: Creating manifests from strategy summaries
- PlanStepLinker: Linking evidence to plan steps
- EvidenceDirectoryScanner: Scanning evidence directories
- ManifestWriter: Writing manifests to JSON files
"""

import json
from pathlib import Path

import pytest

from adw.evidence.manifest import (
    EvidenceDirectoryScanner,
    ManifestGenerator,
    ManifestWriter,
    PlanStepLinker,
)
from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
    APIRequest,
    APIResponse,
    CLIEvidenceSummary,
    CommandResult,
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceType,
)

# =============================================================================
# ManifestGenerator Tests
# =============================================================================


class TestManifestGenerator:
    """Tests for ManifestGenerator class."""

    @pytest.fixture
    def generator(self, tmp_path: Path) -> ManifestGenerator:
        """Create a ManifestGenerator for testing."""
        return ManifestGenerator(
            run_id="01TEST123456789ABCDEFGHJK",
            platform="backend",
            evidence_directory=tmp_path / "evidence",
        )

    @pytest.fixture
    def cli_summary(self) -> CLIEvidenceSummary:
        """Create a CLI evidence summary for testing."""
        return CLIEvidenceSummary(
            total_commands=2,
            passed=1,
            failed=1,
            results=[
                CommandResult(
                    command="adw --version",
                    exit_code=0,
                    stdout="adw 1.0.0",
                    stderr="",
                    duration_seconds=0.1,
                    success=True,
                ),
                CommandResult(
                    command="adw status",
                    exit_code=1,
                    stdout="",
                    stderr="Error",
                    duration_seconds=0.2,
                    success=False,
                ),
            ],
        )

    @pytest.fixture
    def api_summary(self) -> APIEvidenceSummary:
        """Create an API evidence summary for testing."""
        return APIEvidenceSummary(
            base_url="http://localhost:8000",
            total_endpoints=2,
            successful=2,
            failed=0,
            status_mismatches=0,
            results=[
                APIEvidenceResult(
                    endpoint_name="health",
                    request=APIRequest(
                        method="GET", url="http://localhost:8000/health"
                    ),
                    response=APIResponse(
                        status_code=200,
                        body={"status": "ok"},
                        duration_seconds=0.01,
                    ),
                    success=True,
                    status_match=True,
                ),
                APIEvidenceResult(
                    endpoint_name="users",
                    request=APIRequest(method="GET", url="http://localhost:8000/users"),
                    response=APIResponse(
                        status_code=200,
                        body={"users": []},  # Must be dict or string, not list
                        duration_seconds=0.02,
                    ),
                    success=True,
                    status_match=True,
                ),
            ],
        )

    def test_generate_from_cli_summary(
        self, generator: ManifestGenerator, cli_summary: CLIEvidenceSummary
    ):
        """Test generating manifest from CLI summary."""
        manifest = generator.generate([cli_summary])

        assert manifest.run_id == "01TEST123456789ABCDEFGHJK"
        assert manifest.platform == "backend"
        assert manifest.total_items == 2
        assert manifest.passed == 1
        assert manifest.failed == 1
        assert manifest.errors == 0
        assert len(manifest.items) == 2

    def test_generate_from_api_summary(
        self, generator: ManifestGenerator, api_summary: APIEvidenceSummary
    ):
        """Test generating manifest from API summary."""
        manifest = generator.generate([api_summary])

        assert manifest.total_items == 2
        assert manifest.passed == 2
        assert manifest.failed == 0
        assert len(manifest.items) == 2

        # Check item types
        for item in manifest.items:
            assert item.type == EvidenceType.API

    def test_generate_from_multiple_summaries(
        self,
        generator: ManifestGenerator,
        cli_summary: CLIEvidenceSummary,
        api_summary: APIEvidenceSummary,
    ):
        """Test generating manifest from multiple summaries."""
        manifest = generator.generate([cli_summary, api_summary])

        assert manifest.total_items == 4
        assert manifest.passed == 3
        assert manifest.failed == 1

        # Check we have both CLI and API items
        types = {item.type for item in manifest.items}
        assert EvidenceType.CLI in types
        assert EvidenceType.API in types

    def test_generate_empty_summaries(self, generator: ManifestGenerator):
        """Test generating manifest with no summaries."""
        manifest = generator.generate([])

        assert manifest.total_items == 0
        assert manifest.passed == 0
        assert manifest.failed == 0
        assert len(manifest.items) == 0

    def test_evidence_item_details(
        self, generator: ManifestGenerator, api_summary: APIEvidenceSummary
    ):
        """Test that evidence items include proper details."""
        manifest = generator.generate([api_summary])
        health_item = next(i for i in manifest.items if i.name == "health")

        assert health_item.details is not None
        assert health_item.details["method"] == "GET"
        assert health_item.details["status_code"] == 200
        assert "duration_seconds" in health_item.details


# =============================================================================
# PlanStepLinker Tests
# =============================================================================


class TestPlanStepLinker:
    """Tests for PlanStepLinker class."""

    @pytest.fixture
    def plan_content(self) -> str:
        """Sample plan.md content."""
        return """# Implementation Plan

## Step 1: Health check endpoint
Create the /health endpoint that returns server status.

## Step 2: User authentication
Implement login and logout functionality.

## Step 3: User registration
Allow new users to sign up.
"""

    @pytest.fixture
    def plan_file(self, tmp_path: Path, plan_content: str) -> Path:
        """Create a plan.md file for testing."""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan_content)
        return plan_path

    @pytest.fixture
    def sample_manifest(self) -> EvidenceManifest:
        """Create a sample manifest for testing."""
        return EvidenceManifest(
            run_id="01TEST",
            platform="backend",
            evidence_directory=".adw/runs/test/evidence",
            total_items=3,
            passed=3,
            failed=0,
            errors=0,
            skipped=0,
            items=[
                EvidenceItem(
                    name="health_check",
                    type=EvidenceType.API,
                    path="api/health.json",
                    status=EvidenceStatus.PASS,
                ),
                EvidenceItem(
                    name="user_registration",
                    type=EvidenceType.API,
                    path="api/registration.json",
                    status=EvidenceStatus.PASS,
                ),
                EvidenceItem(
                    name="database_setup",
                    type=EvidenceType.CLI,
                    path="cli/database.txt",
                    status=EvidenceStatus.PASS,
                ),
            ],
        )

    def test_parse_plan_steps(self, plan_file: Path):
        """Test parsing plan.md to extract steps."""
        linker = PlanStepLinker(plan_path=plan_file)
        steps = linker.parse_plan_steps()

        assert len(steps) == 3
        assert ("step_1", "Health check endpoint") in steps
        assert ("step_2", "User authentication") in steps
        assert ("step_3", "User registration") in steps

    def test_explicit_links(self, plan_file: Path):
        """Test explicit linking takes precedence."""
        linker = PlanStepLinker(
            plan_path=plan_file,
            explicit_links={"health_check": "step_1"},
        )

        step = linker.link_evidence_to_step("health_check")
        assert step == "step_1"

    def test_heuristic_linking(self, plan_file: Path):
        """Test heuristic linking by keyword matching."""
        linker = PlanStepLinker(plan_path=plan_file)

        # "health_check" should match "Health check endpoint"
        step = linker.link_evidence_to_step("health_check")
        assert step == "step_1"

        # "user_registration" should match "User registration"
        step = linker.link_evidence_to_step("user_registration")
        assert step == "step_3"

    def test_link_steps_updates_manifest(
        self, plan_file: Path, sample_manifest: EvidenceManifest
    ):
        """Test that link_steps updates manifest items."""
        linker = PlanStepLinker(plan_path=plan_file)
        linked = linker.link_steps(sample_manifest)

        # Check items have plan_step set
        health_item = next(i for i in linked.items if i.name == "health_check")
        assert health_item.plan_step == "step_1"

    def test_coverage_calculation(
        self, plan_file: Path, sample_manifest: EvidenceManifest
    ):
        """Test that coverage is calculated correctly."""
        linker = PlanStepLinker(
            plan_path=plan_file,
            explicit_links={
                "health_check": "step_1",
                "user_registration": "step_3",
            },
        )
        linked = linker.link_steps(sample_manifest)

        assert linked.coverage is not None
        assert linked.coverage.total_plan_steps == 3
        assert linked.coverage.covered_steps == 2
        assert linked.coverage.uncovered_steps == 1
        assert abs(linked.coverage.coverage_percentage - 66.7) < 0.1

    def test_no_plan_file(self, tmp_path: Path, sample_manifest: EvidenceManifest):
        """Test behavior when no plan.md exists."""
        linker = PlanStepLinker(plan_path=tmp_path / "nonexistent.md")
        linked = linker.link_steps(sample_manifest)

        # Should return manifest unchanged (no coverage)
        assert linked.coverage is None
        assert linked.step_coverage is None


# =============================================================================
# EvidenceDirectoryScanner Tests
# =============================================================================


class TestEvidenceDirectoryScanner:
    """Tests for EvidenceDirectoryScanner class."""

    @pytest.fixture
    def evidence_dir(self, tmp_path: Path) -> Path:
        """Create an evidence directory structure for testing."""
        evidence_path = tmp_path / "evidence"

        # Create CLI evidence
        cli_dir = evidence_path / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "version.txt").write_text("adw 1.0.0")
        (cli_dir / "status.txt").write_text("Error: connection failed")
        (cli_dir / "summary.json").write_text("{}")  # Should be skipped

        # Create API evidence
        api_dir = evidence_path / "api"
        api_dir.mkdir()
        (api_dir / "health.json").write_text(
            json.dumps({"status_code": 200, "success": True})
        )
        (api_dir / "users.json").write_text(
            json.dumps({"status_code": 500, "success": False})
        )

        # Create screenshots
        screenshots_dir = evidence_path / "screenshots"
        screenshots_dir.mkdir()
        (screenshots_dir / "home.png").write_bytes(b"PNG fake content")

        return evidence_path

    def test_scan_finds_all_evidence(self, evidence_dir: Path):
        """Test scanning finds all evidence files."""
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        # Should find 5 items (2 CLI, 2 API, 1 screenshot)
        assert len(items) == 5

        # Check types
        types = {item.type for item in items}
        assert EvidenceType.CLI in types
        assert EvidenceType.API in types
        assert EvidenceType.SCREENSHOT in types

    def test_scan_categorizes_by_type(self, evidence_dir: Path):
        """Test items are categorized correctly by type."""
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        cli_items = [i for i in items if i.type == EvidenceType.CLI]
        api_items = [i for i in items if i.type == EvidenceType.API]
        screenshot_items = [i for i in items if i.type == EvidenceType.SCREENSHOT]

        assert len(cli_items) == 2
        assert len(api_items) == 2
        assert len(screenshot_items) == 1

    def test_scan_determines_status(self, evidence_dir: Path):
        """Test status is determined from file content."""
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        # CLI version should pass
        version_item = next(i for i in items if i.name == "version")
        assert version_item.status == EvidenceStatus.PASS

        # CLI status should fail (has "Error" in content)
        status_item = next(i for i in items if i.name == "status")
        assert status_item.status == EvidenceStatus.FAIL

        # API users should fail (success: false)
        users_item = next(i for i in items if i.name == "users")
        assert users_item.status == EvidenceStatus.FAIL

    def test_scan_generates_relative_paths(self, evidence_dir: Path):
        """Test paths are relative to evidence directory."""
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        for item in items:
            # Path should not be absolute
            assert not Path(item.path).is_absolute()
            # Path should start with subdirectory
            assert "/" in item.path

    def test_scan_skips_metadata_files(self, evidence_dir: Path):
        """Test metadata files like summary.json are skipped."""
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        names = {item.name for item in items}
        assert "summary" not in names

    def test_scan_empty_directory(self, tmp_path: Path):
        """Test scanning empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        scanner = EvidenceDirectoryScanner(empty_dir)
        items = scanner.scan()

        assert items == []

    def test_scan_nonexistent_directory(self, tmp_path: Path):
        """Test scanning nonexistent directory returns empty list."""
        scanner = EvidenceDirectoryScanner(tmp_path / "nonexistent")
        items = scanner.scan()

        assert items == []


# =============================================================================
# ManifestWriter Tests
# =============================================================================


class TestManifestWriter:
    """Tests for ManifestWriter class."""

    @pytest.fixture
    def sample_manifest(self) -> EvidenceManifest:
        """Create a sample manifest for testing."""
        return EvidenceManifest(
            run_id="01TEST123456789ABCDEFGHJK",
            platform="cli",
            evidence_directory=".adw/runs/test/evidence",
            total_items=1,
            passed=1,
            failed=0,
            errors=0,
            skipped=0,
            items=[
                EvidenceItem(
                    name="version",
                    type=EvidenceType.CLI,
                    path="cli/version.txt",
                    status=EvidenceStatus.PASS,
                    details={"command": "adw --version"},
                )
            ],
        )

    def test_write_creates_file(
        self, tmp_path: Path, sample_manifest: EvidenceManifest
    ):
        """Test writing manifest creates file."""
        writer = ManifestWriter(tmp_path)
        output_path = writer.write(sample_manifest)

        assert output_path.exists()
        assert output_path.name == "manifest.json"

    def test_write_custom_filename(
        self, tmp_path: Path, sample_manifest: EvidenceManifest
    ):
        """Test writing with custom filename."""
        writer = ManifestWriter(tmp_path)
        output_path = writer.write(sample_manifest, filename="custom.json")

        assert output_path.exists()
        assert output_path.name == "custom.json"

    def test_write_creates_directory(
        self, tmp_path: Path, sample_manifest: EvidenceManifest
    ):
        """Test writing creates evidence directory if needed."""
        evidence_dir = tmp_path / "nested" / "evidence"
        writer = ManifestWriter(evidence_dir)
        output_path = writer.write(sample_manifest)

        assert evidence_dir.exists()
        assert output_path.exists()

    def test_write_valid_json(self, tmp_path: Path, sample_manifest: EvidenceManifest):
        """Test written file is valid JSON."""
        writer = ManifestWriter(tmp_path)
        output_path = writer.write(sample_manifest)

        content = output_path.read_text()
        data = json.loads(content)

        assert data["run_id"] == "01TEST123456789ABCDEFGHJK"
        assert data["platform"] == "cli"
        assert data["total_items"] == 1

    def test_write_pretty_printed(
        self, tmp_path: Path, sample_manifest: EvidenceManifest
    ):
        """Test written JSON is pretty-printed."""
        writer = ManifestWriter(tmp_path)
        output_path = writer.write(sample_manifest)

        content = output_path.read_text()
        # Pretty-printed JSON has newlines
        assert "\n" in content

    def test_read_roundtrip(self, tmp_path: Path, sample_manifest: EvidenceManifest):
        """Test read/write roundtrip preserves data."""
        writer = ManifestWriter(tmp_path)
        writer.write(sample_manifest)

        read_manifest = writer.read()

        assert read_manifest is not None
        assert read_manifest.run_id == sample_manifest.run_id
        assert read_manifest.platform == sample_manifest.platform
        assert read_manifest.total_items == sample_manifest.total_items
        assert len(read_manifest.items) == len(sample_manifest.items)

    def test_read_nonexistent_file(self, tmp_path: Path):
        """Test reading nonexistent file returns None."""
        writer = ManifestWriter(tmp_path)
        result = writer.read()

        assert result is None

    def test_read_invalid_json(self, tmp_path: Path):
        """Test reading invalid JSON returns None."""
        (tmp_path / "manifest.json").write_text("not valid json")

        writer = ManifestWriter(tmp_path)
        result = writer.read()

        assert result is None

    def test_validate_missing_run_id(self, tmp_path: Path):
        """Test validation fails for missing run_id."""
        writer = ManifestWriter(tmp_path)

        manifest = EvidenceManifest(
            run_id="",  # Empty
            platform="cli",
            evidence_directory="test",
            total_items=0,
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
        )

        with pytest.raises(ValueError, match="run_id"):
            writer.write(manifest)


# =============================================================================
# Integration Tests
# =============================================================================


class TestManifestIntegration:
    """Integration tests for manifest generation workflow."""

    def test_full_workflow_with_summaries(self, tmp_path: Path):
        """Test complete workflow from summaries to manifest file."""
        evidence_dir = tmp_path / "evidence"

        # Create plan
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("""# Plan
## Step 1: Health check
Implement health endpoint.
""")

        # Create CLI summary
        cli_summary = CLIEvidenceSummary(
            total_commands=1,
            passed=1,
            failed=0,
            results=[
                CommandResult(
                    command="health_check",
                    exit_code=0,
                    stdout="ok",
                    stderr="",
                    duration_seconds=0.1,
                    success=True,
                )
            ],
        )

        # Generate manifest
        generator = ManifestGenerator(
            run_id="01TEST",
            platform="cli",
            evidence_directory=evidence_dir,
        )
        manifest = generator.generate([cli_summary])

        # Link steps
        linker = PlanStepLinker(plan_path=plan_path)
        linked_manifest = linker.link_steps(manifest)

        # Write manifest
        writer = ManifestWriter(evidence_dir)
        output_path = writer.write(linked_manifest)

        # Verify result
        assert output_path.exists()

        read_manifest = writer.read()
        assert read_manifest is not None
        assert read_manifest.total_items == 1
        assert read_manifest.coverage is not None
        assert read_manifest.coverage.coverage_percentage == 100.0

    def test_full_workflow_with_directory_scan(self, tmp_path: Path):
        """Test complete workflow using directory scanning."""
        evidence_dir = tmp_path / "evidence"

        # Create evidence files
        cli_dir = evidence_dir / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "version.txt").write_text("1.0.0")

        api_dir = evidence_dir / "api"
        api_dir.mkdir()
        (api_dir / "health.json").write_text(
            json.dumps({"status_code": 200, "success": True})
        )

        # Scan directory
        scanner = EvidenceDirectoryScanner(evidence_dir)
        items = scanner.scan()

        # Create manifest from scanned items
        passed = sum(1 for i in items if i.status == EvidenceStatus.PASS)
        failed = sum(1 for i in items if i.status == EvidenceStatus.FAIL)
        errors = sum(1 for i in items if i.status == EvidenceStatus.ERROR)
        skipped = sum(1 for i in items if i.status == EvidenceStatus.SKIPPED)

        manifest = EvidenceManifest(
            run_id="01TEST",
            platform="backend",
            evidence_directory=str(evidence_dir),
            total_items=len(items),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            items=items,
        )

        # Write manifest
        writer = ManifestWriter(evidence_dir)
        output_path = writer.write(manifest)

        assert output_path.exists()

        read_manifest = writer.read()
        assert read_manifest.total_items == 2
