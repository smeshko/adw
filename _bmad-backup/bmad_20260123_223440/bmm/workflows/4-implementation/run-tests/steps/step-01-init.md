---
name: 'step-01-init'
description: 'Initialize test workflow by loading and validating project configuration'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/run-tests'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-execute.md'
workflowFile: '{workflow_path}/workflow.md'
projectConfigFile: '{project-root}/_bmad/project-config.yaml'
---

# Step 1: Initialize Test Runner

## STEP GOAL:

To load the project configuration and validate that test commands are configured before execution.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently

### Role Reinforcement:

- ✅ You are a test runner and code fixer
- ✅ Execute commands, analyze failures, fix issues
- ✅ Be efficient and clear in reporting

### Step-Specific Rules:

- 🎯 Focus ONLY on loading and validating config
- 🚫 FORBIDDEN to run any tests in this step
- ✅ Validate test section exists and has enabled commands

## EXECUTION PROTOCOLS:

- 🎯 Load and validate project-config.yaml before any execution
- 💾 Store enabled commands in memory for step 2
- 📖 Display clear test plan to user
- 🚫 FORBIDDEN to execute any tests in this step

## CONTEXT BOUNDARIES:

- Available context: Workflow initialization, module config
- Focus: Configuration loading and validation
- Limits: No test execution, only validation
- Dependencies: project-config.yaml must exist with test section

## INITIALIZATION SEQUENCE:

### 1. Load Project Configuration

Read `{projectConfigFile}` and extract the `test` section.

### 2. Validate Configuration

Check that:
- The file exists
- The `test` section exists
- At least one command is enabled

### 3. Handle Missing Config

If project-config.yaml doesn't exist:

Display error:
"**Error: No project configuration found**

Run `/project-config` first to set up your test commands.

Workflow aborted."

End workflow.

### 4. Handle Missing Test Section

If `test` section doesn't exist or all commands are disabled:

Display error:
"**Error: No test commands configured**

Your project-config.yaml exists but has no test commands enabled.

Run `/project-config` to configure test commands.

Workflow aborted."

End workflow.

### 5. Log Test Plan

Output to stdout:
```
[step-01] ✓ Test configuration loaded
[step-01]   Commands enabled:
[step-01]     - pre_commands: [count]
[step-01]     - unit: [yes/no]
[step-01]     - e2e: [yes/no]
[step-01]     - lint: [yes/no]
[step-01]     - typecheck: [yes/no]
[step-01]     - custom: [count]
[step-01] ✓ Step 1 complete - proceeding to execution
```

### 6. Store Config Context

Store in memory for next step:
- All enabled commands with their command strings
- Order of execution: pre_commands → unit → e2e → lint → typecheck → custom

### 7. Auto-Proceed

Immediately load, read entire file, then execute `{nextStepFile}` to begin test execution.

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [configuration loaded and validated with enabled commands identified], will you then load and read fully `{nextStepFile}` to execute and begin test command execution phase.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project config loaded successfully
- Test section validated
- Commands parsed and ready for execution
- Proceeded to step 2

### ❌ SYSTEM FAILURE:

- Not checking for config file
- Not validating test section
- Proceeding without valid commands
- Not displaying test plan

**Master Rule:** Execute all actions completely, track all results, and proceed to the correct next step. Always validate configuration before attempting to run tests.
