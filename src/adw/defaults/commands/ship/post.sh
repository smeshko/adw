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
#   ADW_TASK_ID      - Task ID from task manager (if configured)
#
# Ship configuration (from project config):
#   ADW_SHIP_AUTO_MERGE       - Whether to auto-merge (true/false, default: true)
#   ADW_SHIP_DELETE_BRANCH    - Delete branch after merge (true/false, default: true)
#   ADW_SHIP_MERGE_STRATEGY   - Merge method (merge/squash/rebase, default: squash)
#   ADW_SHIP_BYPASS_CI        - Bypass CI checks using --admin (true/false, default: false)
#
# Exit codes:
#   0 - Success
#   1 - Error or deployment failed

set -e

echo "Ship phase post-hook: Processing deployment output..."

# =============================================================================
# STEP 1: Parse deployment status markers from LLM output
# =============================================================================

deployment_status=""
pr_merge_approved=""
version_deployed=""
merge_reason=""
pr_number=""

if [[ -n "$ADW_LLM_OUTPUT" ]]; then
    # Extract status markers using sed -E for extended regex (portable on macOS and Linux)
    # Format expected: KEY: value (on its own line or within a code block)

    deployment_status=$(echo "$ADW_LLM_OUTPUT" | sed -E -n 's/.*DEPLOYMENT_STATUS:[[:space:]]*(SUCCESS|FAILED|BLOCKED).*/\1/p' | head -1)
    [[ -z "$deployment_status" ]] && deployment_status="UNKNOWN"

    pr_merge_approved=$(echo "$ADW_LLM_OUTPUT" | sed -E -n 's/.*PR_MERGE_APPROVED:[[:space:]]*(true|false).*/\1/p' | head -1)
    [[ -z "$pr_merge_approved" ]] && pr_merge_approved="false"

    version_deployed=$(echo "$ADW_LLM_OUTPUT" | sed -E -n 's/.*VERSION_DEPLOYED:[[:space:]]*([^[:space:]]*).*/\1/p' | head -1)
    [[ -z "$version_deployed" ]] && version_deployed="N/A"

    merge_reason=$(echo "$ADW_LLM_OUTPUT" | sed -E -n 's/.*MERGE_REASON:[[:space:]]*(.*)/\1/p' | head -1)
    [[ -z "$merge_reason" ]] && merge_reason="No reason provided"

    # Also extract PR_NUMBER from LLM output if available (fallback to env var)
    pr_number_from_output=$(echo "$ADW_LLM_OUTPUT" | sed -E -n 's/.*PR_NUMBER:[[:space:]]*([0-9]+).*/\1/p' | head -1)
    pr_number="${pr_number_from_output:-$ADW_PR_NUMBER}"

    echo "Parsed status:"
    echo "  Deployment Status: $deployment_status"
    echo "  PR Merge Approved: $pr_merge_approved"
    echo "  Version Deployed: $version_deployed"
    echo "  Merge Reason: $merge_reason"
    echo "  PR Number: $pr_number"
else
    echo "Warning: No LLM output available"
    deployment_status="UNKNOWN"
    pr_merge_approved="false"
    version_deployed="N/A"
    merge_reason="No LLM output to parse"
    pr_number="$ADW_PR_NUMBER"
fi

# Validate required fields
if [[ "$deployment_status" == "UNKNOWN" ]]; then
    echo "Warning: Could not parse DEPLOYMENT_STATUS from LLM output"
fi

if [[ -z "$pr_number" ]]; then
    echo "Warning: No PR number available - merge will be skipped"
fi

# =============================================================================
# STEP 2: Save artifacts
# =============================================================================

