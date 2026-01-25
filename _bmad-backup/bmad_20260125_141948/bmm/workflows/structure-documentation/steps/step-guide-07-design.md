---
name: 'step-guide-07-design'
description: 'Guided creation of design documentation section (UI projects only)'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-07-design.md'
nextStepFile: '{workflow_path}/steps/step-guide-08-finalize.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 7: Design Section

## STEP GOAL:

To create the `docs/design/` section for UI/UX documentation, but only if the project has a user interface.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Step-Specific Rules:

- 🎯 First determine if this is a UI project
- 🚫 FORBIDDEN to create design docs for non-UI projects
- 💬 Ask about UI presence before proceeding

## EXECUTION PROTOCOLS:

- 🎯 Determine if project has UI before creating section
- 💾 Create docs/design/ folder only for UI projects
- 📖 Generate README.md and design-system.md if applicable
- 🚫 FORBIDDEN to load next step until user selects menu option

## CONTEXT BOUNDARIES:

- Available context: Completed architecture, development, templates, reference, testing, and product sections
- Focus: UI/UX documentation for projects with user interfaces
- Limits: Skip entirely for non-UI projects (APIs, CLIs, libraries)
- Dependencies: User confirmation of UI project type

## GUIDED SEQUENCE:

### 1. Determine if UI Project

"**Design Section**

This section is for UI/UX documentation (design systems, component libraries, wireframes).

**Is this a UI project?** (web app, mobile app, desktop app with user interface)

- Yes → We'll create a design section
- No → We'll skip this section (APIs, CLIs, libraries don't need this)"

### 2. IF NOT a UI Project:

"Got it! This project doesn't need a design section. Moving on..."

Create empty placeholder and proceed.

### 3. IF UI Project - Create Section Folder

Ensure `docs/design/` folder exists.

### 4. Check for Existing Design Docs

"Do you have existing design documentation?

Options:
- Provide paths to existing design docs, style guides, or Figma links
- Answer: What's your primary UI framework/library? (React, Vue, SwiftUI, etc.)
- Say 'skip' to leave empty"

### 5. IF User Describes UI:

Generate `docs/design/design-system.md`:

```markdown
---
title: Design System
description: UI components and design tokens
author: [user_name]
date: [current date]
---

# Design System

## Framework

**Primary:** [From user answer]

## Design Tokens

### Colors

<!-- TODO: Define color palette -->

### Typography

<!-- TODO: Define font scales -->

### Spacing

<!-- TODO: Define spacing scale -->

## Components

<!-- TODO: Document component library -->

## Patterns

<!-- TODO: Document common UI patterns -->
```

### 6. Create Section README

```markdown
---
title: Design Documentation
description: UI/UX design system and specifications
---

# Design

Design documentation for the user interface.

## Documents

| Document | Description |
|----------|-------------|
| [design-system.md](design-system.md) | Design tokens and components |

## Resources

- Screenshots: `screenshots/`
- Mockups: [Link to Figma/design tool]

## Related Sections

- [Product](../product/) - Requirements
- [Templates](../templates/) - Component templates
```

### 7. Present MENU OPTIONS

Display: **Select an Option:** [A] Advanced Elicitation [S] Skip [C] Continue

#### Menu Handling Logic:

- IF A: Execute {advancedElicitationTask} to refine content, then return to menu
- IF S: Create empty folder with placeholder README, then load, read entire file, then execute {nextStepFile}
- IF C: Ensure section is complete, then load, read entire file, then execute {nextStepFile}
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#7-present-menu-options)

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'S' or 'C'
- After Advanced Elicitation execution, return to this menu

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user selects [S] or [C] will you load and execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Asked about UI project first
- Created design section only if applicable
- README.md generated

### ❌ SYSTEM FAILURE:

- Creating design docs for non-UI projects
- Not asking about UI presence
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
