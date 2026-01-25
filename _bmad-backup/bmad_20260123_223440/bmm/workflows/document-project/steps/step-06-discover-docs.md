---
name: 'step-06-discover-docs'
description: 'Discover existing documentation and gather user context'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-06-discover-docs.md'
nextStepFile: '{workflow_path}/steps/step-07-analyze-tech.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 6: Discover Existing Documentation

## STEP GOAL:

Scan for existing documentation files in the project and gather any additional context or focus areas from the user.

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

- 🎯 Focus only on documentation discovery
- 🚫 FORBIDDEN to ignore existing documentation
- 📊 Log all findings to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Scan for common documentation patterns
- 💾 Create inventory of existing docs
- 📊 Log findings to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Project structure from step-05
- Focus: Documentation discovery and user guidance
- Limits: Discovery only, no analysis yet
- Dependencies: Project structure detected

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Scan for Existing Documentation

For each project part, scan for:
- README.md, README.rst, README.txt
- CONTRIBUTING.md, CONTRIBUTING.rst
- ARCHITECTURE.md, docs/architecture/
- DEPLOYMENT.md, DEPLOY.md, docs/deployment/
- API.md, docs/api/
- Any files in docs/, documentation/, .github/ folders

### 2. Create Documentation Inventory

Create inventory of existing_docs with:
- File path
- File type (readme, architecture, api, etc.)
- Which part it belongs to (if multi-part)

### 3. Log Findings

Output to stdout:
```
[step-06] ✓ Documentation discovery complete
[step-06]   Found: {existing_docs_count} documentation files
[step-06]   Types: {doc_types_summary}
```

### 4. Update State

Update state file with:
- Add "step-06" to completed_steps
- existing_docs inventory
- Set current_step = "step-07"

Output to stdout:
```
[step-06] ✓ Step 6 complete - proceeding to technology analysis
```

### 5. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All standard documentation locations scanned
- Existing docs properly inventoried
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot access project directories

### ⚠️ WARNING (Continue):

- Some documentation directories inaccessible

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
