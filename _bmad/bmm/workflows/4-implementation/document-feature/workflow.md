---
name: document-feature
description: Verify, update, and build reusable project documentation
web_bundle: true
---

# Document Feature

**Goal:** Verify that code changes are properly documented, identify documentation gaps, automatically update documentation, and build reusable project knowledge through feature documentation and conditional docs.

**Your Role:** You are a documentation specialist and knowledge architect that executes documentation analysis and updates. Work autonomously to complete all steps, reporting results clearly at completion. User interaction is only needed if errors require manual intervention.

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that analyzes, updates, and builds documentation.

### Core Principles

- **Config-Driven**: Documentation settings from `_bmad/project-config.yaml`
- **Run All**: Execute all documentation checks, collecting results throughout
- **Auto-Proceed**: Move between steps automatically without user confirmation
- **Clear Reporting**: Provide comprehensive status at workflow completion
- **Fail-Safe**: Handle errors gracefully, continue where possible, report all issues
- **Knowledge Building**: Create reusable feature docs for significant changes

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Move to next step immediately upon completion (no menu wait)
4. **TRACK STATE**: Maintain execution context between steps for final reporting
5. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Key Concepts

**Conditional Docs Guide** (`docs/CONDITIONAL_DOCS.md`):
- A map of "when working on X, read Y documentation"
- Helps future developers find relevant docs for their task
- Auto-updated when new feature docs are created

**Feature Documentation** (`docs/features/`):
- Overview docs for significant changes (new patterns, features, architectural decisions)
- Reusable knowledge that guides future similar implementations
- Referenced in conditional docs guide

### Execution Rules

1. **READ CONFIG**: Load document configuration from project-config.yaml
2. **LOAD GUIDE**: Read conditional docs guide to understand existing documentation
3. **DETECT CHANGES**: Get recent code changes via git
4. **ANALYZE**: Check inline docs, external docs, and significance of changes
5. **UPDATE**: Add missing docs, create feature docs if significant
6. **UPDATE GUIDE**: Add new feature docs to conditional docs guide
7. **COMMIT**: Auto-commit all documentation updates

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 🔄 **ALWAYS** run all documentation checks (don't fail fast)
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📊 **ALWAYS** track results for final reporting
- ⏹️ **STOP** only when workflow completes or unrecoverable error occurs

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`

Load project config from {project-root}/_bmad/project-config.yaml and resolve:

- `document` section with all settings

### 2. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
