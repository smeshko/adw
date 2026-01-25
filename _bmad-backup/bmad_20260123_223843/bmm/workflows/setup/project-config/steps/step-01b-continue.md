---
name: 'step-01b-continue'
description: 'Handle existing project configuration - add, modify, or reconfigure'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/setup/project-config'

# File References
thisStepFile: '{workflow_path}/steps/step-01b-continue.md'
scanStepFile: '{workflow_path}/steps/step-02-scan.md'
configureStepFile: '{workflow_path}/steps/step-03-configure.md'
workflowFile: '{workflow_path}/workflow.md'
configFile: '{project-root}/_bmad/project-config.yaml'
---

# Step 1B: Handle Existing Configuration

## STEP GOAL:

To handle an existing project configuration file by offering options to add missing sections, modify existing sections, or perform a full reconfiguration.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step, ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a project configuration specialist
- ✅ If you already have been given a name, communication_style and identity, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring configuration expertise, user brings their project knowledge
- ✅ Maintain helpful, concise wizard tone throughout

### Step-Specific Rules:

- 🎯 Focus ONLY on analyzing existing config and presenting options
- 🚫 FORBIDDEN to modify config without user consent
- 💬 Present options clearly
- 🚪 DETECT what sections exist and what's missing

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis of current config before taking action
- 💾 Keep existing config values intact unless user requests changes
- 📖 Review the existing config structure
- 🚫 FORBIDDEN to modify config without user approval

## CONTEXT BOUNDARIES:

- Existing config file is loaded
- Previous context = current config contents
- Focus on understanding what exists vs what's missing

## CONTINUATION SEQUENCE:

### 1. Analyze Current Config

Read and parse `{configFile}` to understand:

- **project section**: Is it defined? What values?
- **test section**: Is it defined? What commands?
- **document section**: Is it defined? What settings?
- **ship section**: Is it defined? What configuration?

### 2. Present Current State

Display a summary:

"I found an existing project configuration at `_bmad/project-config.yaml`.

**Current Configuration:**

| Section | Status | Summary |
|---------|--------|---------|
| project | [Configured/Missing] | [name, type if exists] |
| test | [Configured/Missing] | [X commands if exists] |
| document | [Configured/Missing] | [settings summary if exists] |
| ship | [Configured/Missing] | [type if exists] |"

### 3. Identify Missing Sections

List any sections that are not configured:

"**Missing Sections:** [list or 'None - all sections configured']"

### 4. Present Options

Display menu based on state:

"**How would you like to proceed?**

[A] **Add** - Add configuration for missing sections only
[M] **Modify** - Update existing section configurations
[R] **Reconfigure** - Start fresh with a full project rescan
[X] **Exit** - Keep current config unchanged"

### 5. Handle User Choice

#### IF A (Add):
- If no missing sections: "All sections are already configured. Would you like to Modify or Reconfigure instead?"
- If missing sections exist: Note which sections to configure, then load `{configureStepFile}` with context that only missing sections should be configured

#### IF M (Modify):
- Ask: "Which section would you like to modify? [project/test/document/ship]"
- Note the section to modify, then load `{configureStepFile}` with context to modify that section

#### IF R (Reconfigure):
- Warn: "This will rescan your project and rebuild the configuration. Your current settings will be replaced."
- Confirm: "Proceed with full reconfiguration? [Y/N]"
- If Y: Load `{scanStepFile}` for fresh scan
- If N: Redisplay menu

#### IF X (Exit):
- Display: "Configuration unchanged. Your current `_bmad/project-config.yaml` remains active."
- End workflow

### 6. Present MENU OPTIONS

Display: **Select an Option:** [A] Add [M] Modify [R] Reconfigure [X] Exit

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- Handle each option as described above
- User can chat or ask questions - always respond and then redisplay menu

#### Menu Handling Logic:

- IF A: Set context for adding missing sections, load `{configureStepFile}`
- IF M: Ask which section, set context for modifying, load `{configureStepFile}`
- IF R: Confirm, then load `{scanStepFile}` for full rescan
- IF X: End workflow gracefully
- IF Any other comments or queries: help user respond then redisplay menu

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Correctly analyzed existing config structure
- Presented clear summary of current state
- User made informed choice about how to proceed
- Appropriate next step loaded based on choice

### ❌ SYSTEM FAILURE:

- Not analyzing existing config properly
- Modifying config without user consent
- Loading wrong next step for user's choice
- Proceeding without user confirmation

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user has made a choice and confirmed will you load the appropriate next step file or end the workflow.
