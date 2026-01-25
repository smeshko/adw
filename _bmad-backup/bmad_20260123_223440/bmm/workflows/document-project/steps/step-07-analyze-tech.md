---
name: 'step-07-analyze-tech'
description: 'Analyze technology stack for each project part'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-07-analyze-tech.md'
nextStepFile: '{workflow_path}/steps/step-08-conditional-scan.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 7: Analyze Technology Stack

## STEP GOAL:

Analyze the technology stack for each project part by parsing manifest files and detecting frameworks, languages, and dependencies.

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

- 🎯 Focus only on technology detection and architecture patterns
- 🚫 FORBIDDEN to guess technologies without evidence
- 📊 Build technology table with justification
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Parse technology manifest files
- 💾 Build technology table per part
- 📖 Determine architecture patterns
- 📊 Log findings to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Project structure and existing docs from previous steps
- Focus: Technology stack analysis
- Limits: Manifest parsing only (not deep source analysis yet)
- Dependencies: Project structure detected

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Parse Technology Manifests

For each part in project_parts:
- Load key_file_patterns from documentation_requirements
- Scan part root for these patterns
- Parse technology manifest files (package.json, go.mod, requirements.txt, etc.)
- Extract: framework, language, version, database, key dependencies

### 2. Build Technology Table

Build technology_table with columns:
- Category (Language, Framework, Database, Testing, etc.)
- Technology name
- Version
- Justification (where detected)

### 3. Determine Architecture Pattern

Based on detected tech stack and project_type_id:
- Use project_type_id as primary indicator
- Consider framework patterns (React → component hierarchy, Express → middleware pipeline)
- Note architectural style
- Store as `architecture_pattern` for each part

### 4. Log Findings

Output to stdout:
```
[step-07] ✓ Technology stack analyzed
[step-07]   Languages: {languages_list}
[step-07]   Frameworks: {frameworks_list}
[step-07]   Architecture: {architecture_pattern}
```

### 5. Update State

Update state file with:
- Add "step-07" to completed_steps
- technology_table per part
- architecture_pattern
- Set current_step = "step-08"

Output to stdout:
```
[step-07] ✓ Step 7 complete - proceeding to conditional scanning
```

### 6. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Manifest files parsed correctly
- Technology table built with evidence
- Architecture pattern determined
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- No manifest files found
- Cannot parse any technology indicators

### ⚠️ WARNING (Continue):

- Some manifest files unreadable
- Low confidence technology detection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
