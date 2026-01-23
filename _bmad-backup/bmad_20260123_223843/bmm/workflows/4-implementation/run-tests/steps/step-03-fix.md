---
name: 'step-03-fix'
description: 'Attempt to automatically fix failing tests with up to 3 attempts'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-03-fix.md'
reportStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'

# Constants
maxAttempts: 3
---

# Step 3: Auto-Fix Failures

## STEP GOAL:

To automatically analyze and fix failing tests, re-run them, and repeat up to 3 times until all pass or attempts exhausted.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - fix efficiently
- 🔄 Maximum 3 fix attempts total

### Role Reinforcement:

- ✅ You are a code fixer
- ✅ Analyze errors, apply fixes, verify fixes work
- ✅ Be methodical and track what you've tried

### Step-Specific Rules:

- 🎯 Focus on fixing the specific failures
- 🚫 FORBIDDEN to exceed 3 fix attempts
- ✅ Auto-apply fixes without asking
- ✅ Commit all successful fixes
- ✅ Track what was fixed for reporting

## EXECUTION PROTOCOLS:

- 🎯 Analyze each failure and apply appropriate fix strategy
- 💾 Track all fixes applied for commit message
- 📖 Re-run only failed commands after fixes
- 🚫 FORBIDDEN to exceed 3 fix attempts

## CONTEXT BOUNDARIES:

- Available context: Failed commands and error output from step 2
- Focus: Automatic error analysis and code fixing
- Limits: Max 3 attempts, then proceed to report
- Dependencies: Failure details from step 2 execution

## FIX LOOP SEQUENCE:

### 1. Initialize Fix Tracking

```
fixContext = {
  attempt: 1,
  maxAttempts: 3,
  failedCommands: [from step 2],
  fixesApplied: [],
  stillFailing: []
}
```

### 2. Fix Attempt Loop

While `attempt <= maxAttempts` AND `failedCommands.length > 0`:

Output to stdout:
```
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-03] Fix Attempt [attempt]/[maxAttempts]
[step-03] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### A. Analyze Each Failure

For each failed command:

**Lint Failures:**
- Check if `--fix` flag is available
- Run lint with `--fix` flag
- If auto-fix available, apply it

**Type Errors:**
- Parse error messages for file:line:column
- Analyze the type error
- Apply appropriate fix:
  - Missing types → add type annotations
  - Wrong types → correct the type
  - Missing imports → add imports
  - Null/undefined issues → add checks or assertions

**Test Failures:**
- Parse test error output
- Identify failing test and assertion
- Analyze expected vs actual
- Fix the code causing the failure (not the test unless test is wrong)

**Build/Other Failures:**
- Parse error output
- Identify root cause
- Apply appropriate fix

#### B. Apply Fixes

For each identified fix:
- Make the code change
- Track what was changed: `{ file, change, reason }`

#### C. Re-Run Failed Commands

After applying fixes:
- Re-run only the commands that were failing
- Update pass/fail status

#### D. Update Context

```
if command now passes:
  remove from failedCommands
  add to fixesApplied
else:
  keep in failedCommands for next attempt

attempt++
```

#### E. Log Attempt Results

Output to stdout:
```
[step-03] Attempt [attempt] Results:
[step-03]   [command]: ✅ Fixed / ❌ Still failing
[step-03]   Fixed: [X], Still failing: [Y]
```

### 3. Commit Fixes

If any fixes were applied:

Output to stdout:
```
[step-03] Committing fixes...
```

- Stage all modified files
- Create commit with message:
  ```
  fix: auto-fix test/lint failures

  Fixed by test workflow:
  - [list of fixes applied]
  ```

Output to stdout:
```
[step-03] ✓ Committed [X] fixes in [commit hash]
```

### 4. Final Status Check

After loop completes (all pass OR 3 attempts exhausted):

#### IF all commands now pass:
```
fixContext.status = 'ALL_FIXED'
```
Output to stdout:
```
[step-03] ✓ All issues fixed successfully!
[step-03] ✓ Step 3 complete - proceeding to report
```

#### IF some still failing after 3 attempts:
```
fixContext.status = 'PARTIAL_FIX'
fixContext.stillFailing = [remaining failures]
```
Output to stdout:
```
[step-03] ⚠ Fixed [X] issues, [Y] still failing after 3 attempts
[step-03] ✓ Step 3 complete - proceeding to report
```

### 5. Store Fix Context and Proceed

Store fixContext for reporting step.

Load, read entire file, then execute `{reportStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [fix loop completes (all fixed OR 3 attempts exhausted) and fixes committed], will you then load and read fully `{reportStepFile}` to execute and begin final reporting phase.

---

## FIX STRATEGIES BY ERROR TYPE:

### Lint Errors (ESLint, etc.)
1. Try `--fix` flag first
2. If no auto-fix, analyze rule and apply manual fix
3. Common fixes: formatting, import order, unused vars

### Type Errors (TypeScript)
1. Parse file:line:column from error
2. Read the problematic code
3. Apply appropriate type fix
4. Common fixes: add types, fix type mismatches, add null checks

### Test Failures
1. Parse test name and assertion
2. Analyze expected vs actual values
3. Trace to source code issue
4. Fix source code (prefer fixing code over changing test)

### Build Errors
1. Parse error message
2. Identify missing dependencies, syntax errors, etc.
3. Apply targeted fix

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Each failure analyzed with appropriate strategy
- Fixes applied automatically
- Commands re-run after fixes
- Loop respects max 3 attempts
- All fixes committed
- Fix context passed to report step

### ❌ SYSTEM FAILURE:

- Exceeding 3 fix attempts
- Not committing fixes
- Not tracking what was fixed
- Asking for approval (should auto-apply)
- Not re-running after fixes

**Master Rule:** Execute all actions completely, track all results, and proceed to the correct next step. Fix automatically, commit fixes, respect the 3-attempt limit.
