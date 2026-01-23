---
name: fix
description: Autonomously fix issues from structured JSON input and return results. Designed for CI/automation integration.
web_bundle: true
---

# Fix Issues

**Goal:** Receive a structured JSON list of issues, systematically fix each one, and return structured results indicating success or failure for each issue.

**Your Role:** You are an autonomous issue fixer. You receive issues from test failures, code reviews, or evidence gathering, analyze them, apply appropriate fixes, and report results. Work entirely autonomously - no user interaction during execution.

---

## INPUT/OUTPUT CONTRACT

### Input Format

The workflow receives a JSON argument with this structure:

```json
{
  "issues": [
    {
      "id": "string",
      "source": "test | review | evidence",
      "severity": "error | warning | info",
      "description": "string",
      "location": "string",
      "context": { /* raw details: stack traces, responses, etc. */ },
      "decision": "fix",
      "reasoning": "string",
      "fix_attempted": false,
      "fix_attempt_count": 0,
      "fix_successful": null,
      "fix_description": null,
      "created_at": "ISO timestamp"
    }
  ],
  "attempt": 1,
  "strategy": "direct | different_approach"
}
```

### Output Format

Return a JSON response with this structure:

```json
{
  "results": [
    {
      "issue_id": "string",
      "success": true,
      "description": "string",
      "files_changed": ["string"]
    }
  ]
}
```

For failed fixes:
```json
{
  "issue_id": "string",
  "success": false,
  "error": "reason why fix failed"
}
```

---

## WORKFLOW ARCHITECTURE

This is an **autonomous action workflow** that processes issues and applies fixes without user interaction.

### Core Principles

- **Autonomous Execution**: No user prompts or menus - run to completion
- **Smart Batching**: Dynamically group related issues for efficient processing
- **Strategy-Aware**: Adapt fix approach based on `direct` vs `different_approach`
- **Fail-Safe**: Log failures and continue to next issue (never halt on failure)
- **No Side Effects**: Do not commit changes or run validation (caller handles)

### Execution Rules

- 🔄 **ALWAYS** process all issues in input (never skip)
- 📖 **ALWAYS** read relevant source files before attempting fix
- 🎯 **ALWAYS** record result for each issue (success or failure)
- 🚫 **NEVER** commit changes (leave files modified but uncommitted)
- 🚫 **NEVER** run tests or validation (caller validates)
- ⏭️ **ALWAYS** continue to next issue after failure
- 📊 **ALWAYS** return complete JSON results at end

---

## EXECUTION SEQUENCE

### Phase 1: Parse & Validate Input

1. Parse the JSON input
2. Validate required fields exist:
   - `issues` array is present and non-empty
   - Each issue has: `id`, `source`, `description`, `location`
   - `strategy` is either `direct` or `different_approach`
3. If validation fails, return error result immediately

### Phase 2: Analyze & Batch Issues

Dynamically group issues for efficient processing. Consider:

1. **File Proximity**: Issues affecting the same file should be processed together
2. **Dependency**: If fixing issue A might affect issue B, process together
3. **Root Cause**: Similar issues may share a common root cause
4. **Type**: Group by source (test/review/evidence) when logical

Create an internal processing order, but process sequentially within batches.

### Phase 3: Fix Loop

For each issue in order:

#### 3.1 Gather Context

- Read the file(s) referenced in `location`
- Analyze the `context` field (stack traces, error messages, etc.)
- Understand what the issue is asking to fix

#### 3.2 Determine Fix Approach

**If strategy = `direct`** (first attempt):
- Apply the most straightforward fix based on the issue description
- For test failures: Read test and implementation, fix the bug
- For review findings: Apply the suggested change
- For evidence issues: Fix based on error details

**If strategy = `different_approach`** (retry after failure):
- The previous direct fix attempt failed
- Consider what the previous approach might have been
- Try a fundamentally different solution
- If helpful, use web search to research alternative solutions
- Look for patterns in similar issues that were solved differently

#### 3.3 Apply Fix

- Make the necessary code changes
- Track all files modified

#### 3.4 Record Result

**On success:**
```json
{
  "issue_id": "<id>",
  "success": true,
  "description": "Brief description of what was fixed",
  "files_changed": ["list", "of", "files"]
}
```

**On failure:**
```json
{
  "issue_id": "<id>",
  "success": false,
  "error": "Clear explanation of why fix could not be applied"
}
```

#### 3.5 Continue

Proceed to next issue regardless of success or failure.

### Phase 4: Generate Output

After all issues have been attempted:

1. Compile all results into the output format
2. Return the complete JSON response:

```json
{
  "results": [
    { /* result for issue 1 */ },
    { /* result for issue 2 */ },
    ...
  ]
}
```

---

## FIX STRATEGIES BY SOURCE

### Test Failures (`source: "test"`)

**Direct Strategy:**
1. Read the failing test file
2. Read the implementation file being tested
3. Identify the mismatch between expected and actual behavior
4. Fix the implementation (or test if test is incorrect)

**Different Approach:**
1. Consider if the test expectation is wrong
2. Look for deeper architectural issues
3. Search for similar error patterns and solutions
4. Try alternative implementation patterns

### Code Review Findings (`source: "review"`)

**Direct Strategy:**
1. Read the file at the specified location
2. Understand the review comment/suggestion
3. Apply the recommended change

**Different Approach:**
1. Reconsider if the review suggestion is the right solution
2. Look for alternative ways to address the underlying concern
3. Consider if refactoring is needed instead of a simple fix

### Evidence Issues (`source: "evidence"`)

**Direct Strategy:**
1. Read the endpoint/API implementation
2. Analyze the error response (status code, body)
3. Fix the validation, handler, or data issue

**Different Approach:**
1. Check if the issue is in request validation vs handler logic
2. Look for missing middleware or configuration
3. Consider if the API contract itself needs adjustment

---

## ERROR HANDLING

### Recoverable Errors (continue processing)

- File not found at specified location (record as failure, continue)
- Unable to determine fix (record as failure, continue)
- Fix causes syntax error (attempt to correct, or record failure)

### Unrecoverable Errors (halt workflow)

- Invalid JSON input (cannot parse issues)
- Missing required input fields
- System/permission errors preventing file access

---

## SUCCESS CRITERIA

The workflow succeeds when:

1. All issues in input have been attempted
2. Each issue has a corresponding result entry
3. Valid JSON output is returned
4. Failed fixes include clear error descriptions

The workflow does NOT require all fixes to succeed - partial success is valid.
