---
name: 'step-01-init'
description: 'Initialize ship workflow, validate configuration, and run pre-checks'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/ship'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-execute.md'
workflowFile: '{workflow_path}/workflow.md'
projectConfigFile: '{project-root}/_bmad/project-config.yaml'
---

# Step 1: Initialize Ship

## STEP GOAL:

To load and validate the ship configuration from project-config.yaml, run any configured pre-check commands, and confirm the deployment plan with the user before proceeding.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step upon completion
- ⛔ FAIL FAST: Stop immediately on validation or pre-check failure
- 📊 TRACK STATE: Maintain context for final reporting

### Role Reinforcement:

- ✅ You are a release manager executing deployment autonomously
- ✅ Work autonomously without waiting for user input
- ✅ Log progress to stdout for CI visibility
- ✅ Only stop on critical errors or pre-check failures

### Step-Specific Rules:

- 🎯 Focus ONLY on loading config and running pre-checks
- 🚫 FORBIDDEN to execute any deployment commands (version bump, build, publish)
- 📊 Log all actions to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Load and parse project-config.yaml ship section
- 💾 Validate required configuration exists
- 📖 Run all configured pre-checks
- 🚫 FORBIDDEN to proceed if pre-checks fail

## CONTEXT BOUNDARIES:

- Available context: Project configuration, ship section settings
- Focus: Configuration validation and pre-check execution
- Limits: No deployment commands - only validation and confirmation
- Dependencies: project-config.yaml must exist with ship section

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Load Project Configuration

Read `{projectConfigFile}` and extract the `ship` section.

Expected structure:
```yaml
ship:
  pre_checks: []
  type: npm | docker | github-release | custom
  commands:
    version_bump: "command"
    build: "command"
    publish: "command"
    post_publish: []
  environments:
    staging: {}
    production: {}
```

### 2. Validate Configuration

Check that:
- The file exists
- The `ship` section exists
- At least `publish` command is configured

### 3. Handle Missing Config

If project-config.yaml doesn't exist or no ship section:

Display error:
"**Error: No ship configuration found**

Run `/project-config` first to set up your deployment commands.

Workflow aborted."

End workflow.

### 4. Log Ship Plan

Output to stdout:
```
[step-01] ✓ Ship configuration loaded
[step-01]   Type: [npm/docker/github-release/custom]
[step-01]   Version Bump: [command or 'not configured']
[step-01]   Build: [command or 'not configured']
[step-01]   Publish: [command]
[step-01]   Post-Publish: [count] commands
[step-01]   Pre-Checks: [count] commands
```

### 5. Run Pre-Checks

If `pre_checks` is configured and not empty:

Output to stdout:
```
[step-01] Running pre-checks...
```

For each pre-check command:
- Execute the command
- Output: `[step-01]   ✓ [command] passed` or `[step-01]   ✗ [command] failed`

If any pre-check fails:

Output to stdout:
```
[step-01] ✗ CRITICAL: Pre-check failed
[step-01]   Command: [failed command]
[step-01]   Error: [error output]
[step-01]   Deployment aborted
[step-01] Exit Code: 1
```

Exit with code 1.

If all pre-checks pass (or none configured):

Output to stdout:
```
[step-01] ✓ All pre-checks passed
[step-01] ✓ Step 1 complete - proceeding to deployment execution
```

### 6. Auto-Proceed

Store ship context in memory, then load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Configuration loaded and validated successfully
- All pre-checks executed and passed
- Progress logged to stdout
- Auto-proceeded to execution step

### ❌ CRITICAL FAILURE (Exit 1):

- Configuration file not found
- Ship section not configured
- Pre-checks failed

### ⚠️ WARNING (Continue):

- Optional configuration missing

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
