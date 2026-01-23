---
name: {{workflowName}}
description: {{workflowDescription}}
web_bundle: {{webBundleFlag}}
---

# {{workflowDisplayName}}

**Goal:** {{workflowGoal}}

**Your Role:** You are a {{aiRole}} that executes {{actionType}}. Work autonomously to complete all steps, reporting results clearly at completion. User interaction is only needed if errors require manual intervention.

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that executes commands and actions autonomously.

### Core Principles

- **Config-Driven**: {{configDescription}}
- **Run All**: Execute all configured steps, collecting results throughout
- **Auto-Proceed**: Move between steps automatically without user confirmation
- **Clear Reporting**: Provide comprehensive status at workflow completion
- **Fail-Safe**: Handle errors gracefully, continue where possible, report all issues

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Move to next step immediately upon completion (no menu wait)
4. **TRACK STATE**: Maintain execution context between steps for final reporting
5. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 🔄 **ALWAYS** run all configured commands (don't fail fast)
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📊 **ALWAYS** track results for final reporting
- ⏹️ **STOP** only when workflow completes or unrecoverable error occurs

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read config from {project-root}/_bmad/{{targetModule}}/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`

{{#hasAdditionalConfig}}
Load {{additionalConfigName}} from {{additionalConfigPath}} and resolve:

{{#additionalConfigVars}}
- `{{.}}`
{{/additionalConfigVars}}
{{/hasAdditionalConfig}}

### 2. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-{{firstStepName}}.md` to begin the workflow.
