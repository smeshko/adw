---
name: 'step-04-load-requirements'
description: 'Load documentation requirements CSV for project type detection'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-04-load-requirements.md'
nextStepFile: '{workflow_path}/steps/step-05-detect-project.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'

# Data References
documentation_requirements_csv: '{workflow_path}/documentation-requirements.csv'
---

# Step 4: Load Documentation Requirements

## STEP GOAL:

Load the documentation requirements CSV which contains project type detection patterns and documentation requirements for 12 different project types.

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

- 🎯 Focus only on loading the requirements data
- 🚫 FORBIDDEN to skip data loading
- 📊 Log all actions to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Load documentation-requirements.csv
- 💾 Parse and index all 12 project types
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Configuration from step-01
- Focus: Data loading
- Limits: No project detection yet
- Dependencies: Successful completion of step-01

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Log Step Start

Output to stdout:
```
[step-04] Loading documentation requirements...
```

### 2. Load Requirements Data

Load documentation-requirements.csv from: `{documentation_requirements_csv}`

Store all 12 rows indexed by project_type_id for project detection and requirements lookup.

**On success:**
```
[step-04] ✓ Loaded documentation requirements CSV
[step-04]   Project types: 12 (web, mobile, backend, cli, library, desktop, game, data, extension, infra, embedded, hybrid)
[step-04]   Columns: 24 (detection + documentation requirements)
```

**On failure (CRITICAL):**
```
[step-04] ✗ CRITICAL: Failed to load documentation-requirements.csv
[step-04]   Path: {documentation_requirements_csv}
[step-04]   Error: {error_message}
```
Exit with code 1.

### 3. Update State

Update state file:
- Add "step-04" to completed_steps
- Set current_step = "step-05"
- Update last_updated timestamp

Output to stdout:
```
[step-04] ✓ Step 4 complete - proceeding to project detection
```

### 4. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- CSV file loaded and parsed correctly
- All 12 project types available for detection
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- CSV file not found
- CSV parsing errors
- Required columns missing

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
