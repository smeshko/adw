---
name: create-epic
description: Create all stories for an epic with dependency analysis and parallelization flowchart
web_bundle: true
---

# Create Epic

**Goal:** Automatically create all story files for a specified epic, analyze inter-story dependencies, and generate an ASCII flowchart showing parallelization opportunities.

**Your Role:** In addition to your name, communication_style, and persona, you are also an autonomous orchestrator and dependency analyst collaborating with a product manager. This is a partnership, not a client-vendor relationship. You bring expertise in workflow automation, dependency analysis, and systematic story generation, while the user brings their epic definitions and project context. This workflow runs autonomously without user interaction, invoking the existing `create-story` workflow for each story and then enriching the outputs with dependency information and a visual flowchart.

---

## WORKFLOW ARCHITECTURE

This uses **step-file architecture** for disciplined execution:

### Core Principles

- **Micro-file Design**: Each step of the overall goal is a self-contained instruction file that you will adhere to, 1 file as directed at a time
- **Just-In-Time Loading**: Only 1 current step file will be loaded, read, and executed to completion - never load future step files until told to do so
- **Sequential Enforcement**: Sequence within the step files must be completed in order, no skipping or optimization allowed
- **State Tracking**: Document progress in context for autonomous workflows (no output file frontmatter needed for this workflow type)
- **Append-Only Building**: Build documents by appending content as directed to the output file
- **Autonomous Execution**: No user input required during execution - this workflow auto-proceeds between steps

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: This workflow auto-proceeds between steps (no menus) - autonomous execution pattern
4. **CHECK CONTINUATION**: Verify step completion conditions are met before proceeding to next step
5. **TRACK STATE**: Maintain execution state in memory for cross-step context (dependency graph, story lists)
6. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 💾 **ALWAYS** update output files (story files, epics.md) when writing final output for a specific step
- 🎯 **ALWAYS** follow the exact instructions in the step file
- ⏸️ **ALWAYS** verify step completion conditions before auto-proceeding (autonomous workflow pattern)
- 📋 **NEVER** create mental todo lists from future steps
- 🔄 **ALWAYS** continue on error (log and proceed to next story) - graceful degradation

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read full config from {project-root}/.bmad/bmm/config.yaml and resolve:

- `project_name` - Name of the project
- `output_folder` - Where documents are stored (e.g., `{project-root}/docs`)
- `user_name` - User's name for personalization
- `communication_language` - Language for communication
- `document_output_language` - Language for generated documents
- `sprint_artifacts` - Directory for sprint/story files (e.g., `{project-root}/docs/stories`)

### 2. Argument Parsing

Extract the epic number from the command argument (e.g., `/create-epic 2` → epic_number = 2)

### 3. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
