---
name: 'step-04-report'
description: 'Output final structured JSON report to stdout'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 4: Output JSON Report

## STEP GOAL:

To output the final structured JSON report to stdout with all issues, their statuses, and summary information.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is the final step - output JSON only

### Role Reinforcement:

- ✅ You are a JSON reporter
- ✅ Output structured data for downstream agents
- ✅ Provide appropriate exit status

### Step-Specific Rules:

- 🎯 Output ONLY valid JSON to stdout
- 🚫 FORBIDDEN to output any text, tables, or formatting
- ✅ Include all issues with their final status
- ✅ Include summary with counts
- ✅ End with appropriate exit status

## EXECUTION PROTOCOLS:

- 🎯 Compile final JSON from context
- 💾 Output JSON to stdout (and ONLY JSON)
- 📖 Return appropriate exit code
- 🚫 FORBIDDEN to output any non-JSON content

## CONTEXT BOUNDARIES:

- Available context: Issues array (with fix_status), summary from step 3
- Focus: Clean JSON output for agent consumption
- Limits: Report only, no additional execution
- Dependencies: Final issue states and summary from previous steps

## REPORT SEQUENCE:

### 1. Compile Final JSON

Build the output object from context:

```json
{
  "status": context.status,  // "passed" | "failed"
  "summary": {
    "total": context.summary.total,
    "errors": context.summary.errors,
    "warnings": context.summary.warnings,
    "fixed": context.summary.fixed
  },
  "issues": [
    // For each issue in context.issues, include:
    {
      "id": issue.id,
      "severity": issue.severity,
      "type": issue.type,
      "command": issue.command,
      "description": issue.description,
      "location": issue.location,
      "context": issue.context,
      "fix_status": issue.fix_status,  // "fixed" | "unfixable"
      "fix_attempts": issue.fix_attempts,
      "fix_history": issue.fix_history  // array of attempt objects
    }
  ]
}
```

### 2. Handle Success Case (No Issues)

If workflow came directly from step 2 with no issues:

```json
{
  "status": "passed",
  "summary": {
    "total": 0,
    "errors": 0,
    "warnings": 0,
    "fixed": 0
  },
  "issues": []
}
```

### 3. Handle All Fixed Case

If all issues were fixed in step 3:

```json
{
  "status": "passed",
  "summary": {
    "total": N,
    "errors": 0,
    "warnings": 0,
    "fixed": N
  },
  "issues": [
    // All issues with fix_status: "fixed"
  ]
}
```

### 4. Handle Remaining Failures Case

If some issues remain unfixable:

```json
{
  "status": "failed",
  "summary": {
    "total": N,
    "errors": X,
    "warnings": Y,
    "fixed": Z
  },
  "issues": [
    // All issues - fixed ones and unfixable ones
  ]
}
```

### 5. Output JSON to Stdout

**CRITICAL**: Output ONLY the JSON object to stdout.

- No prefixes like `[step-04]`
- No markdown formatting
- No explanatory text
- Just the raw JSON object

```
Output the compiled JSON object to stdout
```

### 6. End Workflow

This is the final step. Workflow ends here.

**Exit Status:**
- Exit 0 if `status === "passed"` (all tests pass or all issues fixed)
- Exit 1 if `status === "failed"` (unfixable issues remain)

---

## CRITICAL STEP COMPLETION NOTE

Workflow completes after this step. No further steps to load.

Return appropriate exit status based on final `context.status`:
- Exit 0 if status is "passed"
- Exit 1 if status is "failed"

---

## OUTPUT EXAMPLES:

### Example: All Tests Passed

```json
{
  "status": "passed",
  "summary": {
    "total": 0,
    "errors": 0,
    "warnings": 0,
    "fixed": 0
  },
  "issues": []
}
```

### Example: Issues Fixed

