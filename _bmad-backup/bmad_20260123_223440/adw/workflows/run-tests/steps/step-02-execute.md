---
name: 'step-02-execute'
description: 'Execute all configured test commands and collect structured issue data'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-02-execute.md'
fixStepFile: '{workflow_path}/steps/step-03-fix.md'
reportStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 2: Execute Test Commands

## STEP GOAL:

To execute all configured test commands, parse failures into structured issues, and route to fix step if issues exist.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
- 🔄 Run ALL commands - do not fail fast

### Role Reinforcement:

- ✅ You are a test runner
- ✅ Execute every enabled command
- ✅ Parse all errors into structured issues

### Step-Specific Rules:

- 🎯 Execute ALL enabled commands regardless of failures
- 🚫 FORBIDDEN to stop on first failure
- ✅ Capture stdout and stderr for each command
- ✅ Parse errors into structured issue objects
- 🚫 FORBIDDEN to output text logs - only build issue data

## EXECUTION PROTOCOLS:

- 🎯 Execute ALL enabled commands regardless of individual failures
- 💾 Parse failures into structured issues with IDs
- 📖 Extract location, description, context from error output
- 🚫 FORBIDDEN to stop on first failure (run all)
- 🚫 NO stdout logging - silent execution, build issues only

## CONTEXT BOUNDARIES:

- Available context: Enabled commands and config from step 1
- Focus: Command execution and structured issue collection
- Limits: Execute only, no fixing in this step
- Dependencies: Valid test configuration from step 1

## EXECUTION SEQUENCE:

### 1. Initialize Context

Create execution context object:

```
context = {
  issues: [],
  issueCounters: { test: 0, lint: 0, type: 0, build: 0 },
  commandResults: [],
  startTime: Date.now()
}
```

Issue ID generation helper:

```
generateIssueId(type):
  context.issueCounters[type]++
  return `${type}-${String(counter).padStart(3, '0')}`
  // e.g., "test-001", "lint-002", "type-003"
```

### 2. Execute Commands in Order

Run commands in this order (if enabled). For each command:
- Execute the command
- Capture stdout and stderr
- If failed, parse output into issues (see section 3)
- Record command result: { name, passed: bool, duration }

#### A. Pre-Commands

For each command in `pre_commands`:
- Execute command
- If failed, parse as build errors

#### B. Unit Tests

If `unit.enabled`:
- Execute `unit.command`
- If failed, parse as test failures

#### C. E2E Tests

If `e2e.enabled`:
- Execute `e2e.command`
- If failed, parse as test failures

#### D. Lint

If `lint.enabled`:
- Execute `lint.command`
- If failed, parse as lint errors (one issue per error/warning)

#### E. Type Check

If `typecheck.enabled`:
- Execute `typecheck.command`
- If failed, parse as type errors

#### F. Custom Commands

For each command in `custom`:
- Execute command
- If failed, parse as build errors

### 3. Parse Errors into Issues

For each failed command, analyze the output and create structured issues:

#### Test Failures (unit, e2e)

Parse test runner output (Jest, Vitest, Mocha, etc.):

```
{
  "id": generateIssueId("test"),
  "severity": "error",
  "type": "test_failure",
  "command": "unit" | "e2e",
  "description": "[Error message from assertion or exception]",
  "location": "[file path]:[line number]",
  "context": {
    "test_name": "[describe block] > [test name]",
    "stack_trace": "[relevant stack trace lines]",
    "fixable": true,
    "fix_hint": "[Analyze error to suggest fix approach]"
  }
}
```

Parsing hints:
- Look for "FAIL" or "✕" markers to find failed tests
- Extract test name from "it('...')" or "test('...')" context
- Parse file:line from stack trace (first non-node_modules line)
- Capture assertion error message as description

#### Lint Errors (eslint, biome, etc.)

Parse each lint error separately (create one issue per error):

```
{
  "id": generateIssueId("lint"),
  "severity": "error" | "warning",
  "type": "lint_error",
  "command": "lint",
  "description": "[rule]: [message]",
  "location": "[file]:[line]:[column]",
  "context": {
    "rule": "[eslint-rule-name]",
    "fixable": [true if --fix can resolve],
    "fix_hint": "[How to fix this lint error]"
  }
}
```

Parsing hints:
- ESLint format: `file:line:col: message (rule-name)`
- Biome format: Similar structured output
- Severity from error level (error vs warning)

#### Type Errors (TypeScript)

Parse TypeScript compiler errors:

```
{
  "id": generateIssueId("type"),
  "severity": "error",
  "type": "type_error",
  "command": "typecheck",
  "description": "[TS error code]: [message]",
  "location": "[file]:[line]:[column]",
  "context": {
    "error_code": "TS[XXXX]",
    "fixable": true,
    "fix_hint": "[Analyze type error to suggest fix]"
  }
}
```

Parsing hints:
- Format: `file(line,col): error TS[code]: message`
- Common fixes: add type annotation, fix type mismatch, add null check

#### Build/Other Errors

For pre_commands and custom commands:

```
{
  "id": generateIssueId("build"),
  "severity": "error",
  "type": "build_error",
  "command": "[command name]",
  "description": "[Error message]",
  "location": "[file:line if parseable, else 'unknown']",
  "context": {
    "raw_output": "[first 500 chars of error output]",
    "fixable": [true if error seems code-related],
    "fix_hint": "[Best guess at fix approach]"
  }
}
```

### 4. Store Results in Context

After all commands complete, store in context for next steps:

```
context.totalTime = Date.now() - context.startTime
context.hasFailures = context.issues.length > 0
```

### 5. Route Based on Results

#### IF no issues (all passed):

Store context and load, read entire file, then execute `{reportStepFile}`

#### IF issues exist (some failed):

Store context with all issues and load, read entire file, then execute `{fixStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [all enabled commands have been executed and issues parsed], will you then:
- Route to `{reportStepFile}` if no issues
- Route to `{fixStepFile}` if any issues exist

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All enabled commands executed
- All failures parsed into structured issues
- Issues have proper IDs, locations, and context
- Correct routing to next step

### ❌ SYSTEM FAILURE:

- Stopping on first failure
- Not parsing errors into issues
- Missing issue fields (id, location, context)
- Outputting text logs instead of building issues
- Wrong routing based on results

**Master Rule:** Execute all actions completely, parse all failures into structured issues, and proceed to the correct next step. Run ALL commands and collect ALL issues before proceeding.
