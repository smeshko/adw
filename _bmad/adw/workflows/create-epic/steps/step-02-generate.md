---
name: 'step-02-generate'
description: 'Create all story files by invoking the existing create-story workflow for each story'

# Path Definitions
workflow_path: '{project-root}/.bmad/bmm/workflows/4-implementation/create-epic'

# File References
thisStepFile: '{workflow_path}/steps/step-02-generate.md'
nextStepFile: '{workflow_path}/steps/step-03-finalize.md'
workflowFile: '{workflow_path}/workflow.md'

# External Workflow Reference
createStoryWorkflow: '{project-root}/.bmad/bmm/workflows/4-implementation/create-story/workflow.yaml'

# Template References
# (No templates used in this step - delegates to create-story workflow)

# Task References
# (Uses createStoryWorkflow as sub-workflow invocation)
---

# Step 2: Generate Stories

## STEP GOAL:

To create all story files for the epic by sequentially invoking the existing `create-story` workflow for each story, handling errors gracefully by logging and continuing.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🤖 This is an AUTONOMOUS step - no user input required
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step when loop completes
- 📋 YOU ARE AN ORCHESTRATOR executing predefined automation

### Role Reinforcement:

- ✅ You are an autonomous orchestrator invoking sub-workflows
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ Invoke sub-workflows sequentially for each story
- ✅ You bring expertise in workflow orchestration and error handling
- ✅ Track success/failure for each story - never stop on individual failures

### Step-Specific Rules:

- 🎯 Focus ONLY on creating story files via create-story workflow
- 🚫 FORBIDDEN to manually write story content
- 🔄 MUST use the existing create-story workflow for each story
- ⚠️ On error: log the error, continue to next story (graceful degradation)
- 💬 Approach: Sequential sub-workflow invocation with comprehensive error tracking

## EXECUTION PROTOCOLS:

- 🎯 Loop through all stories from dependency analysis
- 🔄 Invoke create-story workflow for each
- 📝 Track which stories succeeded/failed
- 🚫 FORBIDDEN to stop on individual failures
- ✅ Proceed to step 3 when loop completes

## CONTEXT BOUNDARIES:

- Input: Story list and dependency graph from Step 1
- Available: create-story workflow at {createStoryWorkflow}
- Output: Story files created in sprint_artifacts folder
- Track: success_list, failure_list for summary

## EXECUTION SEQUENCE:

### 1. Initialize Tracking

Set up tracking variables:
```
stories_to_create = [list from step 1]
success_list = []
failure_list = []
current_index = 0
total_stories = len(stories_to_create)
```

### 2. Story Generation Loop

For each story in stories_to_create:

#### 2a. Display Progress

Display: `Creating story {current_index + 1}/{total_stories}: [{epic}.{story_num}] {story_title}...`

#### 2b. Invoke Create-Story Workflow

Invoke the existing create-story workflow with context:
- **Epic number**: {epic_number}
- **Story number**: {story_num}
- **Story title**: {story_title}
- **Acceptance criteria**: {acceptance_criteria from epics.md}

The create-story workflow will:
- Load its template
- Generate the story content
- Write the story file to sprint_artifacts folder

#### 2c. Handle Result

**IF success:**
- Add to success_list: `{epic}.{story_num}`
- Display: `✓ Story {epic}.{story_num} created`

**IF error:**
- Add to failure_list: `{epic}.{story_num}: {error_message}`
- Display: `✗ Story {epic}.{story_num} failed: {error_message}`
- **CONTINUE to next story** (do not stop)

#### 2d. Increment Counter

```
current_index += 1
```

### 3. Loop Completion Check

After processing all stories:

Display:
```
**Story Generation Complete**

- Total stories: {total_stories}
- Succeeded: {len(success_list)}
- Failed: {len(failure_list)}

Proceeding to finalization...
```

### 4. Store Results for Step 3

Ensure the following are available for step 3:
- `success_list`: Stories that were created successfully
- `failure_list`: Stories that failed with error messages
- `dependency_graph`: From step 1 (needed for dependency sections)
- `wave_assignments`: From step 1 (needed for flowchart)

### 5. Auto-Proceed to Next Step

**Proceeding to finalization...**

After loop completes, immediately load, read entire file, then execute {nextStepFile}.

---

## ERROR HANDLING NOTES:

### Common Errors to Handle:

1. **File write permission**: Log and continue
2. **Template not found**: Log and continue
3. **Invalid story data**: Log and continue
4. **Workflow invocation failure**: Log and continue

### Error Logging Format:

```
failure_list.append({
  "story": "{epic}.{story_num}",
  "title": "{story_title}",
  "error": "{error_message}",
  "timestamp": "{current_time}"
})
```

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All stories in the list were attempted
- create-story workflow invoked for each story
- Success/failure tracked for each story
- Results stored for step 3
- Proceeded to step 3 after loop

### ❌ SYSTEM FAILURE:

- Stopping on first error
- Not invoking create-story workflow
- Manually writing story content instead of using workflow
- Halting for user input
- Not tracking success/failure

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
