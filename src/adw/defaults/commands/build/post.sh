#!/bin/bash
# ADW Post-Hook: Extract Story Output
#
# Extracts the content between the story output markers in the LLM output
# into build_output.md. PhaseRunner commits the phase's changes after this
# hook returns.
#
# Environment variables provided by ADW:
#   ADW_LLM_OUTPUT   - Full LLM output (post-hook only)
#   ADW_ARTIFACTS_DIR - Artifacts directory for this phase
#
# Exit codes:
#   0 - Success (story output extracted, or no markers present)

set -e

# =============================================================================
# Extract story output from LLM response (if markers present)
# =============================================================================
# Markers: "# UPDATED STORY OUTPUT" ... "# END STORY OUTPUT"

if [[ -n "$ADW_LLM_OUTPUT" ]] && [[ -n "$ADW_ARTIFACTS_DIR" ]]; then
    # Check if markers exist in the output
    if echo "$ADW_LLM_OUTPUT" | grep -q "# UPDATED STORY OUTPUT"; then
        echo "Extracting story output from LLM response..."

        # Extract content between markers using sed
        # - Find line with "# UPDATED STORY OUTPUT", start printing from next line
        # - Stop when we hit "# END STORY OUTPUT"
        extracted=$(echo "$ADW_LLM_OUTPUT" | sed -n '/^# UPDATED STORY OUTPUT$/,/^# END STORY OUTPUT$/p' | sed '1d;$d')

        if [[ -n "$extracted" ]]; then
            # Write extracted content to build_output.md
            output_file="$ADW_ARTIFACTS_DIR/build_output.md"
            echo "$extracted" > "$output_file"
            echo "Story output extracted to: $output_file"
        else
            echo "Warning: Markers found but no content extracted"
        fi
    fi
fi
