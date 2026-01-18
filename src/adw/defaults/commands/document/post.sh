#!/bin/bash
# ADW Post-Hook: Extract Feature Documentation
#
# This hook:
# 1. Extracts feature doc content from LLM output (if present between markers)
# 2. Saves it to the artifacts directory for reference
#
# Environment variables provided by ADW:
#   ADW_FEATURE      - The feature description for this run
#   ADW_RUN_ID       - The unique run identifier
#   ADW_PHASE        - Current phase (should be "document")
#   ADW_LLM_OUTPUT   - Full LLM output (post-hook only)
#   ADW_ARTIFACTS_DIR - Artifacts directory for this phase
#
# Exit codes:
#   0 - Success
#   1 - Error
#
# Note: The actual feature doc creation and git commits happen within the LLM
# execution (per instructions.xml). This hook just extracts content for artifacts.

set -e

# =============================================================================
# STEP 1: Extract feature doc from LLM response (if markers present)
# =============================================================================
# Markers: "# FEATURE DOC OUTPUT" ... "# END FEATURE DOC OUTPUT"

if [[ -n "$ADW_LLM_OUTPUT" ]] && [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
    # Check if feature doc markers exist in the output
    if echo "$ADW_LLM_OUTPUT" | grep -q "# FEATURE DOC OUTPUT"; then
        echo "Extracting feature documentation from LLM response..."

        # Extract content between markers using sed
        # - Find line with "# FEATURE DOC OUTPUT", start printing from next line
        # - Stop when we hit "# END FEATURE DOC OUTPUT"
        extracted=$(echo "$ADW_LLM_OUTPUT" | sed -n '/^# FEATURE DOC OUTPUT$/,/^# END FEATURE DOC OUTPUT$/p' | sed '1d;$d')

        if [[ -n "$extracted" ]]; then
            # Write extracted content to feature_doc.md artifact
            output_file="$ADW_ARTIFACTS_DIR/feature_doc.md"
            echo "$extracted" > "$output_file"
            echo "Feature documentation extracted to: $output_file"
        else
            echo "Warning: Feature doc markers found but no content extracted"
        fi
    else
        echo "No feature documentation markers found (changes may not be significant)"
    fi

    # =============================================================================
    # STEP 2: Extract PR description from the end of the output
    # =============================================================================
    # The PR description should be at the end after the documentation report
    # Look for "## Summary" which starts the PR description

    if echo "$ADW_LLM_OUTPUT" | grep -q "^## Summary"; then
        echo "Extracting PR description from LLM response..."

        # Extract from ## Summary to end of output
        # This assumes the PR description is the final section
        pr_desc=$(echo "$ADW_LLM_OUTPUT" | sed -n '/^## Summary$/,$p')

        if [[ -n "$pr_desc" ]]; then
            pr_output_file="$ADW_ARTIFACTS_DIR/pr_description.md"
            echo "$pr_desc" > "$pr_output_file"
            echo "PR description extracted to: $pr_output_file"
        fi
    fi

    # =============================================================================
    # STEP 3: Save full output as document_output.md
    # =============================================================================
    doc_output_file="$ADW_ARTIFACTS_DIR/document_output.md"
    echo "$ADW_LLM_OUTPUT" > "$doc_output_file"
    echo "Full document output saved to: $doc_output_file"
fi

echo "Document phase post-hook complete"
