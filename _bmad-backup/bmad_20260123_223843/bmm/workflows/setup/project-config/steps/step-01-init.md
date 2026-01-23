---
name: 'step-01-init'
description: 'Initialize the project-config workflow by detecting existing config and routing appropriately'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/setup/project-config'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-scan.md'
continueFile: '{workflow_path}/steps/step-01b-continue.md'
workflowFile: '{workflow_path}/workflow.md'
configFile: '{project-root}/_bmad/project-config.yaml'
---

# Step 1: Workflow Initialization

## STEP GOAL:

To initialize the project-config workflow by detecting if an existing configuration file exists and routing to the appropriate next step.

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
- ✅ You bring project structure detection expertise, user brings their project knowledge
- ✅ Maintain helpful, concise wizard tone throughout

### Step-Specific Rules:

- 🎯 Focus ONLY on initialization and routing
- 🚫 FORBIDDEN to look ahead to future steps
- 💬 Handle initialization professionally
- 🚪 DETECT existing config state and handle continuation properly

## EXECUTION PROTOCOLS:

- 🎯 Show analysis before taking any action
- 📖 Check for existing config file
- 🚫 FORBIDDEN to load next step until routing is determined

## CONTEXT BOUNDARIES:

- Variables from workflow.md are available in memory
- Don't assume knowledge from other steps
- Config detection happens in this step

## INITIALIZATION SEQUENCE:

### 1. Check for Existing Config

First, check if the config file already exists:

- Look for file at `{project-root}/_bmad/project-config.yaml`
- If exists, read the complete file
- If not exists, this is a fresh configuration

### 2. Handle Existing Config (If Found)

If the config file exists:

- **STOP here** and load `{continueFile}` immediately
- Do not proceed with fresh setup
- Let step-01b handle the existing config logic

### 3. Fresh Setup (If No Config)

If no config file exists:

Display welcome message:

"Welcome to the Project Configuration Wizard!

I'll help you create a configuration file that enables the test, document, and ship workflows for your project.

This wizard will:
1. Scan your project to detect its type and existing tooling
2. Walk you through configuring each section (all optional except project basics)
3. Validate your commands work correctly
4. Save the configuration to `_bmad/project-config.yaml`

Let's get started!"

### 4. Present MENU OPTIONS

Display: **Proceeding to project scan...**

#### EXECUTION RULES:

- This is an initialization step with auto-proceed
- If config exists → route to step-01b-continue.md
- If no config → proceed to step-02-scan.md

#### Menu Handling Logic:

- IF config exists: Load, read entire file, then execute `{continueFile}`
- IF no config: After welcome message, immediately load, read entire file, then execute `{nextStepFile}` to begin project scanning

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Correctly detected presence/absence of existing config
- User welcomed to the process (if fresh setup)
- Proper routing to next step
- OR existing config properly routed to step-01b-continue.md

### ❌ SYSTEM FAILURE:

- Not checking for existing config properly
- Proceeding with scan when config exists
- Skipping welcome message for fresh setups
- Not routing to step-01b-continue.md when config exists

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN initialization and routing is determined, will you then immediately load, read entire file, then execute the appropriate next step file.
