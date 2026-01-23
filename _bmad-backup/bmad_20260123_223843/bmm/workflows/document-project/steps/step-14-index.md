---
name: 'step-14-index'
description: 'Generate master index as primary AI retrieval source'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-14-index.md'
nextStepFile: '{workflow_path}/steps/step-15-validate.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
indexFile: '{output_folder}/index.md'

# Template References
indexTemplate: '{workflow_path}/templates/index-template.md'
---

# Step 14: Generate Master Index

## STEP GOAL:

Generate the master index.md file that serves as the primary navigation and retrieval source for AI-assisted development.

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

- 🎯 Focus only on index generation
- 🚫 FORBIDDEN to create broken links
- 📊 Comprehensive navigation structure
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Generate index with intelligent navigation
- 💾 Check which expected files actually exist
- 📖 Mark missing files with standard marker
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: All generated documentation files
- Focus: Index generation and link validation
- Limits: Index file only
- Dependencies: All documentation generated

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Check File Existence

Before writing index.md, check which expected files exist:
- For each document that should have been generated, check if file exists
- Set existence flags
- Track missing files in `missing_docs_list`

### 2. Generate Index Content

Create index.md with:

**Project Overview Section:**
- Type (monolith/monorepo/multi-part)
- Primary Language
- Architecture type

**Quick Reference Section:**
- Tech stack summary
- Entry points
- Architecture patterns
- Per-part summaries if multi-part

**Generated Documentation Section:**
- Links to all generated docs
- Mark missing docs with: _(To be generated)_

**Existing Documentation Section:**
- Links to discovered existing docs

**Getting Started Section:**
- Quick start instructions

### 3. Write Index File

Write to: `{output_folder}/index.md`

Validate all links.

### 4. Log Completion

Output to stdout:
```
[step-14] ✓ Master index generated
[step-14]   File: index.md
[step-14]   Links validated: {links_count}
[step-14]   Missing docs marked: {missing_count}
```

### 5. Update State

Update state file with:
- Add "step-14" to completed_steps
- Add index.md to outputs_generated
- Set current_step = "step-15"

Output to stdout:
```
[step-14] ✓ Step 14 complete - proceeding to validation
```

### 6. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Index generated with all sections
- File existence checked
- Missing files marked properly
- All links validated
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write index.md

### ⚠️ WARNING (Continue):

- Some expected files missing (marked appropriately)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
