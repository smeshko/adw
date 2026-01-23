---
name: 'step-guide-02-development'
description: 'Guided creation of development documentation section'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-02-development.md'
nextStepFile: '{workflow_path}/steps/step-guide-03-templates.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'
gettingStartedTemplate: '{workflow_path}/templates/getting-started.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 2: Development Section

## STEP GOAL:

To create the `docs/development/` section by either reorganizing existing development documentation or collaboratively creating getting-started and deployment guides.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a documentation architect
- ✅ Keep questions concise - 2-3 max
- ✅ Focus on getting-started as the priority document

### Step-Specific Rules:

- 🎯 Focus ONLY on development section
- 🚫 FORBIDDEN to create exhaustive documentation
- 💬 Prioritize getting-started.md
- 🚪 Allow skip to create empty placeholder

## EXECUTION PROTOCOLS:

- 🎯 Create docs/development/ folder structure
- 💾 Generate README.md and getting-started.md if user provides input
- 📖 Proceed to next step with 'S' or 'C' selection
- 🚫 FORBIDDEN to load next step until user selects menu option

## CONTEXT BOUNDARIES:

- Available context: Completed architecture section from previous step
- Focus: Developer setup, installation, and getting started guides
- Limits: Keep development docs practical, not exhaustive
- Dependencies: User input on existing docs or setup instructions

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/development/` folder exists.

### 2. Check for Existing Documentation

"**Development Section**

Do you have existing development/setup documentation?

This could be:
- CONTRIBUTING.md
- Setup guides
- Installation instructions
- Deployment docs

Please provide the path(s), or say 'no' if starting fresh."

### 3a. IF Existing Docs Provided:

- Read the provided files
- Move/copy to `docs/development/`
- Rename to standard naming (getting-started.md, deployment.md, troubleshooting.md)
- Create README.md listing the documents

### 3b. IF No Existing Docs (Create New):

"Let's create a getting-started guide. Quick questions:

1. **How do developers install/setup?** (e.g., npm install, pip install, docker-compose up)

2. **What prerequisites are needed?** (e.g., Node 18+, Python 3.9+, Docker)

3. **How do they run the project locally?** (e.g., npm run dev, python main.py)"

Generate `docs/development/getting-started.md`:

```markdown
---
title: Getting Started
description: Developer setup guide
author: [user_name]
date: [current date]
---

# Getting Started

## Prerequisites

[From answer 2]

## Installation

[From answer 1]

## Running Locally

[From answer 3]

## Common Issues

<!-- TODO: Add common issues as they arise -->

## Next Steps

- See [deployment.md](deployment.md) for deployment procedures (TODO)
- See [troubleshooting.md](troubleshooting.md) for issue resolution (TODO)
```

### 4. Create Section README

Generate `docs/development/README.md`:

```markdown
---
title: Development Documentation
description: Guides for developers working on this project
---

# Development

This section contains guides for setting up and working with the project.

## Documents

| Document | Description |
|----------|-------------|
| [getting-started.md](getting-started.md) | Setup and installation guide |

## Related Sections

- [Architecture](../architecture/) - System design
- [Testing](../testing/) - Testing strategies
```

### 5. Present MENU OPTIONS

Display: **Select an Option:** [A] Advanced Elicitation [S] Skip [C] Continue

#### Menu Handling Logic:

- IF A: Execute {advancedElicitationTask} to refine content, then return to menu
- IF S: Create empty folder with placeholder README, then load, read entire file, then execute {nextStepFile}
- IF C: Ensure section is complete, then load, read entire file, then execute {nextStepFile}
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#5-present-menu-options)

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'S' or 'C'
- After Advanced Elicitation execution, return to this menu

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user selects [S] or [C] will you load and execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- docs/development/ folder created
- getting-started.md created or existing docs organized
- README.md generated for section

### ❌ SYSTEM FAILURE:

- Creating exhaustive documentation
- Asking more than 3 questions
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
