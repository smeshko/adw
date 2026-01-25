---
name: 'step-auto-execute'
description: 'Autonomous documentation restructuring using sub-agents for parallel scanning'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-auto-execute.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
readmeRootTemplate: '{workflow_path}/templates/readme-root.template.md'
readmeSectionTemplate: '{workflow_path}/templates/readme-section.template.md'
conditionalDocsTemplate: '{workflow_path}/templates/conditional-docs.template.md'
documentationStandardsTemplate: '{workflow_path}/templates/documentation-standards.template.md'
gettingStartedTemplate: '{workflow_path}/templates/getting-started.template.md'

# Pattern Reference
patternSource: '{project-root}/project-docs-pattern/project-docs-pattern.md'
---

# Autonomous Mode: Documentation Restructuring

## STEP GOAL:

To automatically scan, categorize, reorganize existing documentation into the standard structure, fill major gaps (architecture overview, getting-started), and present a summary report.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input for major decisions
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE AN EXECUTOR following a defined process

### Role Reinforcement:

- ✅ You are a documentation architect performing automated restructuring
- ✅ Use sub-agents for parallel scanning operations
- ✅ Present summary for user review at completion

### Step-Specific Rules:

- 🎯 Execute the full autonomous pipeline
- 🚫 FORBIDDEN to skip the summary report
- 💬 Report findings and actions taken
- 🔄 Use sub-agents for parallel directory scanning

## EXECUTION PROTOCOLS:

- 🎯 Spawn sub-agents for parallel scanning
- 💾 Create standard folder structure
- 📖 Reorganize existing files
- 🔧 Fill major gaps only (architecture, getting-started)
- 📊 Present comprehensive summary

## CONTEXT BOUNDARIES:

- Available context: Project root and existing documentation files
- Focus: Autonomous reorganization with minimal user intervention
- Limits: Fill only major gaps, do not create exhaustive content
- Dependencies: Valid project with scannable file structure

## AUTONOMOUS EXECUTION SEQUENCE:

### 1. Create Standard Directory Structure

Create the docs/ folder structure if it doesn't exist:

```
docs/
├── README.md
├── DOCUMENTATION_STANDARDS.md
├── CONDITIONAL_DOCS.md
├── architecture/
│   └── README.md
├── development/
│   └── README.md
├── templates/
│   └── README.md
├── reference/
│   └── README.md
├── testing/
│   └── README.md
├── product/
│   └── README.md
└── design/
    └── README.md
```

### 2. Parallel Scan with Sub-Agents

Spawn sub-agents to scan different areas concurrently:

**Sub-Agent 1: Architecture Docs**
- Scan for: ARCHITECTURE.md, system diagrams, design docs, ADRs
- Target: docs/architecture/

**Sub-Agent 2: Development Docs**
- Scan for: CONTRIBUTING.md, setup guides, deployment docs, troubleshooting
- Target: docs/development/

**Sub-Agent 3: Reference Docs**
- Scan for: API docs, data models, service catalogs
- Target: docs/reference/

**Sub-Agent 4: Testing Docs**
- Scan for: test strategies, test plans, QA docs
- Target: docs/testing/

**Sub-Agent 5: Product Docs**
- Scan for: PRDs, requirements, specs, roadmaps
- Target: docs/product/

**Sub-Agent 6: Design Docs**
- Scan for: design systems, UI specs, mockups, style guides
- Target: docs/design/

### 3. Categorize and Reorganize

For each file found:
1. Determine appropriate section based on content
2. Move/copy to correct location in docs/ structure
3. Update any relative links if needed
4. Log the action taken

### 4. Fill Major Gaps

Check for and create if missing:

**Architecture Overview (if no architecture docs found):**
- Create `docs/architecture/overview.md` with placeholder structure
- Include sections: System Overview, Key Components, Data Flow, Technology Stack

**Getting Started (if no setup guide found):**
- Create `docs/development/getting-started.md` using template
- Include sections: Prerequisites, Installation, Quick Start, Common Issues

### 5. Generate Root Documents

Create using templates:

**docs/README.md** (using readme-root.template.md):
- Central documentation hub
- Links to all sections
- Project overview

**docs/DOCUMENTATION_STANDARDS.md** (using documentation-standards.template.md):
- Writing rules for the project

**docs/CONDITIONAL_DOCS.md** (using conditional-docs.template.md):
- Task-based navigation guide

### 6. Generate Section READMEs

For each section folder, create README.md (using readme-section.template.md):
- Section purpose and scope
- List of documents in section
- Links to related sections

### 7. Present Summary Report

Display comprehensive summary:

"**Autonomous Restructuring Complete**

**Folders Created:**
- [List of new folders]

**Files Reorganized:**
- [Original location] → [New location]
- ...

**Gaps Filled:**
- [List of generated placeholder docs]

**Root Documents Created:**
- docs/README.md
- docs/DOCUMENTATION_STANDARDS.md
- docs/CONDITIONAL_DOCS.md

**Section READMEs Created:**
- [List all section READMEs]

**Recommended Next Steps:**
1. Review reorganized files for accuracy
2. Fill in placeholder content in generated docs
3. Run Guided mode for any sections needing detailed attention

**Documentation structure is now ready!**"

### 8. Present MENU OPTIONS

Display: **Restructuring Complete** [C] Complete

#### Menu Handling Logic:

- IF C: Workflow complete - display final success message
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#8-present-menu-options)

## CRITICAL STEP COMPLETION NOTE

This is a terminal step. When user selects [C], the workflow is complete.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Standard folder structure created
- Sub-agents scanned all areas
- Existing docs reorganized appropriately
- Major gaps filled with placeholder docs
- Root and section READMEs generated
- Comprehensive summary presented

### ❌ SYSTEM FAILURE:

- Not using sub-agents for parallel scanning
- Skipping folder creation
- Not presenting summary report
- Creating excessive content beyond major gaps

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
