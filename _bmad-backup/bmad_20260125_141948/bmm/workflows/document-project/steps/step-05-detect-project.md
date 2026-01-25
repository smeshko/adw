---
name: 'step-05-detect-project'
description: 'Detect project structure and classify project type'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-05-detect-project.md'
nextStepFile: '{workflow_path}/steps/step-06-discover-docs.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 5: Detect Project Structure

## STEP GOAL:

Scan the project root to detect structure (monolith/monorepo/multi-part) and classify project type(s) using key_file_patterns from documentation requirements.

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

- 🎯 Focus only on structure detection and type classification
- 🚫 FORBIDDEN to assume structure without verification
- 📊 Log all findings to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Use current working directory as project root
- 💾 Scan for key indicators and structure patterns
- 📖 Match against documentation requirements patterns
- 📊 Log detected structure to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Documentation requirements from step-04
- Focus: Project structure and type detection
- Limits: Detection only, no content scanning yet
- Dependencies: Documentation requirements loaded

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Log Step Start

Output to stdout:
```
[step-05] Detecting project structure...
```

### 2. Set Project Root

Use current working directory as `project_root_path`.

Output to stdout:
```
[step-05]   Project root: {project_root_path}
```

### 3. Scan for Structure Indicators

Scan `project_root_path` for:
- Directory structure (client/, server/, api/, src/, app/, packages/, etc.)
- Key files (package.json, go.mod, requirements.txt, etc.)
- Technology markers matching key_file_patterns from requirements

Output to stdout:
```
[step-05]   Scanning directory structure...
[step-05]   Key files found: {key_files_list}
```

### 4. Detect Repository Type

Determine if project is:
- **Monolith**: Single cohesive codebase
- **Monorepo**: Multiple packages in one repository (pnpm-workspace, lerna, nx, etc.)
- **Multi-part**: Separate client/server or similar architecture

Output to stdout:
```
[step-05] ✓ Repository type: {repository_type}
```

**If multiple distinct parts detected:**
```
[step-05]   Parts detected:
[step-05]     - {part_1_name}: {part_1_path}
[step-05]     - {part_2_name}: {part_2_path}
```
Create project_parts array with all detected parts.

**If single project detected:**
```
[step-05]   Structure: Single codebase
```
Create single part in project_parts array.

### 5. Classify Project Type(s)

For each part, match detected patterns against key_file_patterns from documentation requirements.

Assign project_type_id to each part and load corresponding requirements.

Output to stdout:
```
[step-05] ✓ Project classification:
[step-05]   {part_name}: {project_type_id} ({confidence}% match)
```

**If no confident match (CRITICAL):**
```
[step-05] ✗ CRITICAL: Could not classify project type
[step-05]   No key_file_patterns matched with sufficient confidence
[step-05]   Files found: {files_list}
```
Exit with code 1.

### 6. Update State

Update state file:
- Add "step-05" to completed_steps
- Cache project_type_id(s) and repository_type
- Store project_parts array
- Set current_step = "step-06"

Output to stdout:
```
[step-05] ✓ Step 5 complete - proceeding to documentation discovery
```

### 7. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project root correctly identified
- Repository type accurately detected
- Project type(s) classified using requirements patterns
- All parts properly populated
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot access project root directory
- No project type patterns match
- Cannot determine repository structure

### ⚠️ WARNING (Continue):

- Low confidence classification (log warning, proceed)
- Some directories inaccessible (log, continue with available)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
