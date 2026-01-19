#!/bin/bash
# ADW Post-Hook: Process Ship Phase Output and Merge PR
#
# This hook:
# 1. Parses LLM output for deployment status markers
# 2. Extracts ship report and release notes
# 3. Optionally merges the PR based on LLM decision
# 4. Updates task manager status (if configured)
#
# Environment variables provided by ADW:
#   ADW_FEATURE      - The feature description for this run
#   ADW_RUN_ID       - The unique run identifier
#   ADW_PHASE        - Current phase (should be "ship")
#   ADW_LLM_OUTPUT   - Full LLM output (post-hook only)
#   ADW_ARTIFACTS_DIR - Artifacts directory for this phase
#   ADW_PR_NUMBER    - PR number (from pre-hook)
#
# Ship configuration (from project config):
#   ADW_SHIP_MERGE_ON_SUCCESS     - Whether to auto-merge (true/false)
#   ADW_SHIP_DELETE_BRANCH        - Delete branch after merge (true/false)
#   ADW_SHIP_MERGE_METHOD         - Merge method (merge/squash/rebase)
#
# Exit codes:
#   0 - Success
#   1 - Error or deployment blocked

set -e

echo "Ship phase post-hook: Processing deployment output..."

# =============================================================================
# STEP 1: Parse deployment status markers from LLM output
# =============================================================================

deployment_status=""
pr_merge_approved=""
version_deployed=""
merge_reason=""

if [[ -n "$ADW_LLM_OUTPUT" ]]; then
    # Extract status markers using grep
    deployment_status=$(echo "$ADW_LLM_OUTPUT" | grep -oP 'DEPLOYMENT_STATUS:\s*\K(SUCCESS|FAILED|BLOCKED)' || echo "UNKNOWN")
    pr_merge_approved=$(echo "$ADW_LLM_OUTPUT" | grep -oP 'PR_MERGE_APPROVED:\s*\K(true|false)' || echo "false")
    version_deployed=$(echo "$ADW_LLM_OUTPUT" | grep -oP 'VERSION_DEPLOYED:\s*\K[^\s]+' || echo "N/A")
    merge_reason=$(echo "$ADW_LLM_OUTPUT" | grep -oP 'MERGE_REASON:\s*\K.*' || echo "No reason provided")

    echo "Parsed status:"
    echo "  Deployment Status: $deployment_status"
    echo "  PR Merge Approved: $pr_merge_approved"
    echo "  Version Deployed: $version_deployed"
    echo "  Merge Reason: $merge_reason"
fi

# =============================================================================
# STEP 2: Save artifacts
# =============================================================================

if [[ -n "$ADW_LLM_OUTPUT" ]] && [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
    # Save the full ship report
    ship_report_file="$ADW_ARTIFACTS_DIR/ship_report.md"
    echo "$ADW_LLM_OUTPUT" > "$ship_report_file"
    echo "Ship report saved to: $ship_report_file"

    # Extract and save release notes if version was deployed
    if [[ "$version_deployed" != "N/A" ]]; then
        # Look for release notes section in output
        if echo "$ADW_LLM_OUTPUT" | grep -qi "release notes"; then
            release_notes_file="$ADW_ARTIFACTS_DIR/release_notes.md"
            # Extract content after "Release Notes" header
            echo "$ADW_LLM_OUTPUT" | sed -n '/[Rr]elease [Nn]otes/,$p' > "$release_notes_file"
            echo "Release notes saved to: $release_notes_file"
        fi
    fi
fi

# =============================================================================
# STEP 3: Handle deployment status
# =============================================================================

if [[ "$deployment_status" == "FAILED" ]]; then
    echo "Error: Deployment failed"
    echo "Reason: $merge_reason"
    exit 1
fi

if [[ "$deployment_status" == "BLOCKED" ]]; then
    echo "Warning: Deployment blocked by LLM"
    echo "Reason: $merge_reason"
    echo "PR will not be merged automatically"
    exit 0  # Not an error, just blocked
fi

# =============================================================================
# STEP 4: Handle PR merge (if approved and configured)
# =============================================================================

if [[ "$pr_merge_approved" == "true" ]]; then
    echo "LLM approved PR merge"

    # Check if auto-merge is enabled
    merge_enabled="${ADW_SHIP_MERGE_ON_SUCCESS:-false}"

    if [[ "$merge_enabled" != "true" ]]; then
        echo "Auto-merge is disabled in ship config"
        echo "PR #$ADW_PR_NUMBER is ready for manual merge"
        exit 0
    fi

    # Get merge configuration
    merge_method="${ADW_SHIP_MERGE_METHOD:-squash}"
    delete_branch="${ADW_SHIP_DELETE_BRANCH:-true}"

    echo "Merging PR #$ADW_PR_NUMBER with method: $merge_method"

    # Build merge command
    merge_cmd="gh pr merge $ADW_PR_NUMBER --$merge_method"

    if [[ "$delete_branch" == "true" ]]; then
        merge_cmd="$merge_cmd --delete-branch"
    fi

    # Execute merge
    if eval "$merge_cmd"; then
        echo "PR #$ADW_PR_NUMBER merged successfully"

        # Log the merge for task manager sync (if configured)
        if [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
            echo "{\"merged\": true, \"pr_number\": $ADW_PR_NUMBER, \"method\": \"$merge_method\", \"version\": \"$version_deployed\"}" > "$ADW_ARTIFACTS_DIR/merge_record.json"
        fi
    else
        echo "Error: Failed to merge PR #$ADW_PR_NUMBER"
        echo "The PR may require manual review"
        exit 1
    fi
else
    echo "LLM did not approve PR merge"
    echo "Reason: $merge_reason"
    echo "PR #$ADW_PR_NUMBER will not be merged automatically"
fi

echo ""
echo "Ship phase post-hook complete"
