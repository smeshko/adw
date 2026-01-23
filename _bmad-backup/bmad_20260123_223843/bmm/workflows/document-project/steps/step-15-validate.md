---
name: 'step-15-validate'
description: 'Validate and review generated documentation with option to complete gaps'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-15-validate.md'
nextStepFile: '{workflow_path}/steps/step-16-finalize.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
indexFile: '{output_folder}/index.md'
checklistFile: '{workflow_path}/checklist.md'
---

# Step 15: Validate and Review

## STEP GOAL:

Validate generated documentation, detect incomplete items, and offer options to complete gaps or make adjustments before finalization.

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

- 🎯 Focus only on validation
- 📊 Log validation results to stdout
- ⚠️ Log warnings for incomplete items
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Validate generated files
- 💾 Detect incomplete documentation markers
- 📊 Log validation summary to stdout
- ⚡ Auto-proceed to finalization

## CONTEXT BOUNDARIES:

- Available context: All generated files, index.md
- Focus: Validation and gap completion
- Limits: Review only, major changes should restart
- Dependencies: Index generated

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Log Validation Start

Output to stdout:
```
[step-15] Validating generated documentation...
```

### 2. Generate Validation Summary

Collect stats:
- Files generated count
- Total size
- Project type
- Parts documented

Output to stdout:
```
[step-15] Documentation Generation Summary:
[step-15]   Output folder: {output_folder}
[step-15]   Project type: {project_type_summary}
[step-15]   Parts documented: {parts_count}
[step-15]   Files generated: {files_count}
```

### 3. Detect Incomplete Documentation

Read index.md and scan for markers:
- Primary: `_(To be generated)_`
- Fallback: `_(TBD)_`, `_(TODO)_`, `_(Coming soon)_`

For each match, extract:
- Document title
- File path

**If incomplete items found:**
```
[step-15] ⚠ Incomplete documentation detected:
[step-15]   - {incomplete_item_1}
[step-15]   - {incomplete_item_2}
```
Add to warnings array.

**If all complete:**
```
[step-15] ✓ All documentation complete
```

### 4. Update State

Update state file with:
- Add "step-15" to completed_steps
- Record validation_summary
- Record incomplete_items (if any)
- Set current_step = "step-16"

Output to stdout:
```
[step-15] ✓ Step 15 complete - proceeding to finalization
```

### 5. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Validation summary generated
- Incomplete items detected and logged
- Warnings recorded for CI
- Progress logged to stdout
- Auto-proceeded to finalization

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot read index.md for validation

### ⚠️ WARNING (Continue):

- Incomplete documentation detected (logged as warning)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
