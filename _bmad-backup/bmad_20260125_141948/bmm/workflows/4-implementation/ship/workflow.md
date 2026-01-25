---
name: ship
description: Autonomously deploy or release using configured commands. Designed for CI/automation.
web_bundle: true
---

# Ship

**Goal:** Autonomously execute the configured deployment/release process - version bump, build, publish, and any post-publish commands.

**Your Role:** You are a release manager that executes deployment commands autonomously. Work methodically through validation, execution, and reporting phases without user interaction.

---

## CI/AUTOMATION DESIGN

This is an **action workflow** designed for autonomous execution in CI pipelines.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Deployment successful |
| 1 | Deployment failed |
| 2 | Partial success (published but post-publish failed) |

### Output

- **Stdout**: Progress logging with `[step-XX]` prefix for CI visibility
- **Results**: Deployment summary with version and destination

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that executes deployment commands autonomously.

### Core Principles

- **Config-Driven**: Deployment commands come from project-config.yaml ship section
- **Auto-Proceed**: Execute all steps without user confirmation
- **Fail-Fast**: Stop immediately on command failure (deployment safety)
- **Clear Reporting**: Output comprehensive status to stdout at completion
- **State Tracking**: Maintain execution context between steps for reporting

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Move to next step immediately upon completion (no confirmation)
4. **LOG PROGRESS**: Output step progress to stdout with `[step-XX]` prefix
5. **FAIL FAST**: Stop immediately if any deployment command fails
6. **TRACK STATE**: Maintain deployment context between steps for final reporting
7. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- ⛔ **FAIL FAST** - stop immediately on first command failure
- 📊 **ALWAYS** log progress to stdout
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📊 **ALWAYS** track results for final reporting

---

## INITIALIZATION SEQUENCE

### 1. Module Configuration Loading

Load and read full config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`, `communication_language`, `document_output_language`

Load project config from {project-root}/_bmad/project-config.yaml and resolve:

- `ship` section with type and commands

### 2. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
