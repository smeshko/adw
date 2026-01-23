---
name: 'step-01-init'
description: 'Load the specified epic and analyze story dependencies'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/create-epic'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-generate.md'
workflowFile: '{workflow_path}/workflow.md'

# Input/Output Files
epicsFile: '{output_folder}/epics.md'
createStoryWorkflow: '{project-root}/_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml'

# Template References
# (No templates used in this initialization step)

# Task References
# (No external tasks invoked in this step - autonomous execution)
---

# Step 1: Initialize & Analyze Dependencies

## STEP GOAL:

To load the specified epic from epics.md, identify all stories within it, and analyze dependencies between stories using AI-driven inference to build a dependency graph.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🤖 This is an AUTONOMOUS step - no user input required
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step when completion conditions are met
- 📋 YOU ARE AN ORCHESTRATOR executing predefined automation

### Role Reinforcement:

- ✅ You are an autonomous orchestrator and dependency analyst
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ Execute systematically without user interaction
- ✅ You bring expertise in dependency analysis and workflow automation
- ✅ Log progress for the final summary

### Step-Specific Rules:

- 🎯 Focus ONLY on loading epic and analyzing dependencies
- 🚫 FORBIDDEN to create any story files in this step
- 📊 Build the complete dependency graph before proceeding
- ⚠️ If epic not found, report error and end workflow
- 💬 Approach: Systematic parsing and AI-driven dependency inference

## EXECUTION PROTOCOLS:

- 🎯 Parse epic number from command argument
- 📖 Load and parse epics.md
- 🔍 Extract all stories for the specified epic
- 🧠 Analyze dependencies using AI inference
- 💾 Store dependency graph in memory for next steps
- 🚫 FORBIDDEN to proceed if epic not found

## CONTEXT BOUNDARIES:

- Input: Epic number from command argument
- Available: epics.md file
- Output: Dependency graph in memory, list of stories to create
- No output files created in this step

## EXECUTION SEQUENCE:

### 1. Parse Epic Number

Extract the epic number from the command argument:
- Expected format: `/create-epic N` where N is the epic number
- Store as `epic_number` variable
- If no argument provided, report error and end workflow

### 2. Load Epics File

Load {epicsFile} and parse its contents:
- Locate the section for Epic {epic_number}
- Extract all stories defined under this epic
- For each story, capture:
  - Story number (e.g., 2.1, 2.2)
  - Story title
  - Acceptance criteria
  - Any existing notes or context

### 3. Validate Epic Exists

Check if the epic was found:
- IF epic not found:
  - Display: "**Error:** Epic {epic_number} not found in epics.md"
  - End workflow
- IF epic found but has no stories:
  - Display: "**Error:** Epic {epic_number} has no stories defined"
  - End workflow

### 4. Analyze Story Dependencies

For each story in the epic, analyze dependencies using AI inference:

**Dependency Detection Criteria:**
- **Data Dependencies**: Story B needs data/models created by Story A
- **API Dependencies**: Story B uses endpoints/interfaces from Story A
- **UI Dependencies**: Story B builds on UI components from Story A
- **Sequential Logic**: Story B's feature only makes sense after Story A exists
- **Shared Resources**: Stories that modify the same files/components

**For each story, determine:**
- Which other stories it depends on (must complete first)
- Which stories depend on it (it blocks)
- Which stories can run in parallel (no dependencies)

**Build Dependency Graph:**
```
dependency_graph = {
  "{epic}.1": {
    "depends_on": [],
    "blocks": ["{epic}.2", "{epic}.3"],
    "parallel_with": [],
    "rationale": {
      "{epic}.2": "Requires authentication setup",
      "{epic}.3": "Needs user model defined"
    }
  },
  ...
}
```

### 5. Calculate Execution Waves

Group stories into waves based on dependencies:
- **Wave 1**: Stories with no dependencies (can start immediately)
- **Wave 2**: Stories that depend only on Wave 1 stories
- **Wave N**: Stories that depend on Wave N-1 or earlier

Store wave assignments for flowchart generation.

### 6. Display Analysis Summary

Display a brief summary:
```
**Epic {epic_number} Analysis Complete**

- Stories found: {count}
- Execution waves: {wave_count}
- Wave 1 (start immediately): {wave_1_stories}

Proceeding to story generation...
```

### 7. Auto-Proceed to Next Step

**Proceeding to story generation...**

After analysis is complete, immediately load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Epic number parsed from argument
- Epic found in epics.md
- All stories identified and extracted
- Dependencies analyzed for each story
- Dependency graph built in memory
- Wave assignments calculated
- Ready to proceed to step 2

### ❌ SYSTEM FAILURE:

- No epic number provided
- Epic not found in epics.md
- Failed to parse epics.md
- Halting for user input (this is autonomous)
- Creating files in this step

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
