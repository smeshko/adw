"""Integration tests for Document phase PR description generation (Story 9.4).

Tests the document phase execution with PR description output, evidence
manifest integration, and artifact saving.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.extensions import DocumentExtension, ExtensionRegistry
from adw.core.phase_runner import PhaseRunner
from adw.executors.mock import MockExecutor
from adw.hooks.runner import HookRunner
from adw.models import (
    GitConfig,
    HookConfig,
    PhaseStatus,
    RunContext,
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a project structure with document phase configuration."""
    # Create document command directory with prompt and schema
    cmd_dir = tmp_path / ".adw" / "commands" / "document"
    cmd_dir.mkdir(parents=True)

    # Create prompt.md matching the real document prompt
    prompt_content = """# Document Phase - PR Description Generation

Generate a structured Pull Request description.

## Feature Description

{{feature_description}}

## Implementation Summary

{{artifacts.build.build_output}}

## Git Changes

**Available Build Artifacts:**
{{artifacts.build.*}}

## Evidence

**Available Validate Artifacts:**
{{artifacts.validate.*}}

## Instructions

Generate a GitHub-flavored Markdown PR description with the following structure:

1. **Summary** (1-2 sentences): Concise description of what this PR accomplishes
2. **Changes**: Bullet list of key changes made (derived from the build artifacts above)
3. **Testing**: How the changes were verified (from validate artifacts/evidence)
4. **Evidence**: Links to relevant evidence items if available (screenshots, API responses, etc.)

Use the artifact information above to construct the PR description:
- If diff_stats is available, include file counts and line changes
- If evidence_manifest is available, reference evidence items and screenshots
- If no evidence is available, note "No visual evidence captured"

## Output Format

Your response MUST be a valid PR description in the following format:

```markdown
## Summary

[1-2 sentence summary of the PR]

## Changes

- [Change 1]
- [Change 2]
- [Change 3]

## Testing

[Description of testing performed]

## Evidence

[Links to evidence or "No visual evidence captured" if none]
```

## Constraints

- Maximum length: ~4000 characters (GitHub PR description limit)
- Use relative paths for any file references
- If evidence includes screenshots, include them as markdown image links
- Focus on the "why" and impact, not just the "what"
"""
    (cmd_dir / "prompt.md").write_text(prompt_content)

    # Create schema.json
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PRDescription",
        "type": "object",
        "required": ["summary", "changes", "testing"],
        "properties": {
            "summary": {"type": "string", "minLength": 10},
            "changes": {"type": "array", "minItems": 1},
            "testing": {"type": "string", "minLength": 5},
            "evidence": {"type": "string"},
        },
    }
    (cmd_dir / "schema.json").write_text(json.dumps(schema, indent=2))

    return tmp_path


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create runs directory."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def run_id() -> str:
    """Create a sample run ID."""
    return "01HQXH9Z8G2K4M5N6P7R8S9T0V"


