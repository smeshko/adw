---
stepsCompleted: [1, 2, 3]
status: complete
targetWorkflow: dev-begin
editGoals:
  - Always force worktree (remove branch option)
  - Fix sprint-status update to happen in worktree
---

# Workflow Edit: dev-begin

## Workflow Analysis

### Target Workflow

- **Path**: `_bmad/bmm/workflows/4-implementation/dev-begin/`
- **Name**: dev-begin
- **Module**: bmm (4-implementation)
- **Format**: Legacy XML (workflow.yaml + instructions.xml)

### Structure Analysis

- **Type**: Autonomous Workflow
- **Total Steps**: 7 (within single instructions.xml)
- **Step Flow**: Linear with early exit points and goto/anchor patterns
- **Files**:
  ```
  dev-begin/
  ├── workflow.yaml      # Configuration and variables
  ├── instructions.xml   # Main workflow logic (7 steps)
  └── workflow-plan.md   # Planning document
  ```

### Content Characteristics

- **Purpose**: Initialize development environment for a story - handles git state, dependency validation, and worktree/branch setup before invoking dev-story
- **Instruction Style**: Prescriptive (autonomous with specific logic)
- **User Interaction**: Minimal - only Step 1 (uncommitted changes) prompts user
- **Complexity**: Medium-high (git operations, conditional logic, workflow handoff)

### Initial Assessment

#### Strengths

- Well-structured autonomous flow
- Comprehensive error handling and exit points
- Good informational output to user
- Proper dependency checking before work begins
- Resume mode detection works well

#### Issues Identified (User-Reported)

1. **Conditional worktree/branch logic is unwanted** - User wants worktree always
2. **Sprint-status update blocks parallel runs** - Update happens on staging (absolute path), making it dirty for next parallel run

### Edit Goals

| # | Goal | Impact Area |
|---|------|-------------|
| 1 | Always force worktree | Step 5 (decision logic), Step 6 (setup logic) |
| 2 | Update sprint-status in worktree | Step 7 (timing/path of update) |

### Detailed Change Analysis

#### Change 1: Always Force Worktree

**Current Logic (Step 5, lines 237-317):**
- Parses "Can Parallel With" from story file
- If NOT empty → worktree
- If empty → branch

**Required Changes:**
- Remove "Can Parallel With" parsing
- Remove branch decision path
- Always set `environment_type = "worktree"`
- Simplify Step 5 significantly

**Affected Areas:**
- Step 5: Remove conditional, always worktree
- Step 6: Remove branch creation path (lines 397-402)

#### Change 2: Sprint-Status Update in Worktree

**Current Flow:**
1. Step 6: Create worktree, cd into worktree
2. Step 7: Update `{{sprint_status}}` (absolute path to main repo)

**Problem:**
- `sprint_status` = `{implementation_artifacts}/sprint-status.yaml`
- This resolves to absolute path in main repo, not worktree
- Update dirties staging, blocking parallel runs

**Solution (Option B - User Selected):**
- Update sprint-status.yaml **inside the worktree** after cd
- Need to use relative path or worktree-aware path
- Status only visible in that worktree's copy

**Implementation:**
- After cd to worktree, use relative path `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Or compute worktree-local path: `{{environment_path}}/_bmad-output/implementation-artifacts/sprint-status.yaml`

### Best Practices Compliance

- **Step File Structure**: N/A (Legacy XML format)
- **Frontmatter Usage**: N/A (Legacy format)
- **Menu Implementation**: Minimal menus (Step 1 only)
- **Variable Consistency**: Good - uses config-based variables

### Format Notes

- This is a Legacy XML workflow, not the new standalone markdown format
- Single `instructions.xml` contains all 7 steps
- Migration to standalone format is optional but not required for these edits

---

_Analysis completed on 2026-01-18_

---

## Improvement Log

### Change 1: Always Use Worktree (Step 5)

**File:** `instructions.xml`

**Before:**
- Parsed "Can Parallel With" section from story file
- If entries existed → worktree
- If empty → branch
- Resume mode checked for both worktree and branch environments

**After:**
- Removed all "Can Parallel With" parsing
- Always sets `environment_type = "worktree"`
- Resume mode only checks for existing worktree
- Simplified error message for in-progress stories without worktree

**Lines changed:** ~75 lines reduced to ~45 lines

---

### Change 2: Remove Branch Creation Path (Step 6)

**File:** `instructions.xml`

**Before:**
- Had conditional logic for worktree vs branch creation
- Resume mode had multiple paths (worktree, branch checkout, needs_checkout)
- Branch creation block at end of step

**After:**
- Only worktree creation path remains
- Resume mode simplified to single worktree path
- Removed entire `<check if="{{environment_type}} == 'branch'">` block

**Lines changed:** ~65 lines reduced to ~45 lines

---

### Change 3: Sprint-Status Update in Worktree (Step 7)

**File:** `instructions.xml`

**Before:**
```xml
<action>Update {{sprint_status}}: set {{target_story_id}} status to "in-progress"</action>
```
- Used absolute path `{{sprint_status}}` pointing to main repo
- Modified staging's sprint-status.yaml
- Blocked parallel runs (dirty staging)

**After:**
```xml
<action>Update worktree-local sprint-status.yaml: set {{target_story_id}} status to "in-progress"</action>
<action>Path: {{environment_path}}/_bmad-output/implementation-artifacts/sprint-status.yaml</action>
```
- Uses worktree-local path `{{environment_path}}/_bmad-output/...`
- Modifies worktree's copy only
- Staging stays clean for parallel runs

---

## Summary

| Metric | Before | After |
|--------|--------|-------|
| Step 5 lines | ~75 | ~45 |
| Step 6 lines | ~65 | ~45 |
| Decision paths | 2 (worktree/branch) | 1 (worktree only) |
| Parallel run blocking | Yes | No |

**Total lines removed:** ~50 lines of conditional logic

---

_Improvements completed on 2026-01-18_
