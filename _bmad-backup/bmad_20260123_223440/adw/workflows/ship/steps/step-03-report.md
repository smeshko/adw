---
name: 'step-03-report'
description: 'Generate final deployment report with summary and next steps'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/ship'

# File References
thisStepFile: '{workflow_path}/steps/step-03-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 3: Deployment Report

## STEP GOAL:

To generate a comprehensive final report summarizing the deployment outcome, including version deployed, destination, timing, and actionable next steps.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: This is the final step - no next step to load
- 📊 COMPILE RESULTS: Generate comprehensive report from execution context
- 🔢 EXIT CODE: Return appropriate exit code based on results

### Role Reinforcement:

- ✅ You are a release reporter outputting deployment results
- ✅ Work autonomously - this is the final step
- ✅ Log comprehensive report to stdout for CI visibility
- ✅ Return appropriate exit code

### Step-Specific Rules:

- 🎯 Generate comprehensive deployment summary
- 🚫 FORBIDDEN to skip any report sections
- 📊 Output all results to stdout
- 🔢 Return appropriate exit code

## EXECUTION PROTOCOLS:

- 🎯 Compile all deployment results from context
- 💾 Generate formatted report with all sections
- 📖 Provide appropriate next steps based on outcome
- 🚫 FORBIDDEN to end without clear status indication

## CONTEXT BOUNDARIES:

- Available context: Deployment results from Step 2 (success/failure, version, timing, outputs)
- Focus: Clear, comprehensive reporting
- Limits: Report only - no additional commands to execute
- Dependencies: Successful completion of Step 2 execution

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Compile Final Results

Gather from context:
- Deployment type (npm/docker/github-release/custom)
- Commands executed and their status
- Success/failure status
- Version (if bumped)
- Duration (startTime to now)
- Any error messages

### 2. Generate Report

Output to stdout:
```
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-03]
[step-03] DEPLOYMENT REPORT
[step-03]
```

### 3. Log Deployment Summary

Output to stdout:
```
[step-03] Deployment Details:
[step-03]   Type: [npm/docker/github-release/custom]
[step-03]   Version: [version or N/A]
[step-03]   Duration: [time elapsed]
[step-03]   Status: ✅ Success / ❌ Failed / ⚠️ Partial
```

### 4. Log Step Results

Output to stdout:
```
[step-03] Execution Steps:
[step-03]   Pre-Checks: ✅ [count] passed
[step-03]   Version Bump: ✅/❌/⏭️ [version or 'skipped' or error]
[step-03]   Build: ✅/❌/⏭️ [status or 'skipped']
[step-03]   Publish: ✅/❌ [destination]
[step-03]   Post-Publish: ✅/❌/⏭️ [count] commands or 'skipped'
```

### 5. Log Final Status

#### IF deployment succeeded:

**Update Linear Issue to Done (if configured):**

1. Check if .linear config exists at {project-root}/.linear
2. Check if there's a story context with Linear issue ID (from sprint artifacts or environment)
3. If Linear is configured and issue ID available:
   - Get team states: `python ~/.claude/skills/linear/scripts/get_teams.py --detailed --json`
   - Find "Done" or "Completed" state ID from the workflow states
   - Update issue: `python ~/.claude/skills/linear/scripts/update_issue.py {linear_issue_id} --state-id {done_state_id}`
   - Log: `[step-03] 🔗 Linear Issue Updated: {linear_issue_id} → Done`

Output to stdout:
```
[step-03]
[step-03] ✅ DEPLOYMENT SUCCESSFUL
[step-03]
[step-03] Version [version] has been deployed successfully!
[step-03] Destination: [where it was published]
[step-03] Duration: [time elapsed]
[step-03] Linear: [issue_id] → Done (if configured)
[step-03]
[step-03] Exit Code: 0
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### IF deployment failed:

Output to stdout:
```
[step-03]
[step-03] ❌ DEPLOYMENT FAILED
[step-03]
[step-03] Failed at: [step name]
[step-03] Error: [brief error summary]
[step-03]
[step-03] Completed: [list of completed steps]
[step-03]
[step-03] Exit Code: 1
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### IF partial success (post-publish failed):

Output to stdout:
```
[step-03]
[step-03] ⚠️ DEPLOYMENT PARTIALLY SUCCESSFUL
[step-03]
[step-03] Version [version] was published, but post-publish steps failed.
[step-03] Published: ✅
[step-03] Post-Publish: ❌
[step-03]
[step-03] Exit Code: 2
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6. End Workflow

This is the final step. Workflow ends here.

**Exit Status:**
- Exit 0 if deployment successful
- Exit 1 if deployment failed
- Exit 2 if partial success (published but post-publish failed)

## CRITICAL STEP COMPLETION NOTE

This is the final step in the workflow. After displaying the report, the workflow is complete. No further steps to load.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Clear, comprehensive report generated
- Version and destination prominently shown
- All executed steps summarized with status
- Appropriate next steps provided based on outcome
- Workflow ended gracefully

### ❌ SYSTEM FAILURE:

- Incomplete report missing sections
- Missing version or destination information
- No next steps provided
- Unclear final status
- Abrupt ending without summary

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
