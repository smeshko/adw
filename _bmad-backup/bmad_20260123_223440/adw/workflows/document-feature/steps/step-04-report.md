---
name: 'step-04-report'
description: 'Generate final documentation report including feature docs and conditional guide updates'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/document'

# File References
thisStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 4: Documentation Report

## STEP GOAL:

To generate a final report summarizing documentation analysis, updates, feature docs created, and conditional guide changes.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is the final step - report clearly
- 🔄 Workflow ends after this step

### Role Reinforcement:

- ✅ You are a documentation reporter
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

- 🎯 Generate comprehensive summary
- ✅ Show feature docs and conditional guide updates
- ✅ End with appropriate status

## EXECUTION PROTOCOLS:

- 🎯 Compile all results from previous steps into final report
- 💾 Present clear summary of all changes made
- 📖 Highlight knowledge building achievements (feature docs, guide updates)
- 🚫 Do not modify any files in this reporting step

## CONTEXT BOUNDARIES:

- Available context: All results from steps 1-3, files analyzed, issues found, updates made
- Focus: Generating comprehensive final report
- Limits: Reporting only, no file modifications
- Dependencies: Completed analysis and update steps (or direct route if no issues)

## REPORT SEQUENCE:

### 1. Compile Final Results

Gather from context:
- Files analyzed from step 1
- Issues found from step 2
- Significance determination from step 2
- Updates made from step 3
- Feature doc created (if any)
- Conditional guide updates (if any)
- Commit information

### 2. Generate Report Header

```
═══════════════════════════════════════════════════════════════
                    DOCUMENTATION REPORT
═══════════════════════════════════════════════════════════════
```

### 3. Display Analysis Summary

"**Analysis Summary:**

| Category | Checked | Issues Found | Updated |
|----------|---------|--------------|---------|
| Inline docs | [Y/N] | [count] | [count] |
| External docs | [Y/N] | [count] | [count] |
| Significance | Evaluated | [significant/not] | - |
| **Total** | - | [total] | [total] |"

### 4. Display Updates Made (if any)

"**Documentation Updates:**

| Type | File | Details |
|------|------|---------|
| Inline | [file] | [description] |
| External | [file] | [description] |"

### 5. Display Feature Documentation (if created)

If feature doc was created:

"**Feature Documentation Created:**

```
═══════════════════════════════════════════════════════════════
  📚 NEW KNOWLEDGE CAPTURED
═══════════════════════════════════════════════════════════════
```

| Property | Value |
|----------|-------|
| File | `docs/features/[name].md` |
| Title | [Feature Title] |
| Type | [Pattern/Feature/Integration/Decision] |

**Why this was documented:**
- [Significance reason 1]
- [Significance reason 2]

**Future developers should read this when:**
- [Condition 1]
- [Condition 2]
- [Condition 3]"

### 6. Display Conditional Docs Guide Status

"**Conditional Docs Guide:**

| Status | Details |
|--------|---------|
| Guide | [Created/Updated/Unchanged] |
| Entries | [X total entries] |
| New Entry | [Added for feature X / None] |

**Knowledge Discoverability:**
Future developers working on related areas will be guided to read:
- `docs/features/[name].md`"

### 7. Display Final Status

#### IF no issues found AND not significant:

```
═══════════════════════════════════════════════════════════════
  ✅ DOCUMENTATION COMPLETE
═══════════════════════════════════════════════════════════════

All documentation is up to date. No updates needed.
```

#### IF updates made (no feature doc):

```
═══════════════════════════════════════════════════════════════
  ✅ DOCUMENTATION UPDATED
═══════════════════════════════════════════════════════════════

Summary:
- Files analyzed: [X]
- Issues found: [Y]
- Issues fixed: [Z]
- Commit: [hash]
- Pushed: [Yes/No - include warning if failed]

Standard documentation gaps have been addressed.
```

#### IF feature doc created:

```
═══════════════════════════════════════════════════════════════
  ✅ KNOWLEDGE BASE EXPANDED
═══════════════════════════════════════════════════════════════

Summary:
- Files analyzed: [X]
- Issues fixed: [Y]
- Feature doc created: docs/features/[name].md
- Conditional guide: [Created/Updated]
- Commit: [hash]
- Pushed: [Yes/No - include warning if failed]

New reusable knowledge has been captured and made discoverable!
```

### 8. Provide Next Steps

#### IF all complete:
"**Next Steps:**
- Documentation is ready
- Run `/ship` when ready to deploy"

#### IF feature doc created:
"**Next Steps:**
- Review the new feature doc: `docs/features/[name].md`
- Verify the conditions in `docs/CONDITIONAL_DOCS.md` are accurate
- Run `/ship` when ready to deploy"

### 9. End Workflow

This is the final step. Workflow ends here.

**Exit Status:**
- Return success (0) if all documentation is complete

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Clear report generated
- All analysis and updates summarized
- Feature doc creation highlighted
- Conditional guide status shown
- Commit information included
- Appropriate next steps provided

### ❌ SYSTEM FAILURE:

- Incomplete report
- Not highlighting feature docs
- Not showing conditional guide status
- No next steps
- Unclear status

**Master Rule:** Generate a clear report that shows both immediate updates AND knowledge building achievements.
