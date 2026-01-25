---
name: 'step-guide-01-architecture'
description: 'Guided creation of architecture documentation section'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-01-architecture.md'
nextStepFile: '{workflow_path}/steps/step-guide-02-development.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 1: Architecture Section

## STEP GOAL:

To create the `docs/architecture/` section by either reorganizing existing architecture documentation or collaboratively creating an architecture overview through guided questions.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a documentation architect
- ✅ We engage in collaborative dialogue, not command-response
- ✅ Keep questions concise - this is not comprehensive, just enough to start

### Step-Specific Rules:

- 🎯 Focus ONLY on architecture section
- 🚫 FORBIDDEN to create exhaustive documentation
- 💬 Ask 2-3 guiding questions maximum
- 🚪 Allow skip to create empty placeholder

## EXECUTION PROTOCOLS:

- 🎯 Create docs/architecture/ folder
- 💾 Generate README.md and primary doc
- 📖 Proceed to next step with 'C' selection
- 🚫 FORBIDDEN to load next step until user selects 'S' or 'C'

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/architecture/` folder exists.

### 2. Check for Existing Documentation

"**Architecture Section**

Do you have existing architecture documentation I should organize?

This could be:
- ARCHITECTURE.md in your root
- Design documents
- System diagrams
- ADR (Architecture Decision Records)

Please provide the path(s), or say 'no' if starting fresh."

### 3a. IF Existing Docs Provided:

- Read the provided files
- Move/copy to `docs/architecture/`
- Rename to standard naming (overview.md, technical-architecture.md)
- Create README.md listing the documents

"I've organized your architecture docs:
- [List of files moved/created]

Ready to continue to the next section?"

### 3b. IF No Existing Docs (Create New):

Ask focused guiding questions (2-3 max):

"Let's create a basic architecture overview. Quick questions:

1. **What type of system is this?** (web app, API, CLI tool, library, mobile app, etc.)

2. **What are the 2-3 main components?** (e.g., frontend, backend API, database)

3. **Any key technologies to highlight?** (e.g., React, Node.js, PostgreSQL)"

Based on answers, generate a concise `docs/architecture/overview.md`:

```markdown
---
title: Architecture Overview
description: System architecture for [project]
author: [user_name]
date: [current date]
---

# Architecture Overview

## System Type
[From answer 1]

## Key Components
[From answer 2 - brief bullet points]

## Technology Stack
[From answer 3 - brief list]

## Further Documentation
- See `technical-architecture.md` for detailed patterns (TODO)
- See `adrs/` for architecture decisions (TODO)
```

### 4. Create Section README

Generate `docs/architecture/README.md` using template:

```markdown
---
title: Architecture Documentation
description: System architecture and design documentation
---

# Architecture

This section contains architecture and design documentation.

## Documents

| Document | Description |
|----------|-------------|
| [overview.md](overview.md) | High-level system architecture |

## Related Sections

- [Development](../development/) - Implementation guides
- [Reference](../reference/) - Technical specifications
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

#### Skip Behavior:

If user selects [S], create placeholder:
```markdown
# Architecture

This section intentionally left empty.

[Return to Documentation Hub](../README.md)
```

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user selects [S] or [C] will you load and execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- docs/architecture/ folder created
- Either existing docs reorganized OR new overview created
- README.md generated for section
- Menu presented and user selection handled

### ❌ SYSTEM FAILURE:

- Creating exhaustive documentation
- Asking more than 3 questions
- Proceeding without user selection
- Not creating the folder structure

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
