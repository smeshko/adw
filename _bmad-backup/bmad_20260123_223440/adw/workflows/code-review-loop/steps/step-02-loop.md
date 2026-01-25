---
name: 'step-02-loop'
description: 'Execute the review-validate-fix-commit cycle up to 2 times using Codex'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/code-review-loop'

# File References
thisStepFile: '{workflow_path}/steps/step-02-loop.md'
nextStepFile: '{workflow_path}/steps/step-03-finalize.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 2: Review Loop

## STEP GOAL:

To execute the review-validate-fix-commit cycle. Run Codex for adversarial review, validate findings against provided context, fix valid issues, commit, and repeat until clean or max 2 cycles reached.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: This step contains an internal loop - follow loop logic exactly
- 🤖 This is an AUTONOMOUS workflow - proceed without user interaction

### Role Reinforcement:

- ✅ You are the VALIDATOR and FIXER - Codex is the REVIEWER
- ✅ Codex finds issues, YOU decide if they're real
- ✅ Only fix issues that are genuinely problematic
- ✅ Dismiss false positives with clear reasoning

### Step-Specific Rules:

- 🎯 Focus on one cycle at a time
- 🚫 FORBIDDEN to fix issues without validating them first
- 💾 Commit after EVERY cycle that has fixes
- 🔄 Loop back to start of this step until exit condition met

## EXECUTION PROTOCOLS:

- 🎯 Run Codex in report-only mode
- 💾 Track all issues (fixed and skipped)
- 📖 Commit with descriptive message after each fix cycle
- 🚫 FORBIDDEN to exceed 2 cycles
- 🚫 FORBIDDEN to specify a model with `-m` flag - always use Codex's configured default

## CONTEXT FROM STEP 1:

Available in memory from initialization:
- `cycle_count` - current cycle number
- `max_cycles` - maximum cycles (2)
- `issues_fixed` - array of fixed issues
- `issues_skipped` - array of skipped issues
- `files_to_review` - list of files from provided context
- `diff_content` - the code changes to review
- `requirements` - any provided requirements

---

## REVIEW LOOP SEQUENCE:

### 1. Increment Cycle Counter

```
cycle_count = cycle_count + 1
```

Display:
```
───────────────────────────────────────────────────────────────
  CYCLE {cycle_count} of {max_cycles}
───────────────────────────────────────────────────────────────
```

### 2. Build the Review Prompt

Construct the review prompt with exact output format specification.

**Prompt structure:**
```
You are an adversarial code reviewer. Analyze the code changes and find issues.

## Files to Review
{files_to_review from provided context}

## Code Changes
{diff_content from provided context}

{If requirements provided:}
## Requirements
{requirements}

## Your Task
Find code quality issues: bugs, security vulnerabilities, logic errors, missing error handling,
violations of project patterns, incomplete implementations, and test gaps.

## REQUIRED OUTPUT FORMAT (strict JSON)

Return your findings as a JSON array. Each finding MUST follow this exact structure:

```json
{
  "findings": [
    {
      "severity": "HIGH|MEDIUM|LOW",
      "file": "path/to/file.ext",
      "line": 42,
      "issue": "Clear description of the problem",
      "suggested_fix": "Specific fix recommendation",
      "category": "bug|security|logic|error-handling|pattern|incomplete|test"
    }
  ],
  "summary": {
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0,
    "files_reviewed": 5
  }
}
```

If no issues found, return:
```json
{
  "findings": [],
  "summary": {
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0,
    "files_reviewed": 5
  }
}
```

IMPORTANT: Output ONLY the JSON. No markdown, no explanation, no preamble.
```

**If `cycle_count > 1` AND `issues_skipped` is not empty, append exclusion context:**
```

## EXCLUDED ISSUES (Already Dismissed as False Positives)
DO NOT report these issues - they were validated and dismissed in previous cycles:

{For each item in issues_skipped:}
- File: {file}, Line: {line}
  Issue: {issue}
  Reason Dismissed: {reason}

Focus only on NEW issues not listed above.
```

### 3. Run Codex Review

Display: "Running Codex review..."

Execute via Codex:
```bash
codex exec --full-auto \
  -c 'headless=true' \
  -c 'auto_fix_mode="report-only"' \
  "{constructed_prompt}"
```

**Timeout:** 10 minutes (600000ms).

**IMPORTANT:** Do NOT use the `-m` flag. Always use Codex's configured default model.

**If Codex fails:**
- Set `exit_reason = "review_failed"`
- Set `exit_code = 1`
- Proceed to step 3 (finalize)

### 4. Parse Review Findings

Parse the JSON response from Codex.

**Expected JSON structure:**
```json
{
  "findings": [
    {
      "severity": "HIGH|MEDIUM|LOW",
      "file": "path/to/file.ext",
      "line": 42,
      "issue": "Description of the problem",
      "suggested_fix": "How to fix it",
      "category": "bug|security|logic|error-handling|pattern|incomplete|test"
    }
  ],
  "summary": {
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0,
    "files_reviewed": 5
  }
}
```