if [[ -n "$ADW_LLM_OUTPUT" ]] && [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
    # Ensure artifacts directory exists
    mkdir -p "$ADW_ARTIFACTS_DIR"

    # Save the full ship report
    ship_report_file="$ADW_ARTIFACTS_DIR/ship_report.md"
    echo "$ADW_LLM_OUTPUT" > "$ship_report_file"
    echo "Ship report saved to: $ship_report_file"

    # Extract and save release notes if present
    if echo "$ADW_LLM_OUTPUT" | grep -qi "release notes"; then
        release_notes_file="$ADW_ARTIFACTS_DIR/release_notes.md"
        # Extract content after "Release Notes" header
        echo "$ADW_LLM_OUTPUT" | sed -n '/[Rr]elease [Nn]otes/,$p' > "$release_notes_file"
        echo "Release notes saved to: $release_notes_file"
    fi

    # Save parsed status as JSON for programmatic access
    status_file="$ADW_ARTIFACTS_DIR/ship_status.json"

    # Helper function to escape strings for JSON
    json_escape() {
        local str="$1"
        # Escape backslashes, quotes, and control characters
        str="${str//\\/\\\\}"
        str="${str//\"/\\\"}"
        str="${str//$'\n'/\\n}"
        str="${str//$'\r'/\\r}"
        str="${str//$'\t'/\\t}"
        echo "$str"
    }

    # Escape strings that may contain special characters
    merge_reason_escaped=$(json_escape "$merge_reason")

    # Convert string booleans to JSON booleans safely
    pr_merge_approved_json="false"
    [[ "$pr_merge_approved" == "true" ]] && pr_merge_approved_json="true"

    cat > "$status_file" <<EOF
{
  "deployment_status": "$deployment_status",
  "pr_merge_approved": $pr_merge_approved_json,
  "version_deployed": "$version_deployed",
  "merge_reason": "$merge_reason_escaped",
  "pr_number": ${pr_number:-null}
}
EOF
    echo "Status saved to: $status_file"
fi

# =============================================================================
# STEP 3: Handle deployment status (exit early on failure/blocked)
# =============================================================================

if [[ "$deployment_status" == "FAILED" ]]; then
    echo ""
    echo "=========================================="
    echo "DEPLOYMENT FAILED"
    echo "=========================================="
    echo "Reason: $merge_reason"
    echo ""
    echo "The PR will NOT be merged automatically."
    echo "Please review the failure diagnosis in the ship report."
    exit 1
fi

if [[ "$deployment_status" == "BLOCKED" ]]; then
    echo ""
    echo "=========================================="
    echo "DEPLOYMENT BLOCKED"
    echo "=========================================="
    echo "Reason: $merge_reason"
    echo ""
    echo "PR #$pr_number will not be merged automatically."
    echo "Please resolve blocking issues and retry."
    exit 0  # Not an error, just blocked
fi

# =============================================================================
# STEP 4: Handle PR merge (if approved and configured)
# =============================================================================

if [[ "$pr_merge_approved" == "true" ]]; then
    echo ""
    echo "LLM approved PR merge"

    # Validate PR number is available
    if [[ -z "$pr_number" ]]; then
        echo "Error: Cannot merge - no PR number available"
        exit 1
    fi

    # Check if auto-merge is enabled (default: true)
    auto_merge="${ADW_SHIP_AUTO_MERGE:-true}"

    if [[ "$auto_merge" != "true" ]]; then
        echo ""
        echo "=========================================="
        echo "AUTO-MERGE DISABLED"
        echo "=========================================="
        echo "Auto-merge is disabled in ship.pr.auto_merge config."
        echo ""
        echo "PR #$pr_number is ready for manual merge."
        # Try to get PR URL for convenience
        pr_url=$(gh pr view "$pr_number" --json url -q '.url' 2>/dev/null || echo "")
        if [[ -n "$pr_url" ]]; then
            echo "PR URL: $pr_url"
        fi
        echo ""
        echo "To merge manually:"
        echo "  gh pr merge $pr_number --squash"
        exit 0
    fi

    # Get merge configuration
    merge_strategy="${ADW_SHIP_MERGE_STRATEGY:-squash}"
    delete_branch="${ADW_SHIP_DELETE_BRANCH:-true}"

    echo "Merging PR #$pr_number with strategy: $merge_strategy"

    # Build merge body message
    if [[ "$version_deployed" != "N/A" && -n "$version_deployed" ]]; then
        merge_body="Shipped via ADW v$version_deployed"
    else
        merge_body="Shipped via ADW"
    fi

    # Build merge command using array (safer than eval with strings)
    merge_cmd=(gh pr merge "$pr_number")

    case "$merge_strategy" in
        squash)
            merge_cmd+=(--squash --body "$merge_body")
            ;;
        merge)
            merge_cmd+=(--merge --body "$merge_body")
            ;;
        rebase)
            # Rebase doesn't support --body
            merge_cmd+=(--rebase)
            ;;
        *)
            echo "Warning: Unknown merge strategy '$merge_strategy', using squash"
            merge_cmd+=(--squash --body "$merge_body")
            ;;
    esac

    # Add delete-branch flag if configured
    if [[ "$delete_branch" == "true" ]]; then
        merge_cmd+=(--delete-branch)
        echo "Branch will be deleted after merge"
    fi

    # Add --admin flag to bypass CI checks if configured (requires admin access)
    bypass_ci="${ADW_SHIP_BYPASS_CI:-false}"
    if [[ "$bypass_ci" == "true" ]]; then
        merge_cmd+=(--admin)
        echo "Bypassing CI checks with --admin flag (requires admin access)"
    fi

    # Execute merge (using array expansion for proper quoting)
    echo "Executing: ${merge_cmd[*]}"

    # Capture both stdout and stderr, and exit code
    merge_output=""
    merge_exit_code=0
    merge_output=$("${merge_cmd[@]}" 2>&1) || merge_exit_code=$?

    if [[ $merge_exit_code -eq 0 ]]; then
        echo ""
        echo "=========================================="
        echo "PR MERGED SUCCESSFULLY"
        echo "=========================================="
        echo "PR #$pr_number merged with strategy: $merge_strategy"
        if [[ "$version_deployed" != "N/A" ]]; then
            echo "Version deployed: $version_deployed"
        fi
        if [[ "$delete_branch" == "true" ]]; then
            echo "Branch deleted: yes"
        fi

        # Save merge record for task manager sync
        if [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
            merge_record_file="$ADW_ARTIFACTS_DIR/merge_record.json"

            # Convert string boolean to JSON boolean
            delete_branch_json="false"
            [[ "$delete_branch" == "true" ]] && delete_branch_json="true"

            # Escape merge_body for JSON (reuse json_escape if in scope, otherwise inline)
            merge_body_escaped="${merge_body//\\/\\\\}"
            merge_body_escaped="${merge_body_escaped//\"/\\\"}"

            cat > "$merge_record_file" <<EOF
{
  "merged": true,
  "pr_number": $pr_number,
  "merge_strategy": "$merge_strategy",
  "version": "$version_deployed",
  "branch_deleted": $delete_branch_json,
  "merge_body": "$merge_body_escaped"
}
EOF
            echo "Merge record saved to: $merge_record_file"
        fi
    else
        echo ""
        echo "=========================================="
        echo "PR MERGE FAILED"
        echo "=========================================="
        echo "Exit code: $merge_exit_code"
        echo ""

        # Analyze error output for common patterns
        if echo "$merge_output" | grep -qi "conflict"; then
            echo "Error: Merge conflicts detected"
            echo ""
            echo "Remediation:"
            echo "  1. Resolve conflicts locally: git pull origin main && git merge main"
            echo "  2. Push the resolved branch"
            echo "  3. Retry: gh pr merge $pr_number --$merge_strategy"
        elif echo "$merge_output" | grep -qi "status check"; then
            echo "Error: Required status checks have not passed"
            echo ""
            echo "Remediation:"
            echo "  1. Wait for CI checks to complete"
            echo "  2. Fix any failing checks"
            echo "  3. Retry: gh pr merge $pr_number --$merge_strategy"
        elif echo "$merge_output" | grep -qi "review"; then
            echo "Error: PR requires review approval"
            echo ""
            echo "Remediation:"
            echo "  1. Request review from team members"
            echo "  2. Address any review comments"
            echo "  3. Retry: gh pr merge $pr_number --$merge_strategy"
        elif echo "$merge_output" | grep -qi "protected"; then
            echo "Error: Branch protection rules violated"
            echo ""
            echo "Remediation:"
            echo "  1. Check branch protection settings"
            echo "  2. Ensure all requirements are met"
            echo "  3. Retry: gh pr merge $pr_number --$merge_strategy"
        else
            echo "Error output:"
            echo "$merge_output"
            echo ""
            echo "Manual merge instructions:"
            echo "  1. Review the error above"
            echo "  2. Fix any issues"
            echo "  3. Merge manually: gh pr merge $pr_number --$merge_strategy"
        fi

        exit 1
    fi
else
    echo ""
    echo "LLM did not approve PR merge"
    echo "Reason: $merge_reason"
    echo ""
    if [[ -n "$pr_number" ]]; then
        echo "PR #$pr_number will not be merged automatically."
        echo "Please review the ship report and merge manually if appropriate."
    fi
fi

# =============================================================================
# STEP 5: Task Manager Integration (if configured)
# =============================================================================

# Check if task manager integration is available via ADW_TASK_ID
if [[ -n "$ADW_TASK_ID" ]] && [[ "$pr_merge_approved" == "true" ]] && [[ $merge_exit_code -eq 0 ]]; then
    echo ""
    echo "Updating task manager status..."

    # Task manager update is best-effort - don't fail the whole hook
    # The SDK handles task manager updates via Python code, but we log intent here
    if [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
        task_update_file="$ADW_ARTIFACTS_DIR/task_update_request.json"
        cat > "$task_update_file" <<EOF
{
  "task_id": "$ADW_TASK_ID",
  "status": "done",
  "pr_merged": true,
  "pr_number": $pr_number,
  "version": "$version_deployed"
}
EOF
        echo "Task update request saved to: $task_update_file"
        echo "Note: Task manager status update will be handled by ADW SDK"
    fi
fi

echo ""
echo "Ship phase post-hook complete"
