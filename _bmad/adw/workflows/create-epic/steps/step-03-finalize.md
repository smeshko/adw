---
name: 'step-03-finalize'
description: 'Add dependency sections to stories and generate ASCII flowchart in epics.md'

# Path Definitions
workflow_path: '{project-root}/.bmad/bmm/workflows/4-implementation/create-epic'

# File References
thisStepFile: '{workflow_path}/steps/step-03-finalize.md'
workflowFile: '{workflow_path}/workflow.md'

# Input/Output Files
epicsFile: '{output_folder}/epics.md'
storyDir: '{sprint_artifacts}'

# Template References
# (Uses inline ASCII flowchart format - no external templates)

# Task References
# (No external tasks invoked - autonomous finalization)
---

# Step 3: Finalize - Dependencies & Flowchart

## STEP GOAL:

To append dependency sections to each successfully created story file and generate an ASCII flowchart showing parallelization opportunities, inserting it into epics.md under the relevant epic section.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🤖 This is an AUTONOMOUS step - no user input required
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Complete all finalization tasks before ending workflow
- 📋 YOU ARE AN ORCHESTRATOR executing predefined automation

### Role Reinforcement:

- ✅ You are an autonomous orchestrator and dependency analyst
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ Enrich story files with dependency information
- ✅ You bring expertise in dependency visualization and ASCII flowchart generation
- ✅ Provide comprehensive completion summary

### Step-Specific Rules:

- 🎯 Focus ONLY on adding dependencies and generating flowchart
- 🚫 FORBIDDEN to modify story content (only append Dependencies section)
- 📊 Use wave-based ASCII flowchart format as specified
- ✅ Display comprehensive completion summary at end
- 💬 Approach: Systematic enrichment and visualization of dependency data

## EXECUTION PROTOCOLS:

- 🎯 Loop through successfully created stories
- 📝 Append Dependencies section to each story file
- 📊 Generate ASCII flowchart from wave assignments
- 📄 Insert flowchart into epics.md
- ✅ Display final summary and end workflow

## CONTEXT BOUNDARIES:

- Input: success_list, failure_list, dependency_graph, wave_assignments from previous steps
- Output: Updated story files, updated epics.md with flowchart
- Final: Completion summary displayed to user

## EXECUTION SEQUENCE:

### 1. Add Dependencies to Story Files

For each story in success_list:

#### 1a. Load Story File

Load the story file from {storyDir}/{epic_number}-{story_num}.md

#### 1b. Build Dependencies Section

Using the dependency_graph from step 1, create the Dependencies section:

```markdown
## Dependencies

- **Depends On:** {comma-separated list of stories this depends on, or "None"}
- **Blocks:** {comma-separated list of stories this blocks, or "None"}
- **Can Parallel With:** {comma-separated list of parallel stories, or "None"}

### Dependency Rationale
{For each dependency, one concise line explaining why}
```

**Example:**
```markdown
## Dependencies

- **Depends On:** Story 2.1, Story 2.3
- **Blocks:** Story 2.5
- **Can Parallel With:** Story 2.2, Story 2.4

### Dependency Rationale
- Story 2.1: Requires user authentication model
- Story 2.3: Needs API endpoint definitions
```

#### 1c. Append to Story File

Append the Dependencies section to the end of the story file.

#### 1d. Log Progress

Display: `✓ Dependencies added to Story {epic}.{story_num}`

### 2. Generate ASCII Flowchart

Using wave_assignments from step 1, generate the flowchart:

#### 2a. Flowchart Format

Use the wave-based box format:

```
## Epic {epic_number}: Dependency Flowchart

╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [{epic}-1] Story Title                                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After {epic}-1 (PARALLEL)                                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [{epic}-2] Story A          ║     [{epic}-3] Story B             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

#### 2b. Flowchart Design Rules

- Use double-line box characters: ╔ ╗ ╚ ╝ ═ ║
- Group parallel stories in same WAVE box
- Label waves with dependencies (e.g., "After 2-1")
- Note parallel count when >2 stories (e.g., "PARALLEL x6")
- Use │ and ▼ for flow connections between waves
- Split into parallel tracks (side-by-side boxes) when dependency chains diverge
- Story format: [{Epic}-{Story}] Story Title

#### 2c. Handle Complex Dependencies

If stories have diverging dependency chains (like the example with Track A and Track B):
- Create side-by-side wave boxes
- Show which track each story belongs to
- Connect tracks when they merge

### 3. Insert Flowchart into epics.md

#### 3a. Load epics.md

Load {epicsFile}

#### 3b. Find Epic Section

Locate the section for Epic {epic_number}

#### 3c. Insert Flowchart

Insert the flowchart after the epic's story list, before the next epic or end of file.

If a flowchart already exists for this epic, replace it.

#### 3d. Save epics.md

Write the updated epics.md file.

Display: `✓ Flowchart added to epics.md`

### 4. Display Completion Summary

Display the final summary:

```
═══════════════════════════════════════════════════════════════════
                    EPIC {epic_number} CREATION COMPLETE
═══════════════════════════════════════════════════════════════════

**Stories Created:** {len(success_list)}/{total_stories}
{for each success: ✓ [{epic}.{num}] {title}}

**Failed Stories:** {len(failure_list)}
{for each failure: ✗ [{epic}.{num}] {title} - {error}}

**Outputs:**
- Story files: {storyDir}/{epic_number}-*.md
- Flowchart: {epicsFile} (under Epic {epic_number})

**Execution Waves:**
- Wave 1: {wave_1_count} stories (start immediately)
- Wave 2: {wave_2_count} stories
...

═══════════════════════════════════════════════════════════════════
```

### 5. End Workflow

Workflow complete. No further steps.

## CRITICAL STEP COMPLETION NOTE

This is the FINAL step of the create-epic workflow. Upon completion:
- All story files have been created (or failures logged)
- Dependency sections appended to successful story files
- ASCII flowchart inserted into epics.md
- Completion summary displayed to user

The workflow ends here. No further steps to execute.

---

## DEPENDENCIES SECTION FORMAT REFERENCE:

```markdown
## Dependencies

- **Depends On:** Story X.Y, Story X.Z
- **Blocks:** Story X.W
- **Can Parallel With:** Story X.A, Story X.B

### Dependency Rationale
- Story X.Y: [concise reason - 1 line max]
- Story X.Z: [concise reason - 1 line max]
```

**Rules:**
- Only include non-empty fields (omit "Blocks" if none)
- Rationale must be concise (one line per dependency)
- Use "None" if a category is empty but include for clarity

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Dependencies added to all successful story files
- ASCII flowchart generated in correct format
- Flowchart inserted into epics.md
- Completion summary displayed
- Workflow ended cleanly

### ❌ SYSTEM FAILURE:

- Modifying story content beyond adding Dependencies section
- Not using the specified flowchart format
- Not inserting flowchart into epics.md
- Missing completion summary
- Not reporting failures

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
