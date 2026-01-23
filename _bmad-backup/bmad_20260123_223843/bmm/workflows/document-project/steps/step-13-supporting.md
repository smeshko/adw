---
name: 'step-13-supporting'
description: 'Generate supporting documentation files'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-13-supporting.md'
nextStepFile: '{workflow_path}/steps/step-14-index.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'

# Template References
projectOverviewTemplate: '{workflow_path}/templates/project-overview-template.md'
---

# Step 13: Supporting Documentation

## STEP GOAL:

Generate supporting documentation files including project overview, component inventory, and any conditional documentation based on project type.

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

- 🎯 Focus only on supporting document generation
- 🚫 FORBIDDEN to skip applicable document types
- 📊 Comprehensive but organized
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Generate project overview
- 💾 Generate component inventories if applicable
- 📖 Generate project-parts.json for multi-part
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: All previous analysis
- Focus: Supporting documentation only
- Limits: Organization and writing
- Dependencies: Architecture docs complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Generate Project Overview

Write `{output_folder}/project-overview.md` with:
- Project name and purpose
- Executive summary
- Tech stack summary table
- Architecture type classification
- Repository structure
- Links to detailed docs

### 2. Generate Component Inventories

If requires_ui_components == true:
- Write `{output_folder}/component-inventory.md` (or per-part versions)
- Categorize by type
- Note reusable vs specific components

### 3. Generate Multi-Part Metadata

If multi-part project:
- Write `{output_folder}/project-parts.json`:

```json
{
  "repository_type": "monorepo",
  "parts": [...],
  "integration_points": [...]
}
```

### 4. Write Additional Conditional Docs

Based on what was found in previous steps, ensure these exist:
- api-contracts.md (if API scan done)
- data-models.md (if data models scanned)
- deployment-guide.md (if deployment config found)
- contribution-guide.md (if guidelines found)

### 5. Log Completion

Output to stdout:
```
[step-13] ✓ Supporting documentation generated
[step-13]   project-overview.md: ✓
[step-13]   component-inventory.md: {component_inventory_generated ? "✓" : "skipped"}
[step-13]   project-parts.json: {multi_part ? "✓" : "skipped"}
```

### 6. Update State

Update state file with:
- Add "step-13" to completed_steps
- Add supporting files to outputs_generated
- Set current_step = "step-14"

Output to stdout:
```
[step-13] ✓ Step 13 complete - proceeding to index generation
```

### 7. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project overview generated
- Component inventories created if applicable
- Multi-part metadata written if applicable
- All supporting files exist
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write project overview
- Cannot write critical supporting files

### ⚠️ WARNING (Continue):

- Optional supporting files skipped

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
