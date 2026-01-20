#!/bin/bash
# ADW Pre-Hook: Git Branch Management
#
# This hook creates or switches to a feature branch based on the run's
# feature description. It integrates with ADW's git configuration.
#
# When running in worktree mode (ISS-032), the worktree is already created
# with the correct feature branch, so this hook verifies the branch exists
# and skips if already on the correct branch.
#
# Environment variables provided by ADW:
#   ADW_FEATURE    - The feature description for this run
#   ADW_RUN_ID     - The unique run identifier
#   ADW_PHASE      - Current phase (should be "plan")
#
# Exit codes:
#   0 - Success (branch created/switched, already on branch, or git disabled)
#   1 - Error (uncommitted changes or git failure)
#
# This hook is designed to be run as a pre-hook for the plan phase.
# It should NOT be run for other phases.

set -e

# Check if this is the plan phase (only create branch on plan start)
if [[ "$ADW_PHASE" != "plan" ]]; then
    exit 0
fi

# Check if ADW_FEATURE is set
if [[ -z "$ADW_FEATURE" ]]; then
    echo "Warning: ADW_FEATURE not set, skipping git branch creation"
    exit 0
fi

# Try to invoke Python helper to check config and create branch
# If Python is not available or module not found, skip gracefully
python3 -c "
import sys
import os
import subprocess

try:
    from adw.hooks.git_branch import (
        sanitize_branch_name,
        check_uncommitted_changes,
        create_or_switch_branch,
    )
    from adw.config import ConfigLoader
except ImportError:
    # ADW not installed in this environment, skip
    sys.exit(0)

# Load project config to check if git is enabled
try:
    loader = ConfigLoader()
    config = loader.load()
except Exception:
    # No config or error loading, skip
    sys.exit(0)

if not config.git.enabled:
    # Git integration disabled, skip
    sys.exit(0)

# Get feature from environment
feature = os.environ.get('ADW_FEATURE', '')
if not feature:
    sys.exit(0)

# Calculate expected branch name
branch_name = config.git.branch_prefix + sanitize_branch_name(feature)

# Check if already on the expected branch (ISS-032: worktree mode)
# When using worktrees, the orchestrator creates the worktree with the
# feature branch already, so we just need to verify we're on it
result = subprocess.run(
    ['git', 'branch', '--show-current'],
    capture_output=True,
    text=True,
    check=False,
)
current_branch = result.stdout.strip() if result.returncode == 0 else ''

if current_branch == branch_name:
    print(f'Already on branch: {branch_name}')
    sys.exit(0)

# Check for uncommitted changes (only if we need to switch branches)
if check_uncommitted_changes():
    print('Error: Uncommitted changes detected.')
    print('Please commit or stash your changes before running ADW.')
    sys.exit(1)

# Create/switch to branch
print(f'Creating/switching to branch: {branch_name}')

try:
    create_or_switch_branch(branch_name)
    print(f'Now on branch: {branch_name}')
except Exception as e:
    print(f'Error creating branch: {e}')
    sys.exit(1)
" 2>&1 || exit $?
