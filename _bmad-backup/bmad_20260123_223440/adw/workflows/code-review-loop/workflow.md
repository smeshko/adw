---
name: code-review-loop
description: Autonomous code review loop for CI pipelines. Runs Codex adversarial review, validates findings, fixes valid issues, and commits. Repeats up to 2 cycles until clean.
web_bundle: true

# Input Parameters
# Context is provided externally - no parameters required
# The workflow expects full context (diff, files to review) to be provided in the prompt
#
# Exit Codes:
# - 0: Clean (no issues found or all resolved)
# - 1: Issues remain after max cycles
---

<!-- AUTONOMOUS CI WORKFLOW
This workflow is designed for CI pipeline integration:
- Fully autonomous execution (no user input)
- Context provided externally (git diff, files, etc.)
- Codex-only review (no GLM)
- Commits fixes after each cycle
- Returns exit code for CI integration
-->

# Code Review Loop (CI)

**Goal:** Automate adversarial code review in CI pipelines. Run Codex review on provided context, validate JSON findings, fix valid issues, commit, and repeat until clean or max 2 cycles reached.

**Your Role:** You are a senior developer and code quality guardian. You orchestrate the review process by running Codex in report-only mode, validating findings against the provided context, and fixing genuine issues yourself. Work autonomously to deliver clean, reviewed code.

---

## WORKFLOW ARCHITECTURE

This uses **step-file architecture** for disciplined execution:

### Core Principles

- **Micro-file Design**: Each step is a self-contained instruction file
- **Just-In-Time Loading**: Only the current step file is in memory
- **Sequential Enforcement**: Execute steps in order, no skipping
- **Autonomous Execution**: This workflow runs without user interaction
- **Append-Only Building**: Build review state incrementally across cycles

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order
3. **AUTO-PROCEED**: This is an autonomous workflow - proceed automatically between steps
4. **TRACK STATE**: Maintain cycle count and issue tracking in memory

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 💾 **ALWAYS** commit after each fix cycle
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📋 **NEVER** create mental todo lists from future steps

---

## INITIALIZATION SEQUENCE

### 1. First Step Execution

Load, read the full file, and execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