@pytest.fixture
def sample_context(run_id: str) -> RunContext:
    """Create a sample run context."""
    return RunContext(
        run_id=run_id,
        feature_description="Add user authentication with OAuth2",
        current_phase="document",
        phase_history=["plan", "build", "validate"],
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def setup_previous_artifacts(runs_dir: Path, run_id: str) -> None:
    """Set up artifacts from previous phases."""
    # Create build phase artifacts
    build_dir = runs_dir / run_id / "artifacts" / "build"
    build_dir.mkdir(parents=True)
    (build_dir / "build_output.md").write_text("Build completed successfully")
    (build_dir / "diff.txt").write_text("+added line\n-removed line")
    (build_dir / "diff_stats.json").write_text(
        json.dumps(
            {
                "files_changed": 3,
                "insertions": 50,
                "deletions": 10,
                "binary_files": 0,
                "summary": "3 files changed, 50 insertions(+), 10 deletions(-)",
            }
        )
    )

    # Create validate phase artifacts (includes evidence and validation output)
    validate_dir = runs_dir / run_id / "artifacts" / "validate"
    validate_dir.mkdir(parents=True, exist_ok=True)
    (validate_dir / "verify_output.md").write_text("All tests pass")

    # Create evidence manifest
    evidence_manifest = {
        "run_id": run_id,
        "platform": "backend",
        "total_items": 2,
        "passed": 2,
        "failed": 0,
        "errors": 0,
        "items": [
            {
                "name": "unit_tests",
                "type": "cli",
                "status": "pass",
                "path": "cli/unit_tests.txt",
            },
            {
                "name": "integration_tests",
                "type": "cli",
                "status": "pass",
                "path": "cli/integration_tests.txt",
            },
        ],
    }
    (validate_dir / "evidence_manifest.json").write_text(
        json.dumps(evidence_manifest, indent=2)
    )

    # Add validation output to validate directory
    validate_dir = runs_dir / run_id / "artifacts" / "validate"
    validate_dir.mkdir(parents=True, exist_ok=True)
    (validate_dir / "validate_output.md").write_text("Validation passed")


@pytest.fixture
def mock_executor() -> MockExecutor:
    """Create and configure a mock executor with PR description response."""
    executor = MockExecutor()
    executor.configure_responses(
        [
            {
                "content": """## Summary

Add OAuth2 user authentication with token-based access.

## Changes

- Add OAuth2 authentication endpoints
- Implement token refresh logic
- Add user session management

## Testing

All unit tests pass. Integration tests verify OAuth flow end-to-end.

## Evidence

See evidence items: unit_tests (pass), integration_tests (pass)
""",
                "tokens_used": 150,
            }
        ]
    )
    return executor


@pytest.fixture
def phase_runner(
    project_root: Path, runs_dir: Path, mock_executor: MockExecutor
) -> PhaseRunner:
    """Create a PhaseRunner with real components."""
    command_resolver = CommandResolver(project_root=project_root)
    template_engine = TemplateEngine(project_root=project_root)
    hook_runner = HookRunner(config=HookConfig(shell="/bin/bash", timeout_seconds=30))
    artifact_manager = ArtifactManager(runs_dir=runs_dir)

    # Create extension registry with DocumentExtension for pr_description.md
    git_config = GitConfig(auto_create_pr=False)  # Don't attempt PR creation in tests
    extension_registry = ExtensionRegistry()
    extension_registry.register(DocumentExtension(git_config, runs_dir))

    return PhaseRunner(
        command_resolver=command_resolver,
        template_engine=template_engine,
        hook_runner=hook_runner,
        executor=mock_executor,
        artifact_manager=artifact_manager,
        strict_artifacts=False,
        extension_registry=extension_registry,
    )


class TestDocumentPhasePROutput:
    """Tests for Document phase PR description generation."""

    def test_document_phase_saves_pr_description_artifact(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        setup_previous_artifacts: None,
        runs_dir: Path,
        run_id: str,
    ):
        """Test that document phase saves pr_description.md artifact."""
        result = phase_runner.run("document", sample_context)

        assert result.status == PhaseStatus.COMPLETED
        assert "pr_description.md" in result.artifacts

        # Verify the artifact file exists
        pr_path = runs_dir / run_id / "artifacts" / "document" / "pr_description.md"
        assert pr_path.exists()

        # Verify content has expected sections
        content = pr_path.read_text()
        assert "## Summary" in content
        assert "## Changes" in content
        assert "## Testing" in content

    def test_document_phase_saves_document_output_artifact(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        setup_previous_artifacts: None,
        runs_dir: Path,
        run_id: str,
    ):
        """Test that document phase saves standard document_output.md artifact."""
        result = phase_runner.run("document", sample_context)

        assert result.status == PhaseStatus.COMPLETED
        assert "document_output.md" in result.artifacts

        # Verify the artifact file exists
        output_path = (
            runs_dir / run_id / "artifacts" / "document" / "document_output.md"
        )
        assert output_path.exists()

    def test_document_phase_accesses_build_artifacts(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        setup_previous_artifacts: None,
    ):
        """Test that document phase can access build artifacts in template."""
        # The phase should complete without artifact reference errors
        result = phase_runner.run("document", sample_context)
        assert result.status == PhaseStatus.COMPLETED

    def test_document_phase_accesses_evidence_manifest(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        setup_previous_artifacts: None,
    ):
        """Test that document phase can access evidence manifest."""
        # The phase should complete without artifact reference errors
        result = phase_runner.run("document", sample_context)
        assert result.status == PhaseStatus.COMPLETED


class TestDocumentPhaseWithoutEvidence:
    """Tests for Document phase when evidence is not available."""

    @pytest.fixture
    def setup_artifacts_no_evidence(self, runs_dir: Path, run_id: str) -> None:
        """Set up artifacts without evidence manifest."""
        # Create build phase artifacts
        build_dir = runs_dir / run_id / "artifacts" / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "build_output.md").write_text("Build completed")

        # Create verify phase artifacts WITHOUT evidence manifest
        validate_dir = runs_dir / run_id / "artifacts" / "validate"
        validate_dir.mkdir(parents=True)
        (validate_dir / "verify_output.md").write_text("Tests pass")

    @pytest.fixture
    def mock_executor_no_evidence(self) -> MockExecutor:
        """Create mock executor for no-evidence test."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {
                    "content": """## Summary

