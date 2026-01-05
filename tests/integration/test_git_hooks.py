"""Integration tests for git hook functionality.

Tests for git branch management and commit operations with real git
repositories, verifying end-to-end behavior of branch creation,
switching, uncommitted changes detection, staging, and commits.
"""

import subprocess
from pathlib import Path

import pytest

from adw.exceptions import HookError
from adw.hooks.git_branch import (
    check_uncommitted_changes,
    create_or_switch_branch,
    sanitize_branch_name,
)
from adw.hooks.git_commit import (
    create_commit,
    has_staged_changes,
    stage_changes,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create an isolated git repository for testing.

    Creates a minimal git repository with an initial commit
    so that branch operations can be performed.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the initialized git repository.
    """
    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Create initial file and commit
    (tmp_path / "README.md").write_text("# Test Project\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    return tmp_path


class TestGitBranchIntegration:
    """Integration tests for git branch operations."""

    def test_create_new_branch(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should create a new branch when it doesn't exist."""
        monkeypatch.chdir(git_repo)

        create_or_switch_branch("feature/test-branch")

        # Verify we're on the new branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/test-branch"

    def test_switch_to_existing_branch(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should switch to an existing branch."""
        monkeypatch.chdir(git_repo)

        # Create branch first
        subprocess.run(
            ["git", "checkout", "-b", "feature/existing"],
            capture_output=True,
            check=True,
        )
        # Switch back to main/master
        subprocess.run(
            ["git", "checkout", "-"],
            capture_output=True,
            check=True,
        )

        # Now use our function to switch to existing branch
        create_or_switch_branch("feature/existing")

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/existing"

    def test_idempotent_creation(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should be safe to call multiple times (idempotent)."""
        monkeypatch.chdir(git_repo)

        # Call twice - should not raise
        create_or_switch_branch("feature/idempotent")
        create_or_switch_branch("feature/idempotent")

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/idempotent"

    def test_sanitized_branch_names(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should work with sanitized branch names."""
        monkeypatch.chdir(git_repo)

        # Sanitize and create
        branch_name = "feature/" + sanitize_branch_name("Add User Authentication")
        create_or_switch_branch(branch_name)

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/add-user-authentication"


class TestUncommittedChangesIntegration:
    """Integration tests for uncommitted changes detection."""

    def test_clean_repo_returns_false(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return False for a clean working tree."""
        monkeypatch.chdir(git_repo)

        assert check_uncommitted_changes() is False

    def test_modified_file_returns_true(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return True when a file is modified."""
        monkeypatch.chdir(git_repo)

        # Modify a file
        (git_repo / "README.md").write_text("# Modified\n")

        assert check_uncommitted_changes() is True

    def test_new_untracked_file_returns_true(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return True for untracked files."""
        monkeypatch.chdir(git_repo)

        # Create new file
        (git_repo / "new_file.txt").write_text("new content")

        assert check_uncommitted_changes() is True

    def test_staged_changes_returns_true(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return True for staged changes."""
        monkeypatch.chdir(git_repo)

        # Create and stage new file
        (git_repo / "staged.txt").write_text("staged content")
        subprocess.run(
            ["git", "add", "staged.txt"],
            capture_output=True,
            check=True,
        )

        assert check_uncommitted_changes() is True

    def test_committed_changes_returns_false(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return False after committing changes."""
        monkeypatch.chdir(git_repo)

        # Create, stage, and commit
        (git_repo / "committed.txt").write_text("committed content")
        subprocess.run(
            ["git", "add", "committed.txt"],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add committed file"],
            capture_output=True,
            check=True,
        )

        assert check_uncommitted_changes() is False


class TestGitHookErrorHandling:
    """Integration tests for error handling in git operations."""

    def test_error_in_non_git_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise HookError when not in a git repository."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(HookError) as exc_info:
            create_or_switch_branch("feature/test")

        assert exc_info.value.code == "GIT_BRANCH_FAILED"
        assert (
            "not a git repository" in exc_info.value.stderr.lower()
            or "not a git repository" in exc_info.value.message.lower()
        )

    def test_check_uncommitted_changes_in_non_git_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise HookError when checking changes outside a git repo."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(HookError) as exc_info:
            check_uncommitted_changes()

        assert exc_info.value.code == "GIT_STATUS_FAILED"
        assert (
            "not a git repository" in exc_info.value.stderr.lower()
            or "not a git repository" in exc_info.value.message.lower()
        )


class TestStageChangesIntegration:
    """Integration tests for stage_changes function."""

    def test_stage_modified_file(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should stage modified files."""
        monkeypatch.chdir(git_repo)

        # Modify a file
        (git_repo / "README.md").write_text("# Modified\n")

        files = stage_changes()

        assert "README.md" in files
        assert has_staged_changes() is True

    def test_stage_new_file(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should stage new files."""
        monkeypatch.chdir(git_repo)

        # Create new file
        (git_repo / "new_file.py").write_text("# New file\n")

        files = stage_changes()

        assert "new_file.py" in files
        assert has_staged_changes() is True

    def test_stage_multiple_files(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should stage multiple files at once."""
        monkeypatch.chdir(git_repo)

        # Create multiple files
        (git_repo / "file1.py").write_text("# File 1\n")
        (git_repo / "file2.py").write_text("# File 2\n")
        (git_repo / "file3.py").write_text("# File 3\n")

        files = stage_changes()

        assert len(files) == 3
        assert "file1.py" in files
        assert "file2.py" in files
        assert "file3.py" in files

    def test_stage_no_changes(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return empty list when no changes."""
        monkeypatch.chdir(git_repo)

        files = stage_changes()

        assert files == []
        assert has_staged_changes() is False


class TestHasStagedChangesIntegration:
    """Integration tests for has_staged_changes function."""

    def test_no_staged_changes(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return False for clean repo."""
        monkeypatch.chdir(git_repo)

        assert has_staged_changes() is False

    def test_has_staged_changes_after_add(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return True after staging a file."""
        monkeypatch.chdir(git_repo)

        # Create and stage a file
        (git_repo / "staged.py").write_text("# Staged\n")
        subprocess.run(["git", "add", "staged.py"], check=True)

        assert has_staged_changes() is True

    def test_unstaged_changes_not_detected(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return False for unstaged changes."""
        monkeypatch.chdir(git_repo)

        # Modify a file but don't stage it
        (git_repo / "README.md").write_text("# Modified\n")

        assert has_staged_changes() is False


class TestCreateCommitIntegration:
    """Integration tests for create_commit function."""

    def test_create_commit_with_changes(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should create commit and return SHA."""
        monkeypatch.chdir(git_repo)

        # Create and stage a file
        (git_repo / "feature.py").write_text("# Feature\n")
        stage_changes()

        sha = create_commit(
            phase="build",
            feature="Add feature",
            run_id="01HQ123456",
        )

        assert sha is not None
        assert len(sha) == 40  # Full SHA length

        # Verify commit was created
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[adw] Build: Add feature" in result.stdout

    def test_create_commit_no_changes(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return None when no changes to commit."""
        monkeypatch.chdir(git_repo)

        sha = create_commit(
            phase="build",
            feature="No changes",
            run_id="01HQ123456",
        )

        assert sha is None

    def test_create_commit_with_custom_template(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use custom template for commit message."""
        monkeypatch.chdir(git_repo)

        # Create and stage a file
        (git_repo / "custom.py").write_text("# Custom\n")
        stage_changes()

        sha = create_commit(
            phase="verify",
            feature="Custom template",
            run_id="01HQ789",
            template="{phase}: {feature}",
        )

        assert sha is not None

        # Verify commit message uses custom template
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "verify: Custom template"

    def test_create_commit_includes_run_id(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should include run_id in commit body."""
        monkeypatch.chdir(git_repo)

        # Create and stage a file
        (git_repo / "runid.py").write_text("# Run ID test\n")
        stage_changes()

        sha = create_commit(
            phase="build",
            feature="Run ID test",
            run_id="01HQ999888",
        )

        assert sha is not None

        # Verify commit body includes run_id
        result = subprocess.run(
            ["git", "log", "-1", "--format=%b"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Run: 01HQ999888" in result.stdout

    def test_create_commit_unicode_feature(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should handle unicode in feature description."""
        monkeypatch.chdir(git_repo)

        # Create and stage a file
        (git_repo / "unicode.py").write_text("# Unicode test\n")
        stage_changes()

        sha = create_commit(
            phase="build",
            feature="Add émoji support 🚀",
            run_id="01HQ123",
        )

        assert sha is not None

        # Verify unicode is preserved
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "émoji" in result.stdout
        assert "🚀" in result.stdout


class TestGitCommitErrorHandling:
    """Integration tests for git commit error handling."""

    def test_stage_in_non_git_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise HookError when staging outside a git repo."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(HookError) as exc_info:
            stage_changes()

        assert exc_info.value.code == "GIT_STAGE_FAILED"

    def test_has_staged_changes_in_non_git_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise HookError when checking staged changes outside a git repo."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(HookError) as exc_info:
            has_staged_changes()

        assert exc_info.value.code == "GIT_DIFF_FAILED"


class TestPreCommitHookIntegration:
    """Integration tests for pre-commit hook handling."""

    def test_pre_commit_hook_rejects(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise HookError when pre-commit hook rejects commit."""
        monkeypatch.chdir(git_repo)

        # Create a pre-commit hook that always rejects
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text(
            "#!/bin/bash\necho 'Pre-commit hook rejected' >&2\nexit 1\n"
        )
        pre_commit.chmod(0o755)

        # Create and stage a file
        (git_repo / "test.py").write_text("# Test\n")
        stage_changes()

        # Attempt to commit - should raise HookError
        with pytest.raises(HookError) as exc_info:
            create_commit(
                phase="build",
                feature="Test feature",
                run_id="01HQ123456",
            )

        assert exc_info.value.code == "GIT_COMMIT_FAILED"

    def test_pre_commit_hook_modifies_files(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should handle pre-commit hook that modifies files and exits 0."""
        monkeypatch.chdir(git_repo)

        # Create a pre-commit hook that modifies the file (simulating a formatter)
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text(
            "#!/bin/bash\n"
            "# Simulate a formatter that adds a trailing newline\n"
            "for file in $(git diff --cached --name-only); do\n"
            '    if [[ -f "$file" ]]; then\n'
            "        echo '' >> \"$file\"\n"
            "    fi\n"
            "done\n"
            "exit 0\n"
        )
        pre_commit.chmod(0o755)

        # Create and stage a file
        (git_repo / "format_test.py").write_text("# No trailing newline")
        stage_changes()

        # Commit should succeed and include hook modifications via amend
        sha = create_commit(
            phase="build",
            feature="Test formatting",
            run_id="01HQ789",
        )

        assert sha is not None
        assert len(sha) == 40

        # Verify the commit was created
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[adw] Build: Test formatting" in result.stdout

    def test_skip_hooks_bypasses_pre_commit(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should skip pre-commit hook when skip_hooks=True."""
        monkeypatch.chdir(git_repo)

        # Create a pre-commit hook that always rejects
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text(
            "#!/bin/bash\necho 'Pre-commit hook rejected' >&2\nexit 1\n"
        )
        pre_commit.chmod(0o755)

        # Create and stage a file
        (git_repo / "skip_test.py").write_text("# Skip hooks test\n")
        stage_changes()

        # Commit with skip_hooks=True should succeed despite rejecting hook
        sha = create_commit(
            phase="build",
            feature="Skip hooks test",
            run_id="01HQ456",
            skip_hooks=True,
        )

        assert sha is not None
        assert len(sha) == 40

        # Verify commit was created
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[adw] Build: Skip hooks test" in result.stdout


class TestBuildCommitDiffFlowIntegration:
    """Integration tests for the full BUILD → commit → diff capture flow (ISS-009).

    Tests the end-to-end workflow where:
    1. BUILD phase creates files
    2. Auto-commit stages and commits all changes
    3. Git diff captures the changes from the commit
    """

    def test_full_build_commit_diff_flow(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should create files, commit them, and capture diff correctly."""
        monkeypatch.chdir(git_repo)

        # Simulate BUILD phase creating new files (as LLM would)
        (git_repo / "src").mkdir()
        (git_repo / "src" / "main.py").write_text("def main():\n    print('Hello')\n")
        (git_repo / "src" / "utils.py").write_text("def helper():\n    pass\n")
        (git_repo / "tests").mkdir()
        (git_repo / "tests" / "test_main.py").write_text("def test_main():\n    pass\n")

        # Step 1: Stage all changes (including untracked files)
        files = stage_changes()

        assert len(files) == 3
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "tests/test_main.py" in files

        # Step 2: Create commit
        sha = create_commit(
            phase="build",
            feature="Add main application",
            run_id="01HQ123456",
        )

        assert sha is not None
        assert len(sha) == 40

        # Step 3: Verify git diff HEAD~1 captures the changes
        diff_result = subprocess.run(
            ["git", "diff", "HEAD~1", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        diff_files = diff_result.stdout.strip().split("\n")

        assert "src/main.py" in diff_files
        assert "src/utils.py" in diff_files
        assert "tests/test_main.py" in diff_files

        # Verify full diff content is available
        full_diff = subprocess.run(
            ["git", "diff", "HEAD~1"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "def main():" in full_diff.stdout
        assert "def helper():" in full_diff.stdout
        assert "def test_main():" in full_diff.stdout

    def test_subsequent_phases_create_commits(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should create commits for VERIFY, VALIDATE, DOCUMENT phases too."""
        monkeypatch.chdir(git_repo)

        # BUILD phase: create initial code
        (git_repo / "app.py").write_text("# App code\n")
        stage_changes()
        build_sha = create_commit(
            phase="build", feature="Add app", run_id="01HQ001"
        )
        assert build_sha is not None

        # VERIFY phase: add tests
        (git_repo / "test_app.py").write_text("# Tests\n")
        stage_changes()
        verify_sha = create_commit(
            phase="verify", feature="Add app", run_id="01HQ001"
        )
        assert verify_sha is not None
        assert verify_sha != build_sha

        # VALIDATE phase: modify code based on validation
        (git_repo / "app.py").write_text("# App code - validated\n")
        stage_changes()
        validate_sha = create_commit(
            phase="validate", feature="Add app", run_id="01HQ001"
        )
        assert validate_sha is not None
        assert validate_sha != verify_sha

        # DOCUMENT phase: add docs
        (git_repo / "README.md").write_text("# Documentation\n")
        stage_changes()
        doc_sha = create_commit(
            phase="document", feature="Add app", run_id="01HQ001"
        )
        assert doc_sha is not None
        assert doc_sha != validate_sha

        # Verify all commits exist with correct messages
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-4"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[adw] Build:" in log_result.stdout
        assert "[adw] Verify:" in log_result.stdout
        assert "[adw] Validate:" in log_result.stdout
        assert "[adw] Document:" in log_result.stdout

    def test_untracked_files_are_staged(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should stage untracked files (new files created by LLM)."""
        monkeypatch.chdir(git_repo)

        # Create new files (simulating LLM output)
        (git_repo / "new_module.py").write_text("# New module\n")
        (git_repo / "new_test.py").write_text("# New test\n")

        # Verify files are untracked before staging
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "?? new_module.py" in status_result.stdout
        assert "?? new_test.py" in status_result.stdout

        # Stage changes - should stage untracked files with git add -A
        files = stage_changes()

        assert "new_module.py" in files
        assert "new_test.py" in files

        # Verify files are now staged
        assert has_staged_changes() is True

        # Commit and verify
        sha = create_commit(
            phase="build",
            feature="Add modules",
            run_id="01HQ789",
        )
        assert sha is not None

        # Verify commit includes the new files
        diff_result = subprocess.run(
            ["git", "diff", "HEAD~1", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "new_module.py" in diff_result.stdout
        assert "new_test.py" in diff_result.stdout

    def test_no_changes_returns_none(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return None when no changes to commit (empty phase)."""
        monkeypatch.chdir(git_repo)

        # Stage with no changes
        files = stage_changes()
        assert files == []

        # Commit should return None
        sha = create_commit(
            phase="build",
            feature="Empty build",
            run_id="01HQ000",
        )
        assert sha is None

    def test_worktree_support(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should work correctly with worktree paths (ISS-009 worktree fix)."""
        # Create a worktree
        worktree_path = git_repo.parent / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature/test"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Create files in worktree (not the main repo)
        (worktree_path / "worktree_file.py").write_text("# Worktree code\n")

        # Stage and commit using working_dir parameter
        files = stage_changes(working_dir=worktree_path)
        assert "worktree_file.py" in files

        sha = create_commit(
            phase="build",
            feature="Worktree feature",
            run_id="01HQWT1",
            working_dir=worktree_path,
        )
        assert sha is not None

        # Verify commit exists in worktree
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[adw] Build: Worktree feature" in log_result.stdout

        # Cleanup worktree
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path)],
            cwd=git_repo,
            capture_output=True,
        )
