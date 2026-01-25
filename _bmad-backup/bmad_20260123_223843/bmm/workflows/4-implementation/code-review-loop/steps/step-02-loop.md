---
name: 'step-02-loop'
description: 'Execute the review-validate-fix-commit cycle up to 2 times'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/code-review-loop'

# File References
thisStepFile: '{workflow_path}/steps/step-02-loop.md'
nextStepFile: '{workflow_path}/steps/step-03-finalize.md'
workflowFile: '{workflow_path}/workflow.md'

# External Commands
codex_review_command: '/codex-review'

# Template References
# (none required for this step)

# Task References
# (none required for this step)
---

# Step 2: Review Loop

## STEP GOAL:

To execute the review-validate-fix-commit cycle. Spawn Codex for adversarial review, validate findings against codebase and story requirements, fix valid issues, commit, and repeat until clean or max 2 cycles reached.

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
- `review_mode` - "fast" (GLM), "thorough" (GLM+Codex), or "codex" (legacy)
- `issues_fixed` - array of fixed issues
- `issues_skipped` - array of skipped issues
- Story file content with acceptance criteria
- List of changed files
- Architecture context

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

### 2. Run Adversarial Review (Tiered by review_mode)

Execute review based on `review_mode` setting from step 1.

#### 2a. Build the Review Prompt

Construct the review prompt with exact output format specification.

**Base prompt structure:**
```
You are an adversarial code reviewer. Analyze the code changes on this branch and find issues.

## Files to Review
{List of changed_files from step 1}

## Story Context
{Story acceptance criteria and dev notes}

## Architecture Context
{Relevant architecture patterns}

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

#### 2b. Execute Review Based on Mode

---

##### MODE: "fast" (GLM-only via subagent, default)

Display: "⚡ Running GLM review in background..."

**Spawn GLM subagent in background:**

Use the Task tool with:
- `subagent_type`: "glm"
- `run_in_background`: true
- `description`: "GLM code review cycle {cycle_count}"
- `prompt`: The constructed review prompt from 2a

Example invocation pattern:
```
Task(
  subagent_type: "glm",
  run_in_background: true,
  description: "GLM code review cycle {cycle_count}",
  prompt: "{constructed_prompt with JSON output format}"
)
```

**While GLM runs:** You may continue with other lightweight checks or simply wait.

**Retrieve results:** Use `TaskOutput(task_id: {glm_task_id}, block: true, timeout: 300000)` to get results.

**Parse the JSON response** into the findings structure.

**If GLM fails (error, timeout, or API unavailable):**
- Display: "⚠️ GLM review failed, falling back to Codex..."
- Fall through to Codex execution below

---

##### MODE: "codex" (Codex-only, legacy)

Display: "🐌 Running Codex review..."

Execute via Codex:
```bash
codex exec --full-auto \
  -c 'headless=true' \
  -c 'auto_fix_mode="report-only"' \
  "{constructed_prompt}"
```

**Timeout:** 10 minutes (600000ms).

**IMPORTANT:** Do NOT use the `-m` flag. Always use Codex's configured default model.

---

##### MODE: "thorough" (GLM + Codex in parallel via subagents)

Display: "🔍 Running thorough review (GLM + Codex in parallel)..."

**Spawn BOTH reviewers as background subagents simultaneously:**

1. **Start GLM review (background subagent):**
   ```
   Task(
     subagent_type: "glm",
     run_in_background: true,
     description: "GLM review cycle {cycle_count}",
     prompt: "{constructed_prompt with JSON output format}"
   )
   ```
   Store the returned `task_id` as `glm_task_id`.

2. **Start Codex review (background):**
   ```bash
   codex exec --full-auto \
     -c 'headless=true' \
     -c 'auto_fix_mode="report-only"' \
     "{constructed_prompt}" &
   ```
   Run in background shell, capture process for later.

3. **Wait for both to complete:**
   - `TaskOutput(task_id: glm_task_id, block: true, timeout: 600000)`
   - Wait for Codex background process

4. **Merge findings:**
   - Parse JSON from GLM subagent response
   - Parse Codex output (may need flexible parsing)
   - Deduplicate by file+line+issue similarity
   - If both find same issue → mark `found_by: "both"` (higher confidence)
   - If only one finds issue → mark `found_by: "glm"` or `found_by: "codex"`

**If one reviewer fails:** Continue with the other's findings.
**If both fail:** Set `exit_reason = "review_failed"` and proceed to step 3.

---

Capture the output (merged if thorough mode). Parse JSON into findings array.

### 3. Parse Review Findings

Parse the JSON response from the reviewer(s).

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

1. Extract JSON from the subagent response (may be wrapped in markdown code blocks)
2. Parse into structured `findings` array
3. In thorough mode, add `found_by` field to each finding during merge

**If `findings` array is empty:**
- Set `exit_reason = "clean"`
- Display: "✅ No issues found - code is clean"
- Proceed to step 3 (finalize)

**Display findings summary:**
```
  Review findings: {total_count} issues
    HIGH: {high_count}
    MEDIUM: {medium_count}
    LOW: {low_count}