```json
{
  "status": "passed",
  "summary": {
    "total": 2,
    "errors": 0,
    "warnings": 0,
    "fixed": 2
  },
  "issues": [
    {
      "id": "lint-001",
      "severity": "error",
      "type": "lint_error",
      "command": "lint",
      "description": "no-unused-vars: 'x' is defined but never used",
      "location": "src/utils.ts:15:7",
      "context": {
        "rule": "no-unused-vars",
        "fixable": true,
        "fix_hint": "Remove unused variable or use it"
      },
      "fix_status": "fixed",
      "fix_attempts": 1,
      "fix_history": [
        {
          "attempt": 1,
          "action": "Removed unused variable 'x'",
          "files_modified": ["src/utils.ts"]
        }
      ]
    },
    {
      "id": "type-001",
      "severity": "error",
      "type": "type_error",
      "command": "typecheck",
      "description": "TS2322: Type 'string' is not assignable to type 'number'",
      "location": "src/api.ts:42:5",
      "context": {
        "error_code": "TS2322",
        "fixable": true,
        "fix_hint": "Fix type mismatch"
      },
      "fix_status": "fixed",
      "fix_attempts": 1,
      "fix_history": [
        {
          "attempt": 1,
          "action": "Changed parameter type from number to string",
          "files_modified": ["src/api.ts"]
        }
      ]
    }
  ]
}
```

### Example: Unfixable Issues Remain

```json
{
  "status": "failed",
  "summary": {
    "total": 3,
    "errors": 2,
    "warnings": 1,
    "fixed": 1
  },
  "issues": [
    {
      "id": "test-001",
      "severity": "error",
      "type": "test_failure",
      "command": "unit",
      "description": "TypeError: Cannot read property 'id' of undefined",
      "location": "src/services/user.test.ts:45",
      "context": {
        "test_name": "UserService > should fetch user by ID",
        "stack_trace": "at Object.<anonymous> (src/services/user.test.ts:45:12)",
        "fixable": true,
        "fix_hint": "Check for null/undefined before accessing .id"
      },
      "fix_status": "unfixable",
      "fix_attempts": 3,
      "fix_history": [
        {
          "attempt": 1,
          "action": "Added null check before accessing user.id",
          "files_modified": ["src/services/user.ts"]
        },
        {
          "attempt": 2,
          "action": "Modified getUserById to return null instead of throwing",
          "files_modified": ["src/services/user.ts"]
        },
        {
          "attempt": 3,
          "action": "Updated test to handle null case",
          "files_modified": ["src/services/user.test.ts"]
        }
      ]
    },
    {
      "id": "lint-001",
      "severity": "warning",
      "type": "lint_error",
      "command": "lint",
      "description": "no-console: Unexpected console statement",
      "location": "src/debug.ts:10:3",
      "context": {
        "rule": "no-console",
        "fixable": false,
        "fix_hint": "Remove console.log or use proper logger"
      },
      "fix_status": "unfixable",
      "fix_attempts": 3,
      "fix_history": []
    },
    {
      "id": "type-001",
      "severity": "error",
      "type": "type_error",
      "command": "typecheck",
      "description": "TS2339: Property 'foo' does not exist on type 'Bar'",
      "location": "src/models.ts:28:10",
      "context": {
        "error_code": "TS2339",
        "fixable": true,
        "fix_hint": "Add 'foo' property to Bar interface"
      },
      "fix_status": "fixed",
      "fix_attempts": 1,
      "fix_history": [
        {
          "attempt": 1,
          "action": "Added 'foo' property to Bar interface",
          "files_modified": ["src/models.ts"]
        }
      ]
    }
  ]
}
```

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Valid JSON output to stdout
- All issues included with complete data
- Summary counts are accurate
- Appropriate exit status returned
- No text or formatting in output

### ❌ SYSTEM FAILURE:

- Outputting non-JSON content
- Missing issues or incomplete issue data
- Wrong exit status
- Adding text prefixes or formatting
- Invalid JSON syntax

**Master Rule:** Output ONLY valid JSON to stdout. No text, no formatting, no prefixes. Return correct exit code based on status.
