---
name: 'step-03-finalize'
description: 'Complete the workflow by printing summary and returning exit code'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/code-review-loop'

# File References
thisStepFile: '{workflow_path}/steps/step-03-finalize.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 3: Finalize

## STEP GOAL:

To complete the code review loop by printing a comprehensive summary of all review cycles and returning the appropriate exit code for CI integration.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🤖 This is an AUTONOMOUS workflow - proceed without user interaction
- ✅ This is the FINAL step - workflow completes here

### Role Reinforcement:

- ✅ You are completing the review process
- ✅ Ensure all work is properly summarized
- ✅ Return appropriate exit code for CI

### Step-Specific Rules:

- 🎯 Print comprehensive summary to terminal
- 🎯 Return exit code (0 = clean, 1 = issues remain)

## EXECUTION PROTOCOLS:

- 🎯 Complete all finalization tasks
- 📋 Print summary
- ✅ Return exit code

## CONTEXT FROM PREVIOUS STEPS:

Available in memory:
- `cycle_count` - total cycles executed
- `exit_reason` - why we exited ("clean", "all_false_positives", "max_cycles_reached", "review_failed")
- `exit_code` - 0 (success) or 1 (issues remain)
- `issues_fixed` - array of all fixed issues
- `issues_skipped` - array of all skipped issues
- `files_to_review` - list of files that were reviewed

---

## FINALIZATION SEQUENCE:

### 1. Print Terminal Summary

Display comprehensive summary:

```
═══════════════════════════════════════════════════════════════
  CODE REVIEW LOOP (CI) - Complete
═══════════════════════════════════════════════════════════════

  Review Summary:
  ───────────────────────────────────────────────────────────
  Total Cycles: {cycle_count} of 2
  Exit Reason: {exit_reason_description}
  Exit Code: {exit_code}

  Issues Fixed: {issues_fixed.length}
  ───────────────────────────────────────────────────────────
  {For each fixed issue:}
  • [{cycle}] {file}:{line}
    Issue: {issue}
    Fix: {fix}

  Issues Skipped (False Positives): {issues_skipped.length}
  ───────────────────────────────────────────────────────────
  {For each skipped issue:}
  • [{cycle}] {file}:{line}
    Issue: {issue}
    Reason: {reason}

═══════════════════════════════════════════════════════════════
  Workflow Complete - Exit Code: {exit_code}
═══════════════════════════════════════════════════════════════
```

### 2. Exit Reason Descriptions

Map exit_reason to human-readable description:
- `clean` → "No issues found - code is clean"
- `all_false_positives` → "All findings were false positives"
- `max_cycles_reached` → "Maximum 2 cycles reached - some issues may remain"
- `review_failed` → "Review process failed (Codex unavailable)"

### 3. Return Exit Code

The workflow returns:
- **Exit code 0** if:
  - `exit_reason == "clean"` (no issues found)
  - `exit_reason == "all_false_positives"` (all dismissed)
  - All issues were fixed within 2 cycles

- **Exit code 1** if:
  - `exit_reason == "max_cycles_reached"` (issues may remain)
  - `exit_reason == "review_failed"` (Codex failed)

### 4. Workflow Complete

The workflow is now complete. No further action needed.

---

## CRITICAL STEP COMPLETION NOTE

This is the FINAL step. After printing the summary and returning the exit code, the workflow is complete. Do not load any additional steps.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Summary printed to terminal
- Exit code returned correctly
- Workflow completed cleanly

### ❌ SYSTEM FAILURE:

- Missing summary information
- Stopping to ask user questions
- Attempting to load another step
- Not returning exit code

**Master Rule:** This is the FINAL step of an AUTONOMOUS workflow. Complete all tasks and exit cleanly with the appropriate exit code.
