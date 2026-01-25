---
name: 'step-guide-08-finalize'
description: 'Generate root documentation files and complete the workflow'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-guide-08-finalize.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeRootTemplate: '{workflow_path}/templates/readme-root.template.md'
conditionalDocsTemplate: '{workflow_path}/templates/conditional-docs.template.md'
documentationStandardsTemplate: '{workflow_path}/templates/documentation-standards.template.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Guided Step 8: Finalize Documentation

## STEP GOAL:

To generate the root-level documentation files (README.md, CONDITIONAL_DOCS.md, DOCUMENTATION_STANDARDS.md) and complete the documentation structure.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Step-Specific Rules:

- 🎯 Generate root docs based on what was created in previous steps
- 🚫 FORBIDDEN to skip root doc generation
- 💬 Present summary of complete structure

## EXECUTION PROTOCOLS:

- 🎯 Scan docs/ folder to identify completed vs skipped sections
- 💾 Generate root README.md, CONDITIONAL_DOCS.md, DOCUMENTATION_STANDARDS.md
- 📖 Present completion summary with structure overview
- 🚫 FORBIDDEN to skip any root document generation

## CONTEXT BOUNDARIES:

- Available context: All completed sections from previous guided steps
- Focus: Root-level documentation that ties all sections together
- Limits: Generate based on what exists, don't create missing section content
- Dependencies: Completion of all previous guided steps

## GUIDED SEQUENCE:

### 1. Gather Completed Sections

Scan `docs/` folder to identify which sections were completed vs skipped:
- List sections with content
- List sections that are empty/placeholder

### 2. Generate Root README

Using {readmeRootTemplate}, create `docs/README.md`:

```markdown
---
title: Documentation Hub
description: Central documentation for [project_name]
author: [user_name]
date: [current date]
---

# [Project Name] Documentation

Welcome to the documentation hub.

## Quick Links

| Section | Description |
|---------|-------------|
| [Architecture](architecture/) | System design and decisions |
| [Development](development/) | Setup and contribution guides |
| [Templates](templates/) | Component creation patterns |
| [Reference](reference/) | Technical specifications |
| [Testing](testing/) | Testing strategy |
| [Product](product/) | Requirements and specs |
| [Design](design/) | UI/UX documentation |

## Getting Started

New to the project? Start here:
1. [Getting Started Guide](development/getting-started.md)
2. [Architecture Overview](architecture/overview.md)

## Documentation Standards

See [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md) for writing guidelines.

## Task-Based Navigation

See [CONDITIONAL_DOCS.md](CONDITIONAL_DOCS.md) for task-oriented documentation paths.
```

### 3. Generate CONDITIONAL_DOCS

Using {conditionalDocsTemplate}, create `docs/CONDITIONAL_DOCS.md`:

```markdown
---
title: Conditional Documentation Guide
description: Find documentation based on your current task
---

# Conditional Documentation Guide

This guide helps you find relevant documentation based on what you're working on.

## Instructions

- Review the task you need to perform
- Check the conditions below
- Read the relevant documentation before proceeding
- Only read documentation if conditions match your task

## Documentation Map

- docs/architecture/overview.md
  - Conditions:
    - When understanding the system architecture
    - When onboarding to the project

- docs/development/getting-started.md
  - Conditions:
    - When setting up the development environment

- docs/templates/
  - Conditions:
    - When creating a new component

- docs/testing/testing-strategy.md
  - Conditions:
    - When writing or running tests
```

### 4. Generate DOCUMENTATION_STANDARDS

Using {documentationStandardsTemplate}, create `docs/DOCUMENTATION_STANDARDS.md`:

```markdown
---
title: Documentation Standards
description: Guidelines for writing project documentation
---

# Documentation Standards

## File Structure

All documentation files require frontmatter:

```yaml
---
title: Document Title
description: One-line purpose
author: Author Name
date: YYYY-MM-DD
---
```

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| General docs | kebab-case | `getting-started.md` |
| Templates | `{name}-template.md` | `service-template.md` |
| ADRs | `adr-NNN-{title}.md` | `adr-001-database-choice.md` |

## Markdown Standards

- Use ATX-style headers (`#`, `##`, `###`)
- Never skip header levels
- Always include language tags in code blocks
- Use relative paths for internal links

## Content Rules

- No time estimates
- No secrets or credentials
- No absolute paths
- No orphan documents (link from README)
- One document per topic
```

### 5. Present Completion Summary

"**Documentation Structure Complete!**

**Sections Created:**
[List completed sections with file counts]

**Root Documents:**
- ✅ docs/README.md - Documentation hub
- ✅ docs/CONDITIONAL_DOCS.md - Task-based navigation
- ✅ docs/DOCUMENTATION_STANDARDS.md - Writing guidelines

**Structure Overview:**
```
docs/
├── README.md
├── CONDITIONAL_DOCS.md
├── DOCUMENTATION_STANDARDS.md
├── architecture/
├── development/
├── templates/
├── reference/
├── testing/
├── product/
└── design/
```

**Next Steps:**
1. Review generated documents and fill in TODO sections
2. Add more content as the project evolves
3. Keep CONDITIONAL_DOCS.md updated as docs grow

**Your documentation structure is ready!**"

### 6. Present MENU OPTIONS

Display: **Documentation complete!** [C] Complete

#### Menu Handling Logic:

- IF C: Display final success message and end workflow
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#6-present-menu-options)

## CRITICAL STEP COMPLETION NOTE

This is the final step. When user selects [C], the workflow is complete.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Root README.md generated with links to all sections
- CONDITIONAL_DOCS.md created with task-based navigation
- DOCUMENTATION_STANDARDS.md created with guidelines
- Completion summary presented
- Workflow ended gracefully

### ❌ SYSTEM FAILURE:

- Not generating root documents
- Missing links to created sections
- Not presenting completion summary

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
