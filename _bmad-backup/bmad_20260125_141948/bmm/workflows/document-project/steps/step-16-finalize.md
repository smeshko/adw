---
name: 'step-16-finalize'
description: 'Finalize documentation and output completion summary'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-16-finalize.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
indexFile: '{output_folder}/index.md'

# External Workflow References
workflowStatusPath: '{project-root}/_bmad/bmm/workflows/workflow-status'
---

# Step 16: Finalize

## STEP GOAL:

Complete the documentation workflow, finalize state tracking, and output completion summary with exit code.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: This is the final step - workflow ends here
- 🤖 YOU ARE AN EXECUTOR, running autonomously

### Role Reinforcement:

- ✅ You are a technical documentarian executing codebase analysis
- ✅ Work autonomously - this is the final step
- ✅ Log completion summary to stdout for CI visibility
- ✅ Return appropriate exit code

### Step-Specific Rules:

- 🎯 Focus only on finalization and summary
- 📊 Output structured summary to stdout
- 🔢 Return appropriate exit code
- ⏹️ Workflow terminates after this step

## EXECUTION PROTOCOLS:

- 🎯 Update workflow status if integrated
- 💾 Finalize state file
- 📊 Output completion summary to stdout
- 🔢 Exit with appropriate code (0, 1, or 2)

## CONTEXT BOUNDARIES:

- Available context: All generated documentation, warnings, errors
- Focus: Completion and exit code determination
- Limits: No new generation
- Dependencies: All previous steps complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Log Step Start

Output to stdout:
```
[step-16] Finalizing documentation workflow...
```

### 2. Update Workflow Status

If workflow-status integration is active:
- Update status with workflow completion
- Mark document-project as complete

### 3. Finalize State File

Update state file:
- Add "step-16" to completed_steps
- Set timestamps.completed = current_timestamp
- Set current_step = "completed"
- Set exit_code based on warnings/errors

### 4. Determine Exit Code

Calculate exit code:
- **0**: No errors, no warnings (or FAIL_ON_WARNING=false)
- **1**: Critical errors occurred (should not reach this step)
- **2**: Warnings occurred AND FAIL_ON_WARNING=true

### 5. Output Completion Summary

Output to stdout:
```
[step-16] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-16]
[step-16] DOCUMENT-PROJECT COMPLETE
[step-16]
[step-16] Status: {SUCCESS | COMPLETED_WITH_WARNINGS}
[step-16] Duration: {duration}
[step-16]
[step-16] Output Location: {output_folder}/
[step-16] Master Index: {output_folder}/index.md
[step-16]
[step-16] Generated Files:
{generated_files_list_formatted}
[step-16]
[step-16] Warnings: {warning_count}
[step-16] Errors: {error_count}
[step-16]
[step-16] State File: {stateFile}
[step-16] Exit Code: {exit_code}
[step-16]
[step-16] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6. Exit Workflow

Exit with code {exit_code}.

**Workflow terminates here.**

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS (Exit 0):

- All steps completed
- Documentation generated
- State file finalized
- No warnings (or FAIL_ON_WARNING=false)

### ⚠️ PARTIAL SUCCESS (Exit 2):

- All steps completed
- Documentation generated
- Warnings occurred
- FAIL_ON_WARNING=true

### ❌ FAILURE (Exit 1):

- Critical error prevented completion
- (Should not reach this step if critical error occurred)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
