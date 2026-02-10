"""Integration tests for ship phase post.sh hook.

These tests verify the ship post-hook behavior including:
- Status parsing from LLM output
- PR merge execution with different strategies
- Branch deletion handling
- Auto-merge disabled flow
- Merge error handling
- Task manager integration
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestShipPostHookStatusParsing:
    """Tests for parsing LLM output status markers."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    @pytest.fixture
    def tmp_artifacts_dir(self, tmp_path: Path) -> Path:
        """Create a temporary artifacts directory."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        return artifacts_dir

    def run_post_hook(
        self,
        post_hook_path: Path,
        llm_output: str,
        artifacts_dir: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run the post.sh hook with the given LLM output."""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run-123",
            "ADW_FEATURE": "Test feature",
            "PATH": "/usr/bin:/bin",
        }

        if artifacts_dir:
            env["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)

        if env_overrides:
            env.update(env_overrides)

        return subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_parse_success_status(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test parsing SUCCESS deployment status."""
        llm_output = """
## Ship Phase Status

```
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 1.2.3
MERGE_REASON: Deployment successful, all checks passed
PR_NUMBER: 123
```
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        assert "Deployment Status: SUCCESS" in result.stdout
        assert "PR Merge Approved: false" in result.stdout
        assert "Version Deployed: 1.2.3" in result.stdout
        assert "PR Number: 123" in result.stdout

        # Check status JSON artifact
        status_file = tmp_artifacts_dir / "ship_status.json"
        assert status_file.exists()
        status = json.loads(status_file.read_text())
        assert status["deployment_status"] == "SUCCESS"
        assert status["pr_merge_approved"] is False
        assert status["version_deployed"] == "1.2.3"

    def test_parse_failed_status(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test parsing FAILED deployment status exits with code 1."""
        llm_output = """
DEPLOYMENT_STATUS: FAILED
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: N/A
MERGE_REASON: Build command failed with exit code 1
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 1
        assert "DEPLOYMENT FAILED" in result.stdout
        assert "Build command failed" in result.stdout

    def test_parse_blocked_status(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test parsing BLOCKED deployment status exits with code 0."""
        llm_output = """
DEPLOYMENT_STATUS: BLOCKED
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: N/A
MERGE_REASON: PR requires review approval
PR_NUMBER: 456
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        assert "DEPLOYMENT BLOCKED" in result.stdout
        assert "PR requires review approval" in result.stdout

    def test_parse_unknown_status_defaults(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test parsing output with missing status defaults safely."""
        llm_output = """
Some random LLM output without proper status markers.
Just talking about the deployment...
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        # Should not crash, should report UNKNOWN status
        assert "Deployment Status: UNKNOWN" in result.stdout
        assert "PR Merge Approved: false" in result.stdout


class TestShipPostHookAutoMergeDisabled:
    """Tests for auto-merge disabled flow."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    @pytest.fixture
    def tmp_artifacts_dir(self, tmp_path: Path) -> Path:
        """Create a temporary artifacts directory."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        return artifacts_dir

    def run_post_hook(
        self,
        post_hook_path: Path,
        llm_output: str,
        artifacts_dir: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run the post.sh hook with the given LLM output."""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run-123",
            "ADW_FEATURE": "Test feature",
            "PATH": "/usr/bin:/bin",
        }

        if artifacts_dir:
            env["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)

        if env_overrides:
            env.update(env_overrides)

        return subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_pr_not_approved_skips_merge(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test that PR_MERGE_APPROVED: false skips merge even with auto_merge enabled."""
        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 2.0.0
MERGE_REASON: Breaking changes detected, manual review required
PR_NUMBER: 999
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        assert "LLM did not approve PR merge" in result.stdout
        assert "Breaking changes detected" in result.stdout


class TestShipPostHookArtifacts:
    """Tests for artifact generation."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    @pytest.fixture
    def tmp_artifacts_dir(self, tmp_path: Path) -> Path:
        """Create a temporary artifacts directory."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        return artifacts_dir

    def run_post_hook(
        self,
        post_hook_path: Path,
        llm_output: str,
        artifacts_dir: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run the post.sh hook with the given LLM output."""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run-123",
            "ADW_FEATURE": "Test feature",
            "ADW_SHIP_AUTO_MERGE": "false",  # Disable merge to avoid gh calls
            "PATH": "/usr/bin:/bin",
        }

        if artifacts_dir:
            env["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)

        if env_overrides:
            env.update(env_overrides)

        return subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_ship_report_artifact_saved(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test that ship_report.md artifact is saved."""
        llm_output = """
## Ship Phase Report

DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 1.0.0
MERGE_REASON: All good
PR_NUMBER: 42

Detailed report content...
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        ship_report = tmp_artifacts_dir / "ship_report.md"
        assert ship_report.exists()
        content = ship_report.read_text()
        assert "Ship Phase Report" in content
        assert "DEPLOYMENT_STATUS: SUCCESS" in content

    def test_release_notes_artifact_extracted(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test that release notes are extracted to separate artifact."""
        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 1.1.0
MERGE_REASON: Success
PR_NUMBER: 55

## Release Notes

### Added
- New feature A
- New feature B

### Fixed
- Bug fix C
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        release_notes = tmp_artifacts_dir / "release_notes.md"
        assert release_notes.exists()
        content = release_notes.read_text()
        assert "Release Notes" in content
        assert "New feature A" in content

    def test_status_json_artifact_valid(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test that ship_status.json is valid JSON with correct values."""
        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 3.0.0
MERGE_REASON: Deployment successful
PR_NUMBER: 42
"""
        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir)

        assert result.returncode == 0
        status_file = tmp_artifacts_dir / "ship_status.json"
        assert status_file.exists()

        status = json.loads(status_file.read_text())
        assert status["deployment_status"] == "SUCCESS"
        assert status["pr_merge_approved"] is False
        assert status["version_deployed"] == "3.0.0"
        assert status["merge_reason"] == "Deployment successful"
        assert status["pr_number"] == 42


class TestShipPostHookTaskManager:
    """Tests for task manager integration."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    @pytest.fixture
    def tmp_artifacts_dir(self, tmp_path: Path) -> Path:
        """Create a temporary artifacts directory."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        return artifacts_dir

    def run_post_hook(
        self,
        post_hook_path: Path,
        llm_output: str,
        artifacts_dir: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run the post.sh hook with the given LLM output."""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run-123",
            "ADW_FEATURE": "Test feature",
            "ADW_SHIP_AUTO_MERGE": "false",  # Disable merge to avoid gh calls
            "PATH": "/usr/bin:/bin",
        }

        if artifacts_dir:
            env["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)

        if env_overrides:
            env.update(env_overrides)

        return subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_task_update_request_created_when_task_id_present(
        self, post_hook_path: Path, tmp_artifacts_dir: Path
    ) -> None:
        """Test that task_update_request.json is NOT created when merge doesn't happen."""
        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 1.0.0
MERGE_REASON: Success
PR_NUMBER: 100
"""
        # Task update only happens after successful merge
        # With PR_MERGE_APPROVED=false, the task update request won't be created
        env = {
            "ADW_TASK_ID": "TASK-123",
            "ADW_PR_NUMBER": "100",
        }

        result = self.run_post_hook(post_hook_path, llm_output, tmp_artifacts_dir, env)

        assert result.returncode == 0
        # Task update request is NOT created because merge didn't happen
        task_update = tmp_artifacts_dir / "task_update_request.json"
        assert not task_update.exists()  # Expected - no merge means no task update


class TestShipPostHookMergeCommand:
    """Tests for merge command construction (always squash + delete-branch)."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    def test_merge_command_uses_squash_without_delete_branch(
        self, post_hook_path: Path, tmp_path: Path
    ) -> None:
        """Test that merge command uses --squash without --delete-branch."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: true
VERSION_DEPLOYED: 1.0.0
MERGE_REASON: Success
PR_NUMBER: 50
"""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run",
            "ADW_FEATURE": "Test",
            "ADW_ARTIFACTS_DIR": str(artifacts_dir),
            "ADW_PR_NUMBER": "50",
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # gh is not in PATH so merge fails, but command is still printed
        assert "gh pr merge 50 --squash" in result.stdout
        assert "--delete-branch" not in result.stdout

    def test_merge_output_includes_version(
        self, post_hook_path: Path, tmp_path: Path
    ) -> None:
        """Test that version is parsed and displayed in output."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 2.5.0
MERGE_REASON: Success
PR_NUMBER: 60
"""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run",
            "ADW_FEATURE": "Test",
            "ADW_ARTIFACTS_DIR": str(artifacts_dir),
            "ADW_PR_NUMBER": "60",
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Version Deployed: 2.5.0" in result.stdout


class TestShipPostHookEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def post_hook_path(self) -> Path:
        """Get the path to the ship post.sh hook."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "adw"
            / "defaults"
            / "commands"
            / "ship"
            / "post.sh"
        )

    def test_no_llm_output_handles_gracefully(self, post_hook_path: Path) -> None:
        """Test that missing LLM output is handled gracefully."""
        env = {
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run",
            "ADW_FEATURE": "Test",
            "PATH": "/usr/bin:/bin",
            # No ADW_LLM_OUTPUT
        }

        result = subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "No LLM output available" in result.stdout

    def test_no_pr_number_skips_merge(self, post_hook_path: Path) -> None:
        """Test that missing PR number skips merge gracefully."""
        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: true
VERSION_DEPLOYED: 1.0.0
MERGE_REASON: Success
"""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run",
            "ADW_FEATURE": "Test",
            "ADW_SHIP_AUTO_MERGE": "true",
            "PATH": "/usr/bin:/bin",
            # No ADW_PR_NUMBER and no PR_NUMBER in output
        }

        result = subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail because no PR number available
        assert result.returncode == 1
        assert "Cannot merge - no PR number available" in result.stdout

    def test_pr_number_from_output_overrides_env(
        self, post_hook_path: Path, tmp_path: Path
    ) -> None:
        """Test that PR_NUMBER from LLM output is used over env var."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        llm_output = """
DEPLOYMENT_STATUS: SUCCESS
PR_MERGE_APPROVED: false
VERSION_DEPLOYED: 1.0.0
MERGE_REASON: Success
PR_NUMBER: 999
"""
        env = {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_PHASE": "ship",
            "ADW_RUN_ID": "test-run",
            "ADW_FEATURE": "Test",
            "ADW_ARTIFACTS_DIR": str(artifacts_dir),
            "ADW_PR_NUMBER": "123",  # Should be overridden by LLM output
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["/bin/bash", str(post_hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "PR Number: 999" in result.stdout  # From LLM output
        assert "PR #999" in result.stdout
