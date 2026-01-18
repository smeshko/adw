"""Integration tests for single-phase worktree preservation (ISS-018).

These tests verify that when running a single phase, the worktree is preserved
for user inspection rather than being deleted, matching user intent for
stop-and-inspect workflows.
"""

import subprocess
from pathlib import Path

import pytest

from adw.worktree.manager import WorktreeManager


class TestSinglePhaseWorktreePreservation:
    """Integration tests for single-phase worktree preservation (ISS-018).

    These tests verify the behavior where single-phase runs preserve their
    worktree for user inspection, while multi-phase runs clean up.
    """

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository for testing."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        # Create initial commit
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        return tmp_path

    def test_worktree_preserved_after_single_phase_concept(
        self, git_repo: Path
    ) -> None:
        """Verify that the single-phase preservation concept is correct.

        This test creates a worktree and verifies that NOT calling cleanup
        leaves the worktree in place - the fundamental behavior that ISS-018
        implements by removing the cleanup call from single-phase success path.
        """
        # Setup
        run_id = "test-single-phase-run"
        trees_dir = git_repo / "trees"
        trees_dir.mkdir()

        manager = WorktreeManager(project_root=git_repo, base_dir="trees")

        # Create worktree (simulating what orchestrator does)
        # ISS-025: create_worktree now returns (path, branch_name) tuple
        worktree_path, _branch_name = manager.create_worktree(run_id)

        # Verify worktree exists
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # For single-phase: DO NOT call cleanup - worktree should remain
        # (This is what ISS-018 implements by removing _cleanup_worktree call)

        # Verify worktree still exists (preservation behavior)
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # Cleanup manually for test hygiene
        manager.remove_worktree(run_id, force=True, delete_branch=True)
        assert not worktree_path.exists()

    def test_manual_cleanup_command_works(self, git_repo: Path) -> None:
        """Verify that manual cleanup via WorktreeManager works.

        After single-phase preserves the worktree, users can clean up with
        'adw cleanup <run_id>'. This test verifies the underlying mechanism.
        """
        # Setup
        run_id = "test-cleanup-run"
        trees_dir = git_repo / "trees"
        trees_dir.mkdir()

        manager = WorktreeManager(project_root=git_repo, base_dir="trees")

        # Create worktree
        # ISS-025: create_worktree now returns (path, branch_name) tuple
        worktree_path, _branch_name = manager.create_worktree(run_id)
        assert worktree_path.exists()

        # Add some files (simulating work done in the phase)
        test_file = worktree_path / "plan.md"
        test_file.write_text("# Plan output from phase execution")

        # User decides to cleanup after inspection
        worktree_removed, branch_deleted = manager.remove_worktree(
            run_id, force=True, delete_branch=True
        )

        # Verify cleanup worked
        assert worktree_removed
        assert branch_deleted
        assert not worktree_path.exists()
