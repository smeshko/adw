---
name: 'step-guide-06-product'
description: 'Guided creation of product documentation section'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-06-product.md'
nextStepFile: '{workflow_path}/steps/step-guide-07-design.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 6: Product Section

## STEP GOAL:

To create the `docs/product/` section for product requirements and specifications.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Step-Specific Rules:

- 🎯 Focus ONLY on product section
- 🚫 FORBIDDEN to create exhaustive documentation
- 💬 Ask 1-2 guiding questions maximum

## EXECUTION PROTOCOLS:

- 🎯 Create docs/product/ folder structure
- 💾 Generate README.md and prd.md if user provides input
- 📖 Proceed to next step with 'S' or 'C' selection
- 🚫 FORBIDDEN to load next step until user selects menu option

## CONTEXT BOUNDARIES:

- Available context: Completed architecture, development, templates, reference, and testing sections
- Focus: Product requirements, PRDs, and specifications
- Limits: Keep product docs as starting points, not comprehensive PRDs
- Dependencies: User input on product description or existing PRD paths

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/product/` folder exists.

### 2. Check for Existing Documentation

"**Product Section**

This section is for product requirements, PRDs, and specifications.

Do you have existing product documentation?

Options:
- Provide paths to existing PRD or requirements docs
- Tell me in one sentence what this product does
- Say 'skip' to leave empty"

### 3. IF User Describes Product:

Generate `docs/product/prd.md`:

```markdown
---
title: Product Requirements
description: Product requirements document
author: [user_name]
date: [current date]
---

# Product Requirements Document

## Overview

[From user description]

## Problem Statement

<!-- TODO: Define the problem being solved -->

## Goals

<!-- TODO: List primary goals -->

## Non-Goals

<!-- TODO: What is explicitly out of scope -->

## User Stories

<!-- TODO: Add user stories -->

## Success Metrics

<!-- TODO: Define how success is measured -->
```

### 4. Create Section README

```markdown
---
title: Product Documentation
description: Product requirements and specifications
---

# Product

Product documentation including requirements and specifications.

## Documents

| Document | Description |
|----------|-------------|
| [prd.md](prd.md) | Product requirements |

## Related Sections

- [Architecture](../architecture/) - Technical design
- [Design](../design/) - UX/UI specifications
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

- docs/product/ folder created
- README.md generated

### ❌ SYSTEM FAILURE:

- Creating exhaustive documentation
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
