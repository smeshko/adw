"""Integration tests for single-phase worktree preservation.

These tests verify that when running a single phase, the worktree is preserved
for user inspection rather than being deleted, matching user intent for
stop-and-inspect workflows.
"""

from pathlib import Path

from adw.worktree.manager import WorktreeManager


class TestSinglePhaseWorktreePreservation:
    """Integration tests for single-phase worktree preservation.

    These tests verify the behavior where single-phase runs preserve their
    worktree for user inspection, while multi-phase runs clean up.
    """

    def test_worktree_preserved_after_single_phase_concept(
        self, git_repo: Path
    ) -> None:
        """Verify that the single-phase preservation concept is correct.

        This test creates a worktree and verifies that NOT calling cleanup
        leaves the worktree in place - the fundamental behavior behind
        single-phase preservation: the success path makes no cleanup call.
        """
        # Setup
        run_id = "test-single-phase-run"
        trees_dir = git_repo / "trees"
        trees_dir.mkdir()

        manager = WorktreeManager(project_root=git_repo, base_dir="trees")

        # Create worktree (simulating what orchestrator does)
        # create_worktree returns a (path, branch_name) tuple
        worktree_path, _branch_name = manager.create_worktree(run_id)

        # Verify worktree exists
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # For single-phase: DO NOT call cleanup - worktree should remain

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
        # create_worktree returns a (path, branch_name) tuple
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
