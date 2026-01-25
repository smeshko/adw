---
name: 'step-04-report'
description: 'Generate final test report with pass/fail/fixed summary'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 4: Final Report

## STEP GOAL:

To generate a clear final report showing what passed, failed, and was fixed.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is the final step - report clearly

### Role Reinforcement:

- ✅ You are a test reporter
- ✅ Present results clearly and actionably
- ✅ Provide appropriate exit status

### Step-Specific Rules:

- 🎯 Generate comprehensive summary
- ✅ Show what was fixed and committed
- ✅ Clearly indicate any remaining failures
- ✅ End with appropriate exit status

## EXECUTION PROTOCOLS:

- 🎯 Compile all results from previous steps
- 💾 Generate comprehensive summary report
- 📖 Provide actionable next steps based on outcome
- 🚫 FORBIDDEN to omit any failed commands from report

## CONTEXT BOUNDARIES:

- Available context: All results from steps 2-3, fix details if applicable
- Focus: Clear, actionable final report
- Limits: Report only, no additional execution
- Dependencies: Execution results and fix context from previous steps

## REPORT SEQUENCE:

### 1. Compile Final Results

Gather from context:
- Original test results from step 2
- Fix attempts and outcomes from step 3 (if applicable)
- Commit information (if fixes were made)

### 2. Generate Report

Output to stdout:
```
[step-04] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-04]
[step-04] TEST REPORT
[step-04]
```

### 3. Log Results Table

Output to stdout:
```
[step-04] Command Results:
[step-04]   | Command | Initial | Final | Fixed |
[step-04]   |---------|---------|-------|-------|
[step-04]   | unit | ✅/❌ | ✅/❌ | Yes/No |
[step-04]   | e2e | ✅/❌ | ✅/❌ | Yes/No |
[step-04]   | lint | ✅/❌ | ✅/❌ | Yes/No |
[step-04]   | typecheck | ✅/❌ | ✅/❌ | Yes/No |
```

### 4. Log Fix Summary (if applicable)

If fixes were attempted, output to stdout:
```
[step-04] Fixes Applied:
[step-04]   [X] files changed, [Y] fixes committed
```

### 5. Log Final Status

#### IF all passed (including after fixes):

Output to stdout:
```
[step-04]
[step-04] ✅ ALL TESTS PASSED
[step-04]
[step-04] Summary:
[step-04]   Commands run: [X]
[step-04]   Initially passed: [Y]
[step-04]   Fixed: [Z]
[step-04]   Final status: ALL PASS
[step-04]
[step-04] Exit Code: 0
[step-04] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### IF some still failing:

Output to stdout:
```
[step-04]
[step-04] ❌ SOME TESTS FAILED
[step-04]
[step-04] Summary:
[step-04]   Commands run: [X]
[step-04]   Passed: [Y]
[step-04]   Fixed: [Z]
[step-04]   Still failing: [W]
[step-04]
[step-04] Remaining Failures:
[step-04]   - [command]: [brief error summary]
[step-04]
[step-04] Exit Code: 1
[step-04] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6. End Workflow

This is the final step. Workflow ends here.

**Exit Status:**
- Exit 0 if all tests pass
- Exit 1 if any tests still failing

---

## CRITICAL STEP COMPLETION NOTE

Workflow completes after this step. No further steps to load.

Return appropriate exit status based on final test results:
- Exit 0 if all tests pass (including after fixes)
- Exit 1 if any tests still failing after fix attempts

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Clear report generated
- All results summarized
- Fixes documented
- Appropriate exit status
- Actionable next steps provided

### ❌ SYSTEM FAILURE:

- Unclear or incomplete report
- Not showing fix details
- Not providing next steps
- Wrong exit status

**Master Rule:** Execute all actions completely, track all results, and proceed to the correct next step. Generate a clear, actionable report that tells the user exactly what happened and what to do next.
