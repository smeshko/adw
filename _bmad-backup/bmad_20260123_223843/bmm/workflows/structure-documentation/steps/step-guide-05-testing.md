---
name: 'step-guide-05-testing'
description: 'Guided creation of testing documentation section'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-05-testing.md'
nextStepFile: '{workflow_path}/steps/step-guide-06-product.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 5: Testing Section

## STEP GOAL:

To create the `docs/testing/` section for testing strategy and approach documentation.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Step-Specific Rules:

- 🎯 Focus ONLY on testing section
- 🚫 FORBIDDEN to create exhaustive documentation
- 💬 Ask 2 guiding questions maximum

## EXECUTION PROTOCOLS:

- 🎯 Create docs/testing/ folder structure
- 💾 Generate README.md and testing-strategy.md if user provides input
- 📖 Proceed to next step with 'S' or 'C' selection
- 🚫 FORBIDDEN to load next step until user selects menu option

## CONTEXT BOUNDARIES:

- Available context: Completed architecture, development, templates, and reference sections
- Focus: Testing strategy, approach, and framework documentation
- Limits: Keep testing docs high-level, not exhaustive test plans
- Dependencies: User input on testing approach and framework

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/testing/` folder exists.

### 2. Check for Existing Documentation

"**Testing Section**

Do you have existing testing documentation, or shall we create a brief testing strategy?

Options:
- Provide paths to existing test docs
- Answer: What testing approach do you use? (unit tests, integration, e2e, etc.)
- Say 'skip' to leave empty"

### 3. IF User Describes Testing Approach:

Ask one follow-up: "What's your test runner/framework? (jest, pytest, playwright, etc.)"

Generate `docs/testing/testing-strategy.md`:

```markdown
---
title: Testing Strategy
description: Testing approach and methodology
author: [user_name]
date: [current date]
---

# Testing Strategy

## Approach

[From user answer - e.g., "Unit tests for business logic, integration tests for APIs"]

## Test Framework

- **Framework:** [From answer]
- **Location:** `tests/` or `__tests__/`

## Running Tests

```bash
# Run all tests
[appropriate command based on framework]

# Run specific tests
[example command]
```

## Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| Unit | Individual functions | `tests/unit/` |
| Integration | Component interaction | `tests/integration/` |

## Coverage

<!-- TODO: Add coverage requirements and reporting -->
```

### 4. Create Section README

```markdown
---
title: Testing Documentation
description: Testing strategy and quality assurance
---

# Testing

Testing documentation and quality assurance guides.

## Documents

| Document | Description |
|----------|-------------|
| [testing-strategy.md](testing-strategy.md) | Testing approach |

## Related Sections

- [Development](../development/) - Setup guides
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

- docs/testing/ folder created
- README.md generated

### ❌ SYSTEM FAILURE:

- Creating exhaustive documentation
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
