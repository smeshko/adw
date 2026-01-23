---
name: 'step-01-init'
description: 'Initialize document workflow, load conditional docs guide, and detect changes'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/document'

# File References
thisStepFile: '{workflow_path}/steps/step-01-init.md'
nextStepFile: '{workflow_path}/steps/step-02-analyze.md'
workflowFile: '{workflow_path}/workflow.md'
projectConfigFile: '{project-root}/_bmad/project-config.yaml'
conditionalDocsFile: '{project-root}/docs/CONDITIONAL_DOCS.md'
featureDocsDir: '{project-root}/docs/features'
---

# Step 1: Initialize Documentation Check

## STEP GOAL:

To load project configuration, the conditional docs guide, documentation standards, and detect recent code changes that need documentation review.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
- 🔄 Auto-proceed to next step when complete

### Role Reinforcement:

- ✅ You are a documentation specialist and knowledge architect
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

- 🎯 Focus ONLY on loading config and detecting changes
- 🚫 FORBIDDEN to update any docs in this step
- ✅ Load conditional docs guide if it exists
- ✅ Find relevant existing docs for the changes

## EXECUTION PROTOCOLS:

- 🎯 Load all configuration before analyzing changes
- 💾 Store configuration and change context for subsequent steps
- 📖 Parse conditional docs guide to identify relevant documentation
- 🚫 Do not modify any files in this initialization step

## CONTEXT BOUNDARIES:

- Available context: Project configuration files, git status
- Focus: Configuration loading and change detection
- Limits: No documentation updates, analysis only
- Dependencies: Valid project-config.yaml, git repository

## INITIALIZATION SEQUENCE:

### 1. Load Project Configuration

Read `{projectConfigFile}` and extract the `document` section:

```yaml
document:
  standards_file: "path/to/standards"
  check_inline: true/false
  check_external: true/false
  doc_locations:
    - "README.md"
    - "docs/"
  patterns: []
```

### 2. Load Conditional Docs Guide

Check if `{conditionalDocsFile}` exists:

**If exists:**
- Read the complete file
- Parse the conditional documentation entries
- Store for use in analysis step

**If doesn't exist:**
- Note that it needs to be created
- Will be created in update step if feature docs are added

**Sample Conditional Docs Guide format:**
```markdown
# Conditional Documentation Guide

## Instructions
Review the conditions below and read relevant documentation before proceeding.

## Documentation Map

- docs/features/authentication.md
  - Conditions:
    - When working with user authentication
    - When modifying login/logout flows
    - When implementing session management

- docs/features/api-patterns.md
  - Conditions:
    - When adding new API endpoints
    - When modifying request/response handling
    - When working with middleware
```

### 3. Detect Recent Changes

Get changes to analyze:

**Check git status:**
- Uncommitted changes (staged and unstaged)
- Recent commits (last N commits or since last tag)

**Collect changed files:**
- New files added
- Modified files
- Deleted files
- File types and locations

### 4. Find Relevant Documentation

Based on changed files, check conditional docs guide:

For each changed file:
- Check if any conditions in the guide match
- Collect list of relevant docs that should be read/considered

Display:
"**Relevant Documentation Found:**

Based on your changes, consider these existing docs:

| File Changed | Relevant Doc | Reason |
|--------------|--------------|--------|
| [changed file] | [doc path] | [matching condition] |
| ... | ... | ... |

These docs may have patterns or context useful for your changes."

### 5. Display Changes Summary

"**Changes Detected:**

| Type | Count | Files |
|------|-------|-------|
| New | [X] | [list] |
| Modified | [Y] | [list] |
| Deleted | [Z] | [list] |
| Total | [T] | - |

**Conditional Docs Guide:** [Exists/Needs Creation]
**Feature Docs:** [X existing in docs/features/]"

### 6. Handle No Changes

If no changes detected:

Display:
"**No changes detected**

Your working directory is clean.

Workflow complete - nothing to check."

End workflow.

### 7. Store Context and Proceed

Store in memory:
- Document configuration
- Conditional docs guide (if exists)
- List of changed files
- Relevant existing docs for these changes

Auto-proceed to next step:
Load, read entire file, then execute `{nextStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN configuration is loaded and changes are detected, will you then load and read fully `{nextStepFile}` to execute the documentation analysis phase.

If no changes are detected, workflow ends gracefully with "nothing to check" message.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Configuration loaded (or defaults applied)
- Conditional docs guide loaded if available
- Changed files identified
- Relevant existing docs identified
- Context ready for analysis step

### ❌ SYSTEM FAILURE:

- Not checking for changes
- Not loading conditional docs guide
- Not identifying relevant existing docs
- Proceeding with no context

**Master Rule:** Know what changed AND what existing docs are relevant.
