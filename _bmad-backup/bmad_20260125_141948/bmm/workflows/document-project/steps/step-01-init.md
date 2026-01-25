---
name: 'step-01-init'
description: 'Initialize workflow, validate configuration, and prepare for scanning'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-04-load-requirements.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'

# Data References
documentation_requirements_csv: '{workflow_path}/documentation-requirements.csv'

# External Workflow References
workflowStatusPath: '{project-root}/_bmad/bmm/workflows/workflow-status'
---

# Step 1: Workflow Initialization

## STEP GOAL:

Initialize the document-project workflow by loading configuration, resolving environment variables, and preparing the state file for autonomous scanning.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step upon completion
- 🤖 YOU ARE AN EXECUTOR, running autonomously

### Role Reinforcement:

- ✅ You are a technical documentarian executing codebase analysis
- ✅ Work autonomously without waiting for user input
- ✅ Log progress to stdout for CI visibility
- ✅ Only stop on critical errors

### Step-Specific Rules:

- 🎯 Focus only on initialization and configuration loading
- 🚫 FORBIDDEN to begin scanning without completing initialization
- 📊 Log all actions to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Load and validate configuration from bmm/config.yaml
- 🔧 Resolve environment variable overrides
- 💾 Initialize state file
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: BMM configuration, environment variables
- Focus: Initialization, configuration resolution
- Limits: No scanning or documentation generation yet
- Dependencies: Valid BMM configuration

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Log Initialization Start

Output to stdout:
```
[step-01] Initializing document-project workflow...
```

### 2. Load Configuration

Load configuration from `{project-root}/_bmad/bmm/config.yaml` and resolve all variables.

**On success:**
```
[step-01] ✓ Configuration loaded from bmm/config.yaml
[step-01]   Project: {project_name}
[step-01]   Output: {output_folder}
```

**On failure (CRITICAL):**
```
[step-01] ✗ CRITICAL: Failed to load configuration
[step-01]   Error: {error_message}
```
Exit with code 1.

### 3. Resolve Environment Variables

Check and resolve environment variables with defaults:

- `SCAN_MODE` → `scan_mode` (default: `full`)
- `SCAN_LEVEL` → `scan_level` (default: `deep`)
- `FAIL_ON_WARNING` → `fail_on_warning` (default: `false`)

Output to stdout:
```
[step-01] ✓ Environment configuration:
[step-01]   SCAN_MODE: {scan_mode}
[step-01]   SCAN_LEVEL: {scan_level}
[step-01]   FAIL_ON_WARNING: {fail_on_warning}
```

### 4. Check Project Type (Optional)

Check if workflow-status file exists to detect project type:

**If status file exists with greenfield:**
```
[step-01] ⚠ Warning: Greenfield project detected
[step-01]   Documentation workflow is typically for brownfield projects
[step-01]   Continuing to document planning artifacts...
```
Set `warning_count += 1`

**If brownfield or no status file:**
```
[step-01] ✓ Project type: {field_type | "standalone"}
```

### 5. Initialize State File

Create or update state file at `{stateFile}`:

```json
{
  "workflow_version": "2.0.0",
  "execution_mode": "autonomous",
  "timestamps": {
    "started": "{current_timestamp}",
    "last_updated": "{current_timestamp}"
  },
  "config": {
    "scan_mode": "{scan_mode}",
    "scan_level": "{scan_level}",
    "fail_on_warning": "{fail_on_warning}"
  },
  "project_root": "{project-root}",
  "output_folder": "{output_folder}",
  "completed_steps": ["step-01"],
  "current_step": "step-04",
  "warnings": [],
  "errors": [],
  "findings": {},
  "outputs_generated": ["project-scan-report.json"]
}
```

Output to stdout:
```
[step-01] ✓ State file initialized: {stateFile}
[step-01] ✓ Step 1 complete - proceeding to load requirements
```

### 6. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Configuration successfully loaded from bmm/config.yaml
- Environment variables resolved with defaults
- State file initialized
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot load configuration file
- Cannot create state file
- Cannot resolve required paths

### ⚠️ WARNING (Continue):

- Greenfield project detected
- Optional configuration missing

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
