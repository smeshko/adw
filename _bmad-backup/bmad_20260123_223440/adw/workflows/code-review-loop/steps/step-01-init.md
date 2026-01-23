---
name: 'step-01-init'
description: 'Initialize code review loop by parsing provided context and preparing tracking state'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/code-review-loop'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-loop.md'
workflowFile: '{workflow_path}/workflow.md'

# Input
# Full context (git diff, files to review, any requirements) is provided externally
# in the workflow invocation prompt
---

# Step 1: Initialize Code Review Loop

## STEP GOAL:

To parse the provided context and initialize tracking state for the review cycles. Context (diff, files, requirements) is provided externally - no loading required.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step, ensure entire file is read
- 🤖 This is an AUTONOMOUS workflow - proceed without user interaction

### Role Reinforcement:

- ✅ You are a senior developer and code quality guardian
- ✅ You orchestrate review by running Codex, then validating and fixing
- ✅ Work autonomously to deliver clean, reviewed code

### Step-Specific Rules:

- 🎯 Focus ONLY on parsing context and initializing state
- 🚫 FORBIDDEN to start any review or fixes in this step
- 📋 Context is provided externally - do not attempt to load files

## EXECUTION PROTOCOLS:

- 🎯 Parse provided context
- 💾 Initialize tracking state in memory
- 📖 Auto-proceed to step 2 after initialization
- 🚫 FORBIDDEN to skip any initialization tasks

## INITIALIZATION SEQUENCE:

### 1. Parse Provided Context

The workflow is invoked with full context provided in the prompt. This includes:

- **Files to review**: List of file paths that have changes
- **Diff content**: The actual code changes to review
- **Requirements** (optional): Any specific requirements or acceptance criteria

Extract and store:
- `files_to_review` - list of files from the provided context
- `diff_content` - the code changes to review
- `requirements` - any provided requirements (may be empty)

### 2. Initialize Tracking State

Initialize in-memory state:

```
cycle_count = 0
max_cycles = 2
issues_fixed = []
issues_skipped = []
exit_reason = null
exit_code = 0
```

### 3. Display Initialization Summary

Print to terminal:

```
═══════════════════════════════════════════════════════════════
  CODE REVIEW LOOP (CI) - Initialized
═══════════════════════════════════════════════════════════════
  Files to Review: {file_count} files
  Max Cycles: 2

  Starting review loop...
═══════════════════════════════════════════════════════════════
```

### 4. Auto-Proceed to Review Loop

After initialization complete, immediately load and execute `{workflow_path}/steps/step-02-loop.md`.

## CRITICAL STEP COMPLETION NOTE

This is an auto-proceed step. After all initialization tasks are complete, immediately load, read entire file, and execute step-02-loop.md to begin the review cycle.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Context parsed from provided input
- Tracking state initialized
- Auto-proceeded to step 2

### ❌ SYSTEM FAILURE:

- Attempting to load files or run git commands
- Stopping to ask user questions (this is autonomous)
- Not auto-proceeding to step 2

**Master Rule:** This is an AUTONOMOUS workflow. Do not stop for user input. Context is provided externally - do not attempt to load it.
