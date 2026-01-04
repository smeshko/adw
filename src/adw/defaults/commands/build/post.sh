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
# It respects the git.auto_commit and git.skip_hooks configuration settings.

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
import traceback

# Flag for debug output
DEBUG = os.environ.get('ADW_DEBUG', '').lower() in ('1', 'true', 'yes')

def log_error(msg: str, exc: Exception | None = None) -> None:
    \"\"\"Log error with optional traceback in debug mode.\"\"\"
    print(f'Error: {msg}', file=sys.stderr)
    if DEBUG and exc:
        traceback.print_exc()

try:
    from adw.hooks.git_commit import (
        stage_changes,
        create_commit,
    )
    from adw.config import ConfigLoader
except ImportError as e:
    # ADW not installed in this environment, skip gracefully
    if DEBUG:
        print(f'ADW not available: {e}', file=sys.stderr)
    sys.exit(0)

# Load project config to check if git and auto_commit are enabled
try:
    loader = ConfigLoader()
    config = loader.load()
except FileNotFoundError:
    # No config file, skip (expected in non-ADW projects)
    if DEBUG:
        print('No adw.yaml found, skipping', file=sys.stderr)
    sys.exit(0)
except Exception as e:
    # Unexpected error loading config - log it
    log_error(f'Failed to load config: {e}', e)
    sys.exit(0)

if not config.git.enabled:
    # Git integration disabled, skip
    if DEBUG:
        print('Git integration disabled', file=sys.stderr)
    sys.exit(0)

if not config.git.auto_commit:
    # Auto-commit disabled, skip
    if DEBUG:
        print('Auto-commit disabled', file=sys.stderr)
    sys.exit(0)

# Get phase, feature, run_id from environment
phase = os.environ.get('ADW_PHASE', '')
feature = os.environ.get('ADW_FEATURE', '')
run_id = os.environ.get('ADW_RUN_ID', '')

if not all([phase, feature, run_id]):
    print('Warning: Missing required environment variables', file=sys.stderr)
    sys.exit(0)

# Stage all changes
try:
    staged_files = stage_changes()
    if not staged_files:
        print('No changes to commit')
        sys.exit(0)
    print(f'Staged {len(staged_files)} file(s)')
except Exception as e:
    log_error(f'Failed to stage changes: {e}', e)
    sys.exit(1)

# Create commit with optional custom template and skip_hooks setting
try:
    template = config.git.commit_template
    skip_hooks = config.git.skip_hooks
    sha = create_commit(
        phase=phase,
        feature=feature,
        run_id=run_id,
        template=template,
        skip_hooks=skip_hooks,
    )
    if sha:
        print(f'Created commit: {sha[:8]}')
    else:
        print('No changes to commit')
except Exception as e:
    log_error(f'Failed to create commit: {e}', e)
    sys.exit(1)
" 2>&1 || exit $?
