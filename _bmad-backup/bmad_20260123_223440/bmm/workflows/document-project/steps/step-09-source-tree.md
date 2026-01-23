---
name: 'step-09-source-tree'
description: 'Generate annotated source tree analysis'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-09-source-tree.md'
nextStepFile: '{workflow_path}/steps/step-10-dev-ops.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'

# Template References
sourceTreeTemplate: '{workflow_path}/templates/source-tree-template.md'
---

# Step 9: Source Tree Analysis

## STEP GOAL:

Generate a complete, annotated directory tree showing the project structure with purpose annotations for critical directories.

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

- 🎯 Focus only on source tree generation and annotation
- 🚫 FORBIDDEN to skip critical directory annotations
- 📊 Mark entry points and integration points
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Generate directory tree using critical_directories from requirements
- 💾 Annotate tree with directory purposes
- 📖 Mark entry points and key file locations
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Conditional scan results, project structure
- Focus: Source tree visualization and annotation
- Limits: Structure documentation only
- Dependencies: Conditional analysis complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Generate Directory Tree

For each part, generate complete directory tree using critical_directories from doc requirements.

### 2. Annotate the Tree

Add annotations for:
- Purpose of each critical directory
- Entry points marked with indicators
- Key file locations highlighted
- Integration points noted (for multi-part projects)

### 3. Format Output

Create formatted source tree with descriptions:

```
project-root/
├── client/          # React frontend (Part: client)
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Route-based pages
│   │   └── api/         # API client layer → Calls server/
├── server/          # Express API backend (Part: api)
│   ├── src/
│   │   ├── routes/      # REST API endpoints
│   │   ├── models/      # Database models
│   │   └── services/    # Business logic
```

### 4. Write Documentation

Write to: `{output_folder}/source-tree-analysis.md`

Validate document structure.

### 5. Log Completion

Output to stdout:
```
[step-09] ✓ Source tree analysis complete
[step-09]   File: source-tree-analysis.md
[step-09]   Directories annotated: {dir_count}
[step-09]   Entry points marked: {entry_point_count}
```

### 6. Update State

Update state file with:
- Add "step-09" to completed_steps
- Add source-tree-analysis.md to outputs_generated
- Set current_step = "step-10"

Output to stdout:
```
[step-09] ✓ Step 9 complete - proceeding to dev/ops documentation
```

### 7. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Complete directory tree generated
- Critical directories annotated with purposes
- Entry points clearly marked
- Integration points noted for multi-part
- File written and validated
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot access project directories
- Cannot write output file

### ⚠️ WARNING (Continue):

- Some directories inaccessible

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
