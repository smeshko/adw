---
name: code-review-loop
description: Automated code review loop using GLM subagent in background. Default uses GLM subagent (fast, ~2-3 min/cycle). Use --thorough for GLM+Codex parallel (better coverage). Use --codex-only for legacy Codex mode. Returns structured JSON findings for validation.
web_bundle: true

# Input Parameters (all optional)
# story_id - Story ID to review (e.g., "3-1"). If provided and not on correct
#            branch, workflow will find and switch to matching worktree.
# --thorough - Run both GLM and Codex in parallel for maximum coverage
# --codex-only - Force Codex-only mode (legacy behavior)
#
# Review Mode (auto-selected based on flags):
# - "fast" (default): GLM subagent in background, ~2-3 min per cycle
# - "thorough": GLM subagent + Codex in parallel, ~10 min but better coverage
# - "codex": Codex-only (legacy), ~10 min per cycle
#
# Subagent Usage:
# - Fast mode: Spawns 'glm' subagent with run_in_background: true
# - Thorough mode: Spawns 'glm' subagent + Codex in parallel
# - Uses TaskOutput to retrieve results with 5-10 min timeout
# - Expects structured JSON output from subagent
---

<!-- AUTONOMOUS WORKFLOW PATTERN
This workflow intentionally deviates from the standard interactive template:
- Universal Rules: Modified for autonomous execution (no user input required)
- Role Reinforcement: Simplified (no partnership language - fully autonomous)
- Menu Patterns: Replaced with auto-proceed and exit conditions
- Critical Rules: Adapted for autonomous operation (no menu halts)
- Step Processing: Uses AUTO-PROCEED instead of WAIT FOR INPUT

These deviations are intentional and appropriate for this workflow type.
Standard BMAD workflows are interactive; this is an AUTONOMOUS variant.
-->

# Code Review Loop

**Goal:** Automate the code review and fix cycle using background subagents. Default "fast" mode spawns GLM subagent in background (~2-3 min/cycle). "Thorough" mode runs GLM subagent + Codex in parallel for maximum coverage. Validates JSON findings, fixes valid issues, and repeats until clean or max cycles reached.

**Your Role:** You are a senior developer and code quality guardian. You orchestrate the review process by spawning GLM subagent in background (Task tool with run_in_background: true), then retrieving structured JSON results via TaskOutput, validating findings, and fixing issues yourself. You ensure only real issues are addressed, avoiding hallucinated problems. Work autonomously to deliver clean, reviewed code.

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

<!-- AUTONOMOUS WORKFLOW: Standard rules adapted for autonomous operation:
- "halt at menus" → replaced by auto-proceed (no user interaction)
- "update frontmatter" → uses in-memory state tracking instead
- "wait for user input" → N/A for autonomous workflows
-->

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`, `sprint_artifacts`

### 2. First Step Execution

Load, read the full file, and execute `{project-root}/_bmad/bmm/workflows/4-implementation/code-review-loop/steps/step-01-init.md` to begin the workflow.