**Parsing logic:**

1. Extract JSON from the Codex response (may be wrapped in markdown code blocks)
2. Parse into structured `findings` array

**If `findings` array is empty:**
- Set `exit_reason = "clean"`
- Set `exit_code = 0`
- Display: "✅ No issues found - code is clean"
- Proceed to step 3 (finalize)

**Display findings summary:**
```
  Review findings: {total_count} issues
    HIGH: {high_count}
    MEDIUM: {medium_count}
    LOW: {low_count}
```

### 5. Validate Each Finding

For EACH finding from Codex:

#### 5a. Read the Relevant Code

Read the file and surrounding context (10 lines before/after the reported line).

#### 5b. Check Against Provided Context

Ask yourself:
- Does this issue actually exist in the code?
- Is the code actually problematic, or is Codex misunderstanding?
- Does the suggested fix make sense?

#### 5c. Check Against Requirements (if provided)

If requirements were provided, ask yourself:
- Is this relevant to the stated requirements?
- Does fixing this align with the goals?

#### 5d. Classify the Finding

**VALID** if:
- The issue genuinely exists in the code
- Fixing it improves code quality, security, or correctness

**FALSE_POSITIVE** if:
- The code is actually correct
- Codex misunderstood the pattern or intent
- The "fix" would break other functionality

### 6. Process Validated Findings

#### 6a. For VALID Issues

For each VALID issue:
1. Fix the issue in the code
2. Add to tracking:
   ```
   issues_fixed.append({
     cycle: cycle_count,
     severity: "HIGH|MEDIUM|LOW",
     file: "path/to/file",
     line: 42,
     issue: "Brief description",
     fix: "What was changed",
     category: "bug|security|logic|..."
   })
   ```

#### 6b. For FALSE_POSITIVE Issues

For each FALSE_POSITIVE:
1. Do NOT modify any code
2. Add to tracking with FULL context (so Codex won't report it again):
   ```
   issues_skipped.append({
     cycle: cycle_count,
     severity: "HIGH|MEDIUM|LOW",
     file: "path/to/file",
     line: 42,
     issue: "Full issue description from Codex",
     suggested_fix: "The fix suggested",
     category: "bug|security|logic|...",
     reason: "Why this was dismissed"
   })
   ```

### 7. Commit Fixes (If Any)

If any issues were fixed in this cycle:

```bash
git add -A
git commit -m "fix(review): cycle {cycle_count} - {summary of fixes}"
```

The commit message should briefly describe what was fixed.

If NO issues were fixed (all were false positives):
- Set `exit_reason = "all_false_positives"`
- Set `exit_code = 0`
- Proceed to step 3 (finalize)

### 8. Check Exit Conditions

**EXIT to step 3 if:**
- `exit_reason == "clean"` (Codex found no issues)
- `exit_reason == "all_false_positives"` (all findings were dismissed)
- `cycle_count >= max_cycles` (reached 2 cycles)

**LOOP back to action 1 if:**
- Valid issues were fixed AND cycle_count < max_cycles
- There may be more issues to find

### 9. Loop or Exit

**If EXIT condition met:**
- If `cycle_count >= max_cycles` and issues remain:
  - Set `exit_reason = "max_cycles_reached"`
  - Set `exit_code = 1`
- Load and execute `{workflow_path}/steps/step-03-finalize.md`

**If LOOP condition met:**
- Display: "Fixes committed. Running next review cycle..."
- Go back to action 1 (Increment Cycle Counter)

---

## CYCLE SUMMARY DISPLAY

After each cycle, display:

```
  Cycle {N} Complete:
    - Review findings: {total}
    - Valid issues fixed: {fixed_count}
    - False positives skipped: {skipped_count}

  {Next action: "Looping for cycle N+1" OR "Proceeding to finalize"}
───────────────────────────────────────────────────────────────
```

---

## CRITICAL STEP COMPLETION NOTE

This step contains an internal loop. Only proceed to step-03-finalize.md when an exit condition is met:
- Codex found no issues (clean)
- All findings were false positives
- Max 2 cycles reached

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Codex review executed successfully
- JSON response parsed correctly into findings structure
- Each finding validated before action
- Valid issues fixed, false positives dismissed
- Commits made after each fix cycle
- Exit condition properly detected
- Proceeded to step 3 when appropriate

### ❌ SYSTEM FAILURE:

- Failing to parse JSON response from Codex
- Fixing issues without validation
- Not committing after fixes
- Exceeding 2 cycles
- Stopping to ask user questions
- Not tracking fixed/skipped issues

**Master Rule:** This is an AUTONOMOUS workflow. Do not stop for user input. Validate findings yourself using provided context.