```

**In thorough mode, also display source breakdown:**
```
  Source breakdown:
    GLM only: {glm_only_count}
    Codex only: {codex_only_count}
    Both (high confidence): {both_count}
```

### 4. Validate Each Finding

For EACH finding from the reviewer(s):

#### 4a. Read the Relevant Code

Read the file and surrounding context (10 lines before/after the reported line).

#### 4b. Check Against Codebase

Ask yourself:
- Does this issue actually exist in the code?
- Is the code actually problematic, or is Codex misunderstanding?
- Does the code follow project patterns and architecture?

#### 4c. Check Against Story Requirements

Ask yourself:
- Is this relevant to the story's acceptance criteria?
- Does fixing this align with the story's goals?
- Is this within scope of the current work?

#### 4d. Classify the Finding

**VALID** if:
- The issue genuinely exists in the code
- Fixing it improves code quality, security, or correctness
- It's relevant to the current story
- **In thorough mode:** Issues found by BOTH reviewers have higher confidence

**FALSE_POSITIVE** if:
- The code is actually correct
- The reviewer misunderstood the pattern or intent
- The issue is out of scope for this story
- The "fix" would break other functionality

**Note:** In thorough mode, if GLM and Codex disagree, lean toward trusting:
- Issues found by BOTH (highest confidence)
- Issues that match project patterns/architecture (medium)
- Single-source findings that contradict project context (validate carefully)

### 5. Process Validated Findings

#### 5a. For VALID Issues

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
     category: "bug|security|logic|...",
     found_by: "glm|codex|both"  // only in thorough mode
   })
   ```

#### 5b. For FALSE_POSITIVE Issues

For each FALSE_POSITIVE:
1. Do NOT modify any code
2. Add to tracking with FULL context (so reviewer won't report it again):
   ```
   issues_skipped.append({
     cycle: cycle_count,
     severity: "HIGH|MEDIUM|LOW",
     file: "path/to/file",
     line: 42,
     issue: "Full issue description from reviewer",
     suggested_fix: "The fix suggested",
     category: "bug|security|logic|...",
     reason: "Why this was dismissed",
     found_by: "glm|codex|both"  // only in thorough mode
   })
   ```

### 6. Commit Fixes (If Any)

If any issues were fixed in this cycle:

```bash
git add -A
git commit -m "fix(review): cycle {cycle_count} - {summary of fixes}"
```

The commit message should briefly describe what was fixed.

If NO issues were fixed (all were false positives):
- Set `exit_reason = "all_false_positives"`
- Proceed to step 3 (finalize)

### 7. Check Exit Conditions

**EXIT to step 3 if:**
- `exit_reason == "clean"` (Codex found no issues)
- `exit_reason == "all_false_positives"` (all findings were dismissed)
- `cycle_count >= max_cycles` (reached 2 cycles)

**LOOP back to action 1 if:**
- Valid issues were fixed AND cycle_count < max_cycles
- There may be more issues to find

### 8. Loop or Exit

**If EXIT condition met:**
- If `cycle_count >= max_cycles`, set `exit_reason = "max_cycles_reached"`
- Load and execute `{workflow_path}/steps/step-03-finalize.md`

**If LOOP condition met:**
- Display: "Fixes committed. Running next review cycle..."
- Go back to action 1 (Increment Cycle Counter)

---

## CYCLE SUMMARY DISPLAY

After each cycle, display:

```
  Cycle {N} Complete ({review_mode} mode):
    - Review findings: {total} {if thorough: "(GLM: X, Codex: Y, Both: Z)"}
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

- GLM subagent spawned in background correctly (fast/thorough modes)
- TaskOutput used to retrieve subagent results with proper timeout
- JSON response parsed correctly into findings structure
- GLM fallback to Codex works when needed (fast mode)
- Parallel subagent execution works correctly (thorough mode)
- Findings properly merged and deduplicated (thorough mode)
- Each finding validated before action
- Valid issues fixed, false positives dismissed
- Commits made after each fix cycle
- Exit condition properly detected
- Proceeded to step 3 when appropriate

### ❌ SYSTEM FAILURE:

- Not using Task tool with run_in_background for GLM subagent
- Not using TaskOutput to retrieve subagent results
- Failing to parse JSON response from subagent
- Fixing issues without validation
- Not committing after fixes
- Exceeding 2 cycles
- Stopping to ask user questions
- Not tracking fixed/skipped issues
- Not falling back to Codex when GLM fails (fast mode)
- Not merging findings from both sources (thorough mode)

**Master Rule:** This is an AUTONOMOUS workflow. Do not stop for user input. Validate findings yourself using codebase and story context.
