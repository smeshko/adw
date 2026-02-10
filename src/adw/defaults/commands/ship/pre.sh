#!/bin/bash
# ADW Pre-Hook: Validate PR Exists for Ship Phase
#
# This hook:
# 1. Verifies a PR exists for the current branch
# 2. Checks the PR is in a mergeable state
# 3. Exports PR information for the LLM context
#
# Environment variables provided by ADW:
#   ADW_FEATURE      - The feature description for this run
#   ADW_RUN_ID       - The unique run identifier
#   ADW_PHASE        - Current phase (should be "ship")
#   ADW_ARTIFACTS_DIR - Artifacts directory for this phase
#
# Environment variables exported by this hook:
#   ADW_PR_NUMBER    - The PR number for the current branch
#   ADW_PR_URL       - The PR URL
#   ADW_PR_STATE     - The PR state (OPEN, MERGED, CLOSED)
#   ADW_PR_MERGEABLE - Whether the PR is mergeable
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
# STEP 4: Check if PR exists for this branch
# =============================================================================

echo "Checking for PR on branch: $current_branch"

# Try to get PR info (this will fail if no PR exists)
pr_info=$(gh pr view "$current_branch" --json number,url,state,mergeable,title 2>&1) || {
    echo "Error: No pull request found for branch '$current_branch'"
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

# =============================================================================
# STEP 8: Export environment variables for LLM context
# =============================================================================

export ADW_PR_NUMBER="$pr_number"
export ADW_PR_URL="$pr_url"
export ADW_PR_STATE="$pr_state"
export ADW_PR_MERGEABLE="$pr_mergeable"

echo ""
echo "Ship phase pre-hook complete"
echo "PR #$pr_number is ready for deployment review"
