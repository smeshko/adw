---
name: 'step-guide-03-templates'
description: 'Guided creation of component templates from code analysis'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-03-templates.md'
nextStepFile: '{workflow_path}/steps/step-guide-04-reference.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'
templateFileTemplate: '{workflow_path}/templates/template-file.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 3: Templates Section

## STEP GOAL:

To create the `docs/templates/` section by analyzing code files provided by the user and generating component templates that document patterns for creating similar components.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a documentation architect with code analysis expertise
- ✅ Analyze provided code files to extract patterns
- ✅ Use Advanced Elicitation to understand code patterns deeply

### Step-Specific Rules:

- 🎯 Focus ONLY on templates section
- 🚫 FORBIDDEN to create templates without analyzing real code
- 💬 User provides code file paths, you analyze and generate templates
- 🔄 Can create multiple templates in a loop until user is done

## GUIDED SEQUENCE:

### 1. Create Section Folder

Ensure `docs/templates/` folder exists.

### 2. Introduce Template Creation

"**Templates Section**

Templates help developers create new components by documenting existing patterns.

I'll analyze code files you provide and generate template documentation showing:
- When to use the pattern
- Directory structure
- Code examples with placeholders
- Integration steps

**Do you want to create component templates?**

If yes, provide a path to a code file you'd like to templatize (e.g., `src/services/EmailService.ts`, `app/models/user.py`)

Or say 'skip' to create an empty templates section."

### 3. Template Creation Loop

For each code file provided:

#### 3a. Analyze the Code File

Read the provided file and analyze:
- Component type (service, model, controller, repository, etc.)
- Key patterns used
- Dependencies and integrations
- Naming conventions
- Structure and organization

#### 3b. Generate Template Document

Using {templateFileTemplate} as structure, create a template doc:

```markdown
---
title: [Component Type] Template
description: Template for creating [component type] components
author: [user_name]
date: [current date]
---

# [Component Type] Template

## When to Use

- [Bullet points derived from code analysis]

## Quick Reference

| Aspect | Value |
|--------|-------|
| Location | `[path pattern]` |
| Pattern | [pattern name] |
| Naming | `{Name}[Component].ext` |

## Directory Structure

[If applicable, show folder structure]

## Code Template

```[language]
// Copy this template and replace {Placeholders}

[Extracted code pattern with placeholders replacing specific names]
```

## Existing Patterns

Reference implementations in the codebase:
- [Link to the analyzed file]

## Integrations

[Steps to integrate: registration, config, dependencies]

## Checklist

- [ ] Created file with correct naming
- [ ] Implemented required methods
- [ ] Added to registration/config
- [ ] Added tests

## References

- [Links to related templates]
```

#### 3c. Confirm and Offer More

"I've created `docs/templates/[component-type]-template.md` based on `[file path]`.

**Want to create another template?**
Provide another code file path, or select from the menu below."

### 4. Create Section README

After template loop completes, generate `docs/templates/README.md`:

```markdown
---
title: Component Templates
description: Templates for creating new components
---

# Templates

This section contains templates for creating new components in the project.

## Available Templates

| Template | Description |
|----------|-------------|
[List generated templates]

## How to Use

1. Find the template matching your component type
2. Copy the code template section
3. Replace `{Placeholders}` with your specific values
4. Follow the integration checklist

## Related Sections

- [Architecture](../architecture/) - System patterns
- [Reference](../reference/) - API and data models
```

### 5. Present MENU OPTIONS

Display: **Select an Option:** [A] Advanced Elicitation [S] Skip [C] Continue

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- Advanced Elicitation helps analyze code patterns more deeply
- ONLY proceed to next step when user selects 'S' or 'C'

#### Menu Handling Logic:

- IF A: Execute {advancedElicitationTask} to explore code patterns, then return to menu
- IF S: Create empty folder with placeholder README, then load, read entire file, then execute {nextStepFile}
- IF C: Ensure section is complete, then load, read entire file, then execute {nextStepFile}
- IF user provides a file path: Analyze and create template, then return to menu
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#5-present-menu-options)

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user selects [S] or [C] will you load and execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- docs/templates/ folder created
- Templates generated from actual code analysis
- Each template follows the template-file structure
- README.md lists all generated templates

### ❌ SYSTEM FAILURE:

- Creating templates without analyzing real code
- Not using the template-file structure
- Proceeding without user selection

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
