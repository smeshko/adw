# BMAD Action Workflow Template

This template provides the standard structure for **action workflows** - automated, non-interactive workflows that execute commands and actions without user intervention between steps.

## When to Use Action Workflows

Use this template when:

- The workflow executes system commands (tests, builds, deployments)
- No user decision points are needed between steps
- The workflow should run to completion automatically
- Results are reported at the end, not iteratively

Use the standard workflow template instead when:

- User collaboration or input is needed at each step
- Content is being co-created with the user
- Decision points require user selection
- The workflow produces documents iteratively

<!-- TEMPLATE START -->

---

name: [WORKFLOW_NAME]
description: [Brief description of what this workflow accomplishes]
web_bundle: [true/false]

---

# [WORKFLOW_DISPLAY_NAME]

**Goal:** [State the primary goal of this workflow in one clear sentence]

**Your Role:** You are a [role] that executes [type of actions]. Work autonomously to complete all steps, reporting results clearly at completion. User interaction is only needed if errors require manual intervention.

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that executes commands and actions autonomously.

### Core Principles

- **Config-Driven**: Actions and commands come from configuration files
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

Load and read full config from {project-root}/\_bmad/[MODULE_FOLDER]/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`

[If additional config needed:]
Load [additional config] from [path] and resolve:

- [config values needed]

### 2. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-[name].md` to begin the workflow.

<!-- TEMPLATE END -->

## How to Use This Template

### Step 1: Copy and Replace Placeholders

Copy the template above and replace:

- `[WORKFLOW_NAME]` → Your workflow's kebab-case name (e.g., `test`, `build`, `deploy`)
- `[WORKFLOW_DISPLAY_NAME]` → Your workflow's display name (e.g., `Test Runner`)
- `[Brief description]` → One-sentence description
- `[true/false]` → Whether to include in web bundle
- `[role]` → AI's role (e.g., "test runner", "build executor", "deployment agent")
- `[type of actions]` → What the workflow does (e.g., "test commands", "build steps")
- `[MODULE_FOLDER]` → Target module (e.g., `bmm`, `bmb`, `core`)

### Step 2: Create the Folder Structure

```
[workflow-folder]/
├── workflow.md          # This file
└── steps/
    ├── step-01-init.md
    ├── step-02-[action].md
    ├── step-03-[action].md
    └── step-0N-report.md  # Final step should always report results
```

### Step 3: Design Your Step Flow

Action workflows typically follow this pattern:

1. **Init Step**: Load configuration, validate prerequisites
2. **Action Steps**: Execute commands/actions, collect results
3. **Conditional Steps**: Handle success/failure paths (optional)
4. **Report Step**: Summarize results, provide next steps

### Step 4: Configure Step Routing

Action workflows can use:

- **Linear routing**: Each step proceeds to the next
- **Conditional routing**: Route based on results (e.g., success → report, failure → fix → report)

Example conditional routing in step frontmatter:

```yaml
# File References
thisStepFile: '{workflow_path}/steps/step-02-execute.md'
successStepFile: '{workflow_path}/steps/step-04-report.md'
failureStepFile: '{workflow_path}/steps/step-03-fix.md'
```

## Key Differences from Standard Workflows

| Aspect | Standard Workflow | Action Workflow |
|--------|-------------------|-----------------|
| User Interaction | Required at each step | Only on errors |
| Menus | A/P/C options | None (auto-proceed) |
| Role | Facilitator/Collaborator | Executor/Runner |
| Content Generation | User-directed | Autonomous |
| Progress Reporting | Iterative | End-of-workflow |
| State Tracking | Output file frontmatter | In-memory context |

## Reference Example

See `{project-root}/_bmad/bmm/workflows/4-implementation/run-tests/workflow.md` for a complete action workflow implementation.
