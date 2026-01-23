---
name: 'step-01-init'
description: 'Initialize test workflow by loading and validating project configuration'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/run-tests'

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
- ✅ Be efficient - no unnecessary output

### Step-Specific Rules:

- 🎯 Focus ONLY on loading and validating config
- 🚫 FORBIDDEN to run any tests in this step
- ✅ Validate test section exists and has enabled commands
- 🚫 NO stdout logging - silent initialization

## EXECUTION PROTOCOLS:

- 🎯 Load and validate project-config.yaml before any execution
- 💾 Store enabled commands in context for step 2
- 🚫 FORBIDDEN to execute any tests in this step
- 🚫 NO stdout logging - only build context silently

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

Output error JSON and exit:

```json
{
  "status": "failed",
  "summary": { "total": 1, "errors": 1, "warnings": 0, "fixed": 0 },
  "issues": [
    {
      "id": "config-001",
      "severity": "error",
      "type": "config_error",
      "command": "init",
      "description": "No project configuration found. Run /project-config first.",
      "location": "_bmad/project-config.yaml",
      "context": {
        "fixable": false,
        "fix_hint": "Create project-config.yaml with test commands"
      }
    }
  ]
}
```

Exit with code 1. Workflow ends.

### 4. Handle Missing Test Section

If `test` section doesn't exist or all commands are disabled:

Output error JSON and exit:

```json
{
  "status": "failed",
  "summary": { "total": 1, "errors": 1, "warnings": 0, "fixed": 0 },
  "issues": [
    {
      "id": "config-002",
      "severity": "error",
      "type": "config_error",
      "command": "init",
      "description": "No test commands configured in project-config.yaml",
      "location": "_bmad/project-config.yaml",
      "context": {
        "fixable": false,
        "fix_hint": "Add test commands to project-config.yaml test section"
      }
    }
  ]
}
```

Exit with code 1. Workflow ends.

### 5. Build Execution Context

Store in context for next step:

```
context = {
  enabledCommands: {
    pre_commands: [...],  // array of command strings
    unit: { enabled: bool, command: "..." },
    e2e: { enabled: bool, command: "..." },
    lint: { enabled: bool, command: "..." },
    typecheck: { enabled: bool, command: "..." },
    custom: [...]  // array of custom command objects
  },
  executionOrder: ["pre_commands", "unit", "e2e", "lint", "typecheck", "custom"]
}
```

### 6. Auto-Proceed

Immediately load, read entire file, then execute `{nextStepFile}` to begin test execution.

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [configuration loaded and validated with enabled commands identified], will you then load and read fully `{nextStepFile}` to execute and begin test command execution phase.

If configuration is invalid, output error JSON and exit immediately.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project config loaded successfully
- Test section validated
- Commands parsed and stored in context
- Proceeded to step 2 silently

### ❌ SYSTEM FAILURE:

- Not checking for config file
- Not validating test section
- Proceeding without valid commands
- Outputting text logs instead of JSON errors

**Master Rule:** Execute all actions completely, validate configuration, output JSON errors if invalid, and proceed to the correct next step silently.
