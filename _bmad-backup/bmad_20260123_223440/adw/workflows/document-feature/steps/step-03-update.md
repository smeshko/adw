---
name: 'step-03-update'
description: 'Update documentation, create feature docs, and update conditional docs guide'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/document'

# File References
thisStepFile: '{workflow_path}/steps/step-03-update.md'
nextStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
conditionalDocsFile: '{project-root}/docs/CONDITIONAL_DOCS.md'
featureDocsDir: '{project-root}/docs/features'
---

# Step 3: Update Documentation

## STEP GOAL:

To update inline documentation, external documentation, create feature docs for significant changes, and update the conditional docs guide.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - update efficiently
- 🔄 Auto-proceed to next step when complete

### Role Reinforcement:

- ✅ You are a documentation writer and knowledge architect
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

- 🎯 Update docs based on analysis from step 2
- ✅ Auto-apply all documentation updates
- ✅ Create feature docs for significant changes
- ✅ Update conditional docs guide
- ✅ Commit all changes

## EXECUTION PROTOCOLS:

- 🎯 Apply all documentation updates identified in analysis
- 💾 Track all modifications for commit message and reporting
- 📖 Create feature documentation following template structure
- 🚫 Do not skip any identified issues

## CONTEXT BOUNDARIES:

- Available context: Analysis results from step 2, inline/external issues, significance determination
- Focus: Applying documentation updates and creating feature docs
- Limits: Only update based on analysis results, no new analysis
- Dependencies: Completed analysis step with issue list and significance decision

## UPDATE SEQUENCE:

### 1. Initialize Update Tracking

```
updates = {
  inlineUpdates: [],
  externalUpdates: [],
  featureDocCreated: null,
  conditionalDocsUpdated: false,
  filesModified: []
}
```

### 2. Update Inline Documentation

For each inline issue from analysis:

**Add Missing JSDoc/Docstrings:**
- Read the code element
- Generate appropriate documentation
- Follow project patterns
- Apply the update

**Track update:**
```
{
  file: "path/to/file",
  line: 42,
  type: "added_jsdoc",
  element: "function processData"
}
```

### 3. Update External Documentation

For each external issue from analysis:

**Update README.md:**
- Add new feature descriptions
- Update API references
- Fix outdated information

**Update docs/ files:**
- Add new sections for new features
- Update existing sections with changes

### 4. Create Feature Documentation (if significant)

If analysis determined changes are significant:

**Create feature docs directory if needed:**
```bash
mkdir -p docs/features
```

**Create feature doc using template:**

```markdown
# [Feature Title]

**Date:** [current date]
**Related Files:** [list of main files]

## Overview

[2-3 sentence summary of what was built and why, based on git diff analysis]

## What Was Built

[List the main components/features implemented]

- [Component/feature 1]
- [Component/feature 2]

## Technical Implementation

### Key Files

- `[file_path]`: [what this file does]
- `[file_path]`: [what this file does]

### Key Patterns

[Describe the most important technical patterns in 3-5 bullet points]

- [Pattern 1]: [description]
- [Pattern 2]: [description]

## How to Use

[Step-by-step instructions for using the new feature]

1. [Step 1]
2. [Step 2]

## Configuration

[Any configuration options, environment variables, or settings]

## Notes

[Any additional context, limitations, or future considerations]
```

**Save to:** `docs/features/[feature-name].md`

### 5. Update Conditional Docs Guide

**If feature doc was created:**

Check if `{conditionalDocsFile}` exists:

**If doesn't exist, create it:**

```markdown
# Conditional Documentation Guide

This guide helps you find relevant documentation based on what you're working on.

## Instructions

- Review the task you need to perform
- Check the conditions below
- Read the relevant documentation before proceeding
- Only read documentation if conditions match your task

## Documentation Map

- docs/features/[new-feature].md
  - Conditions:
    - [condition 1]
    - [condition 2]
    - [condition 3]
```

**If exists, append new entry:**

Read the existing file and add:

```markdown
- docs/features/[new-feature].md
  - Conditions:
    - [condition 1]
    - [condition 2]
    - [condition 3]
```

### 6. Display Updates Made

"**Documentation Updates Applied:**

**Inline Documentation:**

| File | Element | Update |
|------|---------|--------|
| [file] | [element] | Added JSDoc/docstring |

**External Documentation:**

| File | Section | Update |
|------|---------|--------|
| [file] | [section] | [change description] |

**Feature Documentation:** (if created)

| Item | Details |
|------|---------|
| File | `docs/features/[name].md` |
| Title | [Feature Title] |
| Sections | [list] |

**Conditional Docs Guide:**

| Action | Details |
|--------|---------|
| [Created/Updated] | Added entry for [feature] |
| Conditions | [list of conditions] |"

### 7. Commit and Push Documentation Changes

Stage all modified documentation files:

Create commit with message:
```
docs: update documentation for recent changes

Inline documentation:
- [list of inline updates]

External documentation:
- [list of external updates]

Feature documentation:
- Created docs/features/[name].md (if applicable)

Conditional docs guide:
- [Created/Updated] with new entry (if applicable)
```

Display: "Committed documentation updates in [commit hash]"

**Push changes to remote:**

```bash
git push
```

Display: "Pushed documentation changes to remote"

**If push fails:**
- Display warning: "⚠️ Push failed - changes committed locally but not pushed"
- Store push_status = "failed" for reporting
- Continue to next step (don't halt workflow)

### 8. Store Update Context and Proceed

Store updates context for report step.

Load, read entire file, then execute `{nextStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN all documentation updates are applied, feature docs created (if significant), conditional guide updated, and changes committed, will you then load and read fully `{nextStepFile}` to execute the reporting phase.

---

## FEATURE DOC TEMPLATES BY TYPE:

### New Pattern
Focus on: How to use the pattern, when to use it, examples

### New Feature
Focus on: What it does, how to use it, configuration

### Integration
Focus on: Setup, authentication, error handling, gotchas

### Architecture Decision
Focus on: Why this approach, alternatives considered, trade-offs

---

## CONDITIONAL DOCS ENTRY EXAMPLES:

**Authentication Feature:**
```markdown
- docs/features/authentication.md
  - Conditions:
    - When adding protected routes
    - When implementing login/logout flows
    - When working with user sessions
    - When troubleshooting auth issues
```

**API Patterns:**
```markdown
- docs/features/api-patterns.md
  - Conditions:
    - When adding new API endpoints
    - When implementing request validation
    - When working with API middleware
    - When handling API errors
```

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All identified issues addressed
- Documentation follows project patterns
- Feature doc created for significant changes
- Conditional docs guide updated
- Changes committed with clear message

### ❌ SYSTEM FAILURE:

- Not addressing all issues
- Not creating feature doc when warranted
- Not updating conditional docs guide
- Not committing changes
- Generic/unhelpful documentation

**Master Rule:** Build knowledge that helps future developers find what they need.
