#!/bin/bash
# ADW Pre-Hook: Validate PR Exists for Ship Phase
#
# This hook:
# 1. Verifies the run's PR exists (by ADW_PR_URL, else the current branch)
# 2. Checks the PR is in a mergeable state
# 3. Writes pre_hook_vars.json (pr_number, pr_url, pr_state, pr_mergeable)
#    to the artifacts dir for template rendering
#
# Environment variables provided by ADW:
#   ADW_PR_URL       - The run's PR URL (if the document phase opened one)
#   ADW_ARTIFACTS_DIR - Artifacts directory for this phase
#
# Exit codes:
#   0 - Success (PR exists and is ready)
#   1 - Error (no PR, not mergeable, or other issue)

set -e

echo "Ship phase pre-hook: Validating PR exists..."

# =============================================================================
# STEP 1: Check if gh CLI is available
# =============================================================================

if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Install it with: brew install gh"
    exit 1
fi

# =============================================================================
# STEP 1b: Check if jq is available (needed to parse gh output)
# =============================================================================

if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed (needed to parse GitHub CLI output)"
    echo "Install it with: brew install jq"
    exit 1
fi

# =============================================================================
# STEP 2: Check if gh is authenticated
# =============================================================================

if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
fi

# =============================================================================
# STEP 3: Get current branch
# =============================================================================

current_branch=$(git branch --show-current)
if [[ -z "$current_branch" ]]; then
    echo "Error: Could not determine current branch"
    exit 1
fi

echo "Current branch: $current_branch"

# =============================================================================
# STEP 4: Check the run's PR exists (by URL, falling back to the branch)
# =============================================================================

pr_ref="${ADW_PR_URL:-$current_branch}"
echo "Checking for PR: $pr_ref"

# Try to get PR info (this will fail if no PR exists)
pr_info=$(gh pr view "$pr_ref" --json number,url,state,mergeable,title 2>&1) || {
    echo "Error: No pull request found for '$pr_ref'"
    echo "Create a PR first with: gh pr create"
    exit 1
}

# =============================================================================
# STEP 5: Parse PR information
# =============================================================================

pr_number=$(echo "$pr_info" | jq -r '.number')
pr_url=$(echo "$pr_info" | jq -r '.url')
pr_state=$(echo "$pr_info" | jq -r '.state')
pr_mergeable=$(echo "$pr_info" | jq -r '.mergeable')
pr_title=$(echo "$pr_info" | jq -r '.title')

echo "PR #$pr_number: $pr_title"
echo "URL: $pr_url"
echo "State: $pr_state"
echo "Mergeable: $pr_mergeable"

# =============================================================================
# STEP 5b: Write variables to artifacts dir for template rendering
# =============================================================================

if [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
    mkdir -p "$ADW_ARTIFACTS_DIR"
    cat > "$ADW_ARTIFACTS_DIR/pre_hook_vars.json" <<EOF
{
  "pr_number": "$pr_number",
  "pr_url": "$pr_url",
  "pr_state": "$pr_state",
  "pr_mergeable": "$pr_mergeable"
}
EOF
fi

# =============================================================================
# STEP 6: Validate PR state
# =============================================================================

if [[ "$pr_state" == "MERGED" ]]; then
    echo "Error: PR #$pr_number has already been merged"
    exit 1
fi

if [[ "$pr_state" == "CLOSED" ]]; then
    echo "Error: PR #$pr_number is closed"
    exit 1
fi

if [[ "$pr_state" != "OPEN" ]]; then
    echo "Error: PR #$pr_number is in unexpected state: $pr_state"
    exit 1
fi

# =============================================================================
# STEP 7: Check mergeability (warn but don't fail)
# =============================================================================

if [[ "$pr_mergeable" == "CONFLICTING" ]]; then
    echo "Warning: PR #$pr_number has merge conflicts"
    echo "The LLM will be informed and may choose to block the merge"
fi

if [[ "$pr_mergeable" == "UNKNOWN" ]]; then
    echo "Note: PR mergeability is still being calculated by GitHub"
fi

echo ""
echo "Ship phase pre-hook complete"
echo "PR #$pr_number is ready for deployment review"
