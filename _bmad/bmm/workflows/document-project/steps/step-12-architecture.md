---
name: 'step-12-architecture'
description: 'Generate architecture documentation for each part'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-12-architecture.md'
nextStepFile: '{workflow_path}/steps/step-13-supporting.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 12: Architecture Documentation

## STEP GOAL:

Generate comprehensive architecture documentation for each project part, consolidating all previous analysis into structured architecture files.

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

- 🎯 Focus only on consolidating into architecture docs
- 🚫 FORBIDDEN to skip any part in multi-part projects
- 📊 Comprehensive but organized documentation
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Generate architecture doc per part
- 💾 Consolidate all previous findings
- 📖 Follow architecture template structure
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: All previous step findings
- Focus: Architecture documentation generation
- Limits: Consolidation and writing only
- Dependencies: All analysis steps complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Generate Architecture Documentation

For each part in project_parts:

Fill in architecture sections:
- Executive Summary
- Technology Stack (from Step 7)
- Architecture Pattern (from Step 7)
- Data Architecture (from Step 8 data models scan)
- API Design (from Step 8 API scan if applicable)
- Component Overview (from Step 8 component scan)
- Source Tree (from Step 9)
- Development Workflow (from Step 10)
- Deployment Architecture (from Step 10)
- Testing Strategy (from test patterns)

### 2. Write Architecture Files

**If single part project:**
- Generate: `{output_folder}/architecture.md`

**If multi-part project:**
- Generate: `{output_folder}/architecture-{part_id}.md` for each part

### 3. Validate Each File

For each architecture file:
- Validate against architecture template schema
- Ensure all sections populated
- Update state with output

### 4. Log Completion

Output to stdout:
```
[step-12] ✓ Architecture documentation generated
[step-12]   Files created: {architecture_files_count}
[step-12]   Parts documented: {parts_count}
```

### 5. Update State

Update state file with:
- Add "step-12" to completed_steps
- Add architecture files to outputs_generated
- Set current_step = "step-13"

Output to stdout:
```
[step-12] ✓ Step 12 complete - proceeding to supporting docs
```

### 6. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Architecture doc per part generated
- All sections populated from previous steps
- Files written and validated
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write architecture files
- Missing critical findings from previous steps

### ⚠️ WARNING (Continue):

- Some sections have limited content

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
