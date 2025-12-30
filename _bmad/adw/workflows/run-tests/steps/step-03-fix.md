---
name: 'step-03-fix'
description: 'Attempt to automatically fix issues with up to 3 attempts, tracking status per issue'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-03-fix.md'
reportStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'

# Constants
maxAttempts: 3
---

# Step 3: Auto-Fix Issues

## STEP GOAL:

To automatically analyze and fix issues from the issues array, re-run affected commands, update issue statuses, and repeat up to 3 times until all resolved or attempts exhausted.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - fix efficiently
- 🔄 Maximum 3 fix attempts total

### Role Reinforcement:

- ✅ You are a code fixer
- ✅ Analyze issues, apply fixes, verify fixes work
- ✅ Track fix status per issue

### Step-Specific Rules:

- 🎯 Work through issues systematically
- 🚫 FORBIDDEN to exceed 3 fix attempts
- ✅ Auto-apply fixes without asking
- ✅ Update issue status after each attempt
- ✅ Commit all successful fixes
- 🚫 NO stdout logging - only update issue data

## EXECUTION PROTOCOLS:

- 🎯 Analyze each issue and apply appropriate fix strategy
- 💾 Update issue objects with fix status and attempts
- 📖 Re-run only affected commands after fixes
- 🚫 FORBIDDEN to exceed 3 fix attempts
- 🚫 NO stdout logging - silent execution

## CONTEXT BOUNDARIES:

- Available context: Issues array from step 2
- Focus: Automatic issue analysis and code fixing
- Limits: Max 3 attempts, then proceed to report
- Dependencies: Structured issues from step 2 execution

## FIX LOOP SEQUENCE:

### 1. Initialize Fix Tracking

Extend each issue object with fix tracking:

```
For each issue in context.issues:
  issue.fix_status = "pending"  // pending | fixed | unfixable
  issue.fix_attempts = 0
  issue.fix_history = []
```

Initialize loop context:

```
fixContext = {
  attempt: 1,
  maxAttempts: 3,
  pendingIssues: context.issues.filter(i => i.fix_status === "pending"),
  fixedCount: 0,
  commitMessages: []
}
```

### 2. Fix Attempt Loop

While `attempt <= maxAttempts` AND `pendingIssues.length > 0`:

#### A. Analyze and Fix Each Pending Issue

For each issue with `fix_status === "pending"`:

**Lint Issues (`type: "lint_error"`):**
- If `context.fixable` is true, run lint command with `--fix` flag
- Otherwise, analyze the rule and apply manual fix
- Common fixes: formatting, import order, unused vars

**Type Issues (`type: "type_error"`):**
- Read the file at `issue.location`
- Analyze the TypeScript error
- Apply appropriate fix:
  - Missing types → add type annotations
  - Wrong types → correct the type
  - Missing imports → add imports
  - Null/undefined issues → add checks or assertions

**Test Issues (`type: "test_failure"`):**
- Read the test file and source file
- Analyze expected vs actual from `issue.description`
- Fix the source code (prefer fixing code over changing test)
- If test is clearly wrong, fix the test

**Build Issues (`type: "build_error"`):**
- Analyze `context.raw_output`
- Identify root cause
- Apply targeted fix

#### B. Record Fix Attempt

For each issue attempted:

```
issue.fix_attempts++
issue.fix_history.push({
  attempt: fixContext.attempt,
  action: "[description of fix applied]",
  files_modified: ["file1.ts", "file2.ts"]
})
```

#### C. Re-Run Affected Commands

After applying fixes:
- Identify which commands need re-running based on fixed issues
- Re-run only those commands
- Parse output for any remaining/new issues

#### D. Update Issue Statuses

For each issue:

```
if command now passes for this issue:
  issue.fix_status = "fixed"
  fixContext.fixedCount++
  fixContext.commitMessages.push(issue.fix_history.last.action)
else if issue.fix_attempts >= 3:
  issue.fix_status = "unfixable"
else:
  // remains "pending" for next attempt
```

#### E. Update Pending List

```
fixContext.pendingIssues = context.issues.filter(i => i.fix_status === "pending")
fixContext.attempt++
```

### 3. Commit Fixes

If any issues were fixed (`fixContext.fixedCount > 0`):

- Stage all modified files
- Create commit with message:

```
fix: auto-fix [N] issues

Fixed by run-tests workflow:
- [list of fix actions from commitMessages]
```

- Store commit hash in context: `context.fixCommitHash = [hash]`

### 4. Finalize Issue States

After loop completes, ensure all issues have final status:

```
For each issue in context.issues:
  if issue.fix_status === "pending":
    issue.fix_status = "unfixable"  // couldn't fix in 3 attempts
```

Calculate summary:

```
context.summary = {
  total: context.issues.length,
  errors: context.issues.filter(i => i.severity === "error").length,
  warnings: context.issues.filter(i => i.severity === "warning").length,
  fixed: context.issues.filter(i => i.fix_status === "fixed").length
}

context.status = context.issues.every(i => i.fix_status === "fixed")
  ? "passed"
  : "failed"
```

### 5. Proceed to Report

Store updated context and load, read entire file, then execute `{reportStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [fix loop completes (all fixed OR 3 attempts exhausted) and fixes committed], will you then load and read fully `{reportStepFile}` to execute and output final JSON.

---

## FIX STRATEGIES BY ISSUE TYPE:

### Lint Errors

1. Try `--fix` flag first (if `context.fixable`)
2. If no auto-fix, analyze rule and apply manual fix
3. Common fixes: formatting, import order, unused vars, missing semicolons

### Type Errors

1. Parse file:line from `issue.location`
2. Read the problematic code
3. Apply appropriate type fix based on error code:
   - TS2304: Cannot find name → add import
   - TS2322: Type mismatch → fix type or cast
   - TS2531: Object possibly null → add null check
   - TS7006: Parameter has implicit any → add type annotation

### Test Failures

1. Read test file at `issue.location`
2. Find the specific test from `context.test_name`
3. Analyze assertion error in `issue.description`
4. Trace to source code issue
5. Fix source code (prefer over changing test assertions)

### Build Errors

1. Parse error message from `context.raw_output`
2. Identify: missing dependencies, syntax errors, config issues
3. Apply targeted fix
4. May require package install, config change, or code fix

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Each issue analyzed with appropriate strategy
- Fixes applied automatically (no user prompts)
- Issue objects updated with fix_status and fix_history
- Commands re-run after fixes
- Loop respects max 3 attempts
- All fixes committed with descriptive message
- Summary calculated correctly

### ❌ SYSTEM FAILURE:

- Exceeding 3 fix attempts
- Not updating issue.fix_status
- Not committing fixes
- Asking for approval (should auto-apply)
- Not re-running after fixes
- Outputting text logs

**Master Rule:** Execute all actions completely, update all issue statuses, commit fixes, respect the 3-attempt limit, and proceed to report step.
