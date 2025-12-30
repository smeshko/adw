# BMAD Action Step Template

This template provides the standard structure for **action workflow steps** - automated steps that execute without user intervention and auto-proceed to the next step.

<!-- TEMPLATE START -->

---

name: 'step-[N]-[short-name]'
description: '[Brief description of what this step accomplishes]'

# Path Definitions

workflow_path: '{project-root}/\_bmad/[module]/workflows/[workflow-name]'

# File References

thisStepFile: '{workflow_path}/steps/step-[N]-[short-name].md'
nextStepFile: '{workflow_path}/steps/step-[N+1]-[next-name].md' # Remove for final step
workflowFile: '{workflow_path}/workflow.md'

# Conditional Routing (if needed)

successStepFile: '{workflow_path}/steps/step-[X]-[success-step].md'
failureStepFile: '{workflow_path}/steps/step-[Y]-[failure-step].md'

# Config References (if needed)

projectConfigFile: '{project-root}/\_bmad/project-config.yaml'

# Constants (if needed)

maxAttempts: 3

---

# Step [N]: [Step Name]

## STEP GOAL:

[State the goal in context of the overall workflow goal. Be specific about what this step accomplishes.]

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
- 🔄 Auto-proceed to next step when complete

### Role Reinforcement:

- ✅ You are a [specific role, e.g., "test runner", "code fixer", "reporter"]
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

- 🎯 Focus ONLY on [specific task for this step]
- 🚫 FORBIDDEN to [what not to do in this step]
- ✅ [What to ensure in this step]
- ✅ [Additional requirement]

## EXECUTION PROTOCOLS:

- 🎯 [Step-specific protocol 1]
- 💾 [Step-specific protocol 2 - e.g., state tracking]
- 📖 [Step-specific protocol 3 - e.g., result capture]
- 🚫 [Step-specific restriction]

## CONTEXT BOUNDARIES:

- Available context: [what context is available from previous steps]
- Focus: [what this step should concentrate on]
- Limits: [what not to assume or do]
- Dependencies: [what this step depends on]

## EXECUTION SEQUENCE:

[Use "EXECUTION SEQUENCE" or step-appropriate name like "INITIALIZATION SEQUENCE", "FIX LOOP SEQUENCE", "REPORT SEQUENCE"]

### 1. [First Action Title]

[Specific instructions for first action]

### 2. [Second Action Title]

[Specific instructions for second action]

### N. [Final Action Title]

[Specific instructions for final action]

### N+1. Proceed to Next Step

[Choose ONE of these routing patterns:]

#### Linear Routing (most common):

Immediately load, read entire file, then execute `{nextStepFile}`.

#### Conditional Routing:

**IF [success condition]:**
Load, read entire file, then execute `{successStepFile}`

**IF [failure condition]:**
Load, read entire file, then execute `{failureStepFile}`

#### Final Step (no next step):

This is the final step. Workflow ends here.

**Exit Status:**

- Return success (0) if [success condition]
- Return failure (1) if [failure condition]

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [completion requirements are met], will you then load and read fully `{nextStepFile}` to execute [next step description].

[For conditional routing:]
Route to `{successStepFile}` if [condition], otherwise route to `{failureStepFile}`.

[For final step:]
Workflow completes after this step. No further steps to load.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- [Step-specific success criteria 1]
- [Step-specific success criteria 2]
- Results properly tracked for reporting
- Correct routing to next step
- [Additional success criteria]

### ❌ SYSTEM FAILURE:

- [Step-specific failure mode 1]
- [Step-specific failure mode 2]
- Not tracking results
- Wrong routing based on results
- [Additional failure modes]

**Master Rule:** Execute all actions completely, track all results, and proceed to the correct next step.

<!-- TEMPLATE END -->

## Step Type Patterns

### Initialization Step (step-01-init)

Purpose: Load configuration, validate prerequisites, prepare execution context.

Key elements:

- Load required configuration files
- Validate configuration exists and is valid
- Handle missing/invalid config gracefully (abort with clear message)
- Display execution plan
- Store context for subsequent steps
- Auto-proceed to execution step

### Execution Step (step-02-execute, etc.)

Purpose: Execute the main actions of the workflow.

Key elements:

- Initialize results tracking
- Execute all configured commands/actions
- Capture output (stdout, stderr, timing)
- Track pass/fail status for each action
- Display progress during execution
- Compile results summary
- Route based on results (conditional or linear)

### Fix/Recovery Step (step-03-fix)

Purpose: Attempt to automatically fix failures.

Key elements:

- Initialize fix tracking with attempt counter
- Implement fix loop with max attempts
- Analyze each failure type
- Apply appropriate fixes automatically
- Re-run failed actions after fixes
- Commit successful fixes
- Track what was fixed for reporting
- Always proceed to report step when done

### Report Step (step-0N-report - always final)

Purpose: Generate final summary and provide next steps.

Key elements:

- Compile all results from previous steps
- Generate comprehensive report
- Show what passed, failed, was fixed
- Display fix details if applicable
- Provide appropriate exit status
- Suggest next steps based on outcome

## Routing Patterns

### Linear Routing

```
step-01-init → step-02-execute → step-03-process → step-04-report
```

### Conditional Routing (Success/Failure Paths)

```
step-01-init → step-02-execute ─┬─[all pass]──→ step-04-report
                                └─[failures]──→ step-03-fix → step-04-report
```

### Loop-Back Routing

```
step-01-init → step-02-execute ─┬─[all pass]──→ step-04-report
                                └─[failures]──→ step-03-fix ─┬─[fixed]──→ step-04-report
                                                             └─[still failing, attempts < max]──→ step-03-fix (loop)
```

## Key Differences from Standard Step Template

| Aspect | Standard Step | Action Step |
|--------|---------------|-------------|
| Menu | Required (A/P/C) | None |
| User Input | Required before proceeding | Not needed |
| Progression | Wait for 'C' selection | Auto-proceed |
| Role | Facilitator | Executor |
| Content | User-directed generation | Autonomous execution |
| Section Name | "Sequence of Instructions" | "EXECUTION SEQUENCE" (or contextual) |
| Advanced Elicitation | Available | Not applicable |
| Party Mode | Available | Not applicable |

## Reference Examples

- **Init Step**: `_bmad/bmm/workflows/4-implementation/run-tests/steps/step-01-init.md`
- **Execute Step**: `_bmad/bmm/workflows/4-implementation/run-tests/steps/step-02-execute.md`
- **Fix Step**: `_bmad/bmm/workflows/4-implementation/run-tests/steps/step-03-fix.md`
- **Report Step**: `_bmad/bmm/workflows/4-implementation/run-tests/steps/step-04-report.md`
