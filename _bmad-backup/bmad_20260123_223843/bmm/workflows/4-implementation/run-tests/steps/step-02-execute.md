---
name: 'step-02-execute'
description: 'Execute all configured test commands and collect results'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-02-execute.md'
fixStepFile: '{workflow_path}/steps/step-03-fix.md'
reportStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 2: Execute Test Commands

## STEP GOAL:

To execute all configured test commands, collect results, and route to fix step if failures occur.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
- 🔄 Run ALL commands - do not fail fast

### Role Reinforcement:

- ✅ You are a test runner
- ✅ Execute every enabled command
- ✅ Collect all output for analysis

### Step-Specific Rules:

- 🎯 Execute ALL enabled commands regardless of failures
- 🚫 FORBIDDEN to stop on first failure
- ✅ Capture stdout and stderr for each command
- ✅ Track pass/fail status for each command

## EXECUTION PROTOCOLS:

- 🎯 Execute ALL enabled commands regardless of individual failures
- 💾 Track pass/fail/timing for each command
- 📖 Capture stdout and stderr for failed commands
- 🚫 FORBIDDEN to stop on first failure (run all)

## CONTEXT BOUNDARIES:

- Available context: Enabled commands and config from step 1
- Focus: Command execution and result collection
- Limits: Execute only, no fixing in this step
- Dependencies: Valid test configuration from step 1

## EXECUTION SEQUENCE:

### 1. Initialize Results Tracking

Create results object:
```
results = {
  passed: [],
  failed: [],
  skipped: [],
  totalTime: 0
}
```

### 2. Execute Commands in Order

Run commands in this order (if enabled):

#### A. Pre-Commands
For each command in `pre_commands`:
- Execute command
- Record result (pass/fail)
- Capture output
- Continue regardless of result

#### B. Unit Tests
If `unit.enabled`:
- Execute `unit.command`
- Record result
- Capture output

#### C. E2E Tests
If `e2e.enabled`:
- Execute `e2e.command`
- Record result
- Capture output

#### D. Lint
If `lint.enabled`:
- Execute `lint.command`
- Record result
- Capture output

#### E. Type Check
If `typecheck.enabled`:
- Execute `typecheck.command`
- Record result
- Capture output

#### F. Custom Commands
For each command in `custom`:
- Execute command
- Record result
- Capture output

### 3. Log Execution Progress

For each command, output to stdout:
```
[step-02] Running: [command name]...
[step-02]   [command output - abbreviated if long]
[step-02]   Result: ✅ PASS / ❌ FAIL
```

### 4. Log Results Summary

After all commands complete, output to stdout:
```
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-02] Execution Complete
[step-02]   Passed: [X]
[step-02]   Failed: [Y]
[step-02]   Skipped: [Z]
[step-02]   Total Time: [duration]
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5. Route Based on Results

#### IF all passed:
Output: `[step-02] ✓ All tests passed - proceeding to report`
Load, read entire file, then execute `{reportStepFile}`

#### IF any failed:
Output: `[step-02] ⚠ Some tests failed - attempting automatic fixes`
Store failed commands and their error output in context
Load, read entire file, then execute `{fixStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [all enabled commands have been executed and results collected], will you then:
- Route to `{reportStepFile}` if all tests passed
- Route to `{fixStepFile}` if any tests failed

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All enabled commands executed
- Results properly tracked
- Output captured for failed commands
- Correct routing to next step

### ❌ SYSTEM FAILURE:

- Stopping on first failure
- Not capturing error output
- Not tracking all results
- Wrong routing based on results

**Master Rule:** Execute all actions completely, track all results, and proceed to the correct next step. Run ALL commands and collect ALL results before proceeding.
