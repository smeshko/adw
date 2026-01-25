---
name: 'step-guide-04-reference'
description: 'Guided creation of reference documentation section'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-04-reference.md'
nextStepFile: '{workflow_path}/steps/step-guide-05-testing.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 4: Reference Section

## STEP GOAL:

To create the `docs/reference/` section for data models, API contracts, and service catalogs.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Step-Specific Rules:

- 🎯 Focus ONLY on reference section
- 🚫 FORBIDDEN to create exhaustive documentation
- 💬 Ask 2-3 guiding questions maximum
- 🚪 Allow skip to create empty placeholder

## EXECUTION PROTOCOLS:

- 🎯 Create docs/reference/ folder structure
- 💾 Generate README.md and primary doc if user provides input
- 📖 Proceed to next step with 'S' or 'C' selection
- 🚫 FORBIDDEN to load next step until user selects menu option

## CONTEXT BOUNDARIES:

- Available context: Completed architecture, development, and templates sections
- Focus: Data models, API contracts, service catalogs
- Limits: Keep reference docs concise, not exhaustive
- Dependencies: User input on existing docs or data model description

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/reference/` folder exists.

### 2. Check for Existing Documentation

"**Reference Section**

This section is for technical reference documentation:
- Data models and entities
- API contracts and endpoints
- Service catalog

Do you have existing reference documentation, or shall we create a starting point?

Options:
- Provide paths to existing docs
- Tell me about your main data models (1-2 sentences)
- Say 'skip' to leave empty"

### 3a. IF Existing Docs Provided:

- Read and reorganize into `docs/reference/`
- Standard files: data-models.md, api-contracts.md, services-catalog.md

### 3b. IF User Describes Data Models:

Generate concise `docs/reference/data-models.md`:

```markdown
---
title: Data Models
description: Core entities and data structures
author: [user_name]
date: [current date]
---

# Data Models

## Core Entities

[Based on user description - brief outline]

## Entity Relationships

<!-- TODO: Add entity relationship details -->

## DTOs and Contracts

<!-- TODO: Document data transfer objects -->
```

### 4. Create Section README

```markdown
---
title: Reference Documentation
description: Technical reference for data models, APIs, and services
---

# Reference

Technical reference documentation for the project.

## Documents

| Document | Description |
|----------|-------------|
| [data-models.md](data-models.md) | Core entities and data structures |

## Related Sections

- [Architecture](../architecture/) - System design
- [Templates](../templates/) - Component patterns
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

- docs/reference/ folder created
- README.md generated

### ❌ SYSTEM FAILURE:

- Creating exhaustive documentation
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
