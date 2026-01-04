#!/bin/bash
# ADW Post-Hook: Git Commit Changes
#
# This hook automatically stages and commits changes after phase completion.
# It integrates with ADW's git configuration to provide automatic commit
# functionality with configurable message templates.
#
# Environment variables provided by ADW:
#   ADW_FEATURE    - The feature description for this run
#   ADW_RUN_ID     - The unique run identifier
#   ADW_PHASE      - Current phase (e.g., "build", "verify")
#
# Exit codes:
#   0 - Success (commit created, no changes, or auto-commit disabled)
#   1 - Error (commit failed or git error)
#
# This hook is designed to be run as a post-hook for any phase.
# It respects the git.auto_commit configuration setting.

set -e

# Check if ADW_FEATURE and ADW_RUN_ID are set
if [[ -z "$ADW_FEATURE" ]] || [[ -z "$ADW_RUN_ID" ]]; then
    echo "Warning: ADW_FEATURE or ADW_RUN_ID not set, skipping auto-commit"
    exit 0
fi

# Check if ADW_PHASE is set
if [[ -z "$ADW_PHASE" ]]; then
    echo "Warning: ADW_PHASE not set, skipping auto-commit"
    exit 0
fi

# Try to invoke Python helper to check config and create commit
# If Python is not available or module not found, skip gracefully
python3 -c "
import sys
import os

try:
    from adw.hooks.git_commit import (
        stage_changes,
        has_staged_changes,
        create_commit,
    )
    from adw.config import ConfigLoader
except ImportError:
    # ADW not installed in this environment, skip
    sys.exit(0)

# Load project config to check if git and auto_commit are enabled
try:
    loader = ConfigLoader()
    config = loader.load()
except Exception:
    # No config or error loading, skip
    sys.exit(0)

if not config.git.enabled:
    # Git integration disabled, skip
    sys.exit(0)

if not config.git.auto_commit:
    # Auto-commit disabled, skip
    sys.exit(0)

# Get phase, feature, run_id from environment
phase = os.environ.get('ADW_PHASE', '')
feature = os.environ.get('ADW_FEATURE', '')
run_id = os.environ.get('ADW_RUN_ID', '')

if not all([phase, feature, run_id]):
    sys.exit(0)

# Stage all changes
try:
    staged_files = stage_changes()
    if not staged_files:
        print('No changes to commit')
        sys.exit(0)
    print(f'Staged {len(staged_files)} file(s)')
except Exception as e:
    print(f'Error staging changes: {e}')
    sys.exit(1)

# Create commit with optional custom template
try:
    template = config.git.commit_template
    sha = create_commit(
        phase=phase,
        feature=feature,
        run_id=run_id,
        template=template,
    )
    if sha:
        print(f'Created commit: {sha[:8]}')
    else:
        print('No changes to commit')
except Exception as e:
    print(f'Error creating commit: {e}')
    sys.exit(1)
" 2>&1 || exit $?