Add feature without evidence.

## Changes

- Add new feature

## Testing

Tests pass

## Evidence

No visual evidence captured
""",
                    "tokens_used": 100,
                }
            ]
        )
        return executor

    @pytest.fixture
    def phase_runner_no_evidence(
        self,
        project_root: Path,
        runs_dir: Path,
        mock_executor_no_evidence: MockExecutor,
    ) -> PhaseRunner:
        """Create phase runner for no-evidence test."""
        command_resolver = CommandResolver(project_root=project_root)
        template_engine = TemplateEngine(project_root=project_root)
        hook_runner = HookRunner(
            config=HookConfig(shell="/bin/bash", timeout_seconds=30)
        )
        artifact_manager = ArtifactManager(runs_dir=runs_dir)

        return PhaseRunner(
            command_resolver=command_resolver,
            template_engine=template_engine,
            hook_runner=hook_runner,
            executor=mock_executor_no_evidence,
            artifact_manager=artifact_manager,
            strict_artifacts=False,
        )

    def test_document_phase_handles_missing_evidence(
        self,
        phase_runner_no_evidence: PhaseRunner,
        sample_context: RunContext,
        setup_artifacts_no_evidence: None,
    ):
        """Test that document phase handles missing evidence gracefully."""
        result = phase_runner_no_evidence.run("document", sample_context)

        # Should complete even without evidence manifest
        assert result.status == PhaseStatus.COMPLETED


class TestDocumentPhaseWithoutBuildArtifacts:
    """Tests for Document phase when build artifacts are not available."""

    @pytest.fixture
    def setup_artifacts_no_build(self, runs_dir: Path, run_id: str) -> None:
        """Set up artifacts without build phase artifacts."""
        # Create validate phase artifacts only (no build artifacts)
        validate_dir = runs_dir / run_id / "artifacts" / "validate"
        validate_dir.mkdir(parents=True, exist_ok=True)
        (validate_dir / "verify_output.md").write_text("Tests pass")
        (validate_dir / "validate_output.md").write_text("Validation passed")

        # Note: Intentionally NOT creating build artifacts

    @pytest.fixture
    def mock_executor_no_build(self) -> MockExecutor:
        """Create mock executor for no-build-artifacts test."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {
                    "content": """## Summary

Add feature without build artifacts context.

## Changes

- Add new feature

## Testing

Tests pass

## Evidence

No visual evidence captured
""",
                    "tokens_used": 100,
                }
            ]
        )
        return executor

    @pytest.fixture
    def phase_runner_no_build(
        self, project_root: Path, runs_dir: Path, mock_executor_no_build: MockExecutor
    ) -> PhaseRunner:
        """Create phase runner for no-build-artifacts test."""
        command_resolver = CommandResolver(project_root=project_root)
        template_engine = TemplateEngine(project_root=project_root)
        hook_runner = HookRunner(
            config=HookConfig(shell="/bin/bash", timeout_seconds=30)
        )
        artifact_manager = ArtifactManager(runs_dir=runs_dir)

        # Create extension registry with DocumentExtension for pr_description.md
        git_config = GitConfig(auto_create_pr=False)
        extension_registry = ExtensionRegistry()
        extension_registry.register(DocumentExtension(git_config, runs_dir))

        return PhaseRunner(
            command_resolver=command_resolver,
            template_engine=template_engine,
            hook_runner=hook_runner,
            executor=mock_executor_no_build,
            artifact_manager=artifact_manager,
            strict_artifacts=False,
            extension_registry=extension_registry,
        )

    def test_document_phase_handles_missing_build_artifacts(
        self,
        phase_runner_no_build: PhaseRunner,
        sample_context: RunContext,
        setup_artifacts_no_build: None,
    ):
        """Test that document phase handles missing build artifacts gracefully."""
        result = phase_runner_no_build.run("document", sample_context)

        # Should complete even without build artifacts
        assert result.status == PhaseStatus.COMPLETED
        assert "pr_description.md" in result.artifacts
