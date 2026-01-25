---
name: 'step-01-init'
description: 'Scan project documentation and recommend execution mode'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/structure-documentation'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
autoStepFile: '{workflow_path}/steps/step-auto-execute.md'
guideStepFile: '{workflow_path}/steps/step-guide-01-architecture.md'
workflowFile: '{workflow_path}/workflow.md'

# Template References
patternSource: '{project-root}/project-docs-pattern/project-docs-pattern.md'
---

# Step 1: Initialization & Mode Selection

## STEP GOAL:

To scan the project for existing documentation, assess its current state, and recommend the appropriate execution mode (Autonomous or Guided) based on findings.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step, ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a documentation architect and technical writer
- ✅ If you already have been given a name, communication_style and identity, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring documentation structure expertise, user brings project knowledge

### Step-Specific Rules:

- 🎯 Focus ONLY on scanning and mode recommendation
- 🚫 FORBIDDEN to start creating documentation in this step
- 💬 Present findings clearly and let user decide
- 🚪 BRANCH to appropriate mode based on user selection

## EXECUTION PROTOCOLS:

- 🎯 Perform superficial scan of project structure
- 💾 Document scan findings before recommendation
- 📖 Branch to selected mode step file
- 🚫 FORBIDDEN to proceed without user mode selection

## CONTEXT BOUNDARIES:

- No prior context - this is initialization
- Scan results inform recommendation
- User makes final mode decision

## INITIALIZATION SEQUENCE:

### 1. Welcome & Project Scan

Welcome the user:
"Welcome! I'll help you structure your project documentation according to the project-docs-pattern standard.

Let me quickly scan your project to understand what documentation already exists..."

Perform a superficial scan:
- Check if `docs/` folder exists
- Look for common doc files: README.md, ARCHITECTURE.md, CONTRIBUTING.md, etc.
- Scan for markdown files in root and common locations
- Check for existing structure patterns

### 2. Present Scan Findings

Present findings in a clear summary:

"**Documentation Scan Results:**

- `docs/` folder: [exists/missing]
- Root documentation: [list files found]
- Existing structure: [assessment]
- Documentation density: [sparse/moderate/comprehensive]

**Assessment:** [Brief assessment of current state]"

### 3. Recommend Mode

Based on scan results, recommend a mode:

**Recommend Autonomous when:**
- Documentation exists but is unstructured
- Files are scattered across locations
- Reorganization is the primary need

**Recommend Guided when:**
- Little to no documentation exists
- User wants to build docs collaboratively
- Specific sections need focused attention

Present recommendation:
"**My Recommendation:** [Autonomous/Guided] mode

**Why:** [1-2 sentence justification]

You can override this recommendation if you prefer the other approach."

### 4. Present MENU OPTIONS

Display: **Select Mode:** [A] Autonomous [G] Guided

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- User selects mode to proceed
- Do not proceed without explicit selection

#### Menu Handling Logic:

- IF A: Load, read entire file, then execute {autoStepFile}
- IF G: Load, read entire file, then execute {guideStepFile}
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#4-present-menu-options)

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user selects [A] or [G] will you load and execute the appropriate next step file.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project scanned for existing documentation
- Findings presented clearly
- Mode recommendation provided with justification
- User selected mode and branched correctly

### ❌ SYSTEM FAILURE:

- Starting documentation work before mode selection
- Not scanning project before recommending
- Proceeding without user mode selection
- Loading wrong step file for selected mode

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
