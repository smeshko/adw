---
stepsCompleted: [1, 2, 3, 4, 6, 7, 8]
status: complete
---

# Workflow Creation Plan: dev-begin

## Initial Project Context

- **Module:** bmm (4-implementation)
- **Target Location:** .bmad/bmm/workflows/4-implementation/dev-begin/
- **Created:** 2025-12-09

---

## Requirements

### 1. Workflow Purpose and Scope

| Aspect | Details |
|--------|---------|
| **Problem** | Remove environment setup logic from dev-story; automate worktree vs branch decision |
| **Primary User** | Developers starting work on a story |
| **Main Outcome** | Configured development environment (worktree or branch) + dev-story invocation |

### 2. Workflow Type Classification

**Autonomous Workflow** - Runs with minimal human input, makes decisions automatically based on project state.

### 3. Workflow Flow and Step Structure

**Linear with early exit points:**

```
Step 1: Git State Check (uncommitted changes)
Step 2: Determine Target Story
Step 3: Validate Story State (STOP if done/review not merged)
Step 4: Dependency Check (STOP if incomplete dependencies)
Step 5: Environment Decision & Setup (worktree or branch)
Step 6: Invoke dev-story
```

### 4. User Interaction Style

- **Minimal input** - Only story ID (optional, can auto-detect)
- **One exception** - Uncommitted changes prompt (safety)
- **Inform, don't ask** - Reports decisions, doesn't prompt for choices
- **Automatic decisions** - All environment decisions based on project state

### 5. Instruction Style

**Prescriptive** - Autonomous workflow with specific logic that must execute consistently.

### 6. Input Requirements

| Input | Required | Source |
|-------|----------|--------|
| Story ID | Optional | User input or auto-detect |
| Story file | Required | Located via sprint-status or story-id |
| sprint-status.yaml | Required | For dependency status checks |
| .worktrees/ directory | Optional | Scanned for resume detection |

### 7. Output Specifications

| Output | Type |
|--------|------|
| Environment decision | Worktree or Branch |
| Worktree/Branch created | Git action |
| dev-story invocation | Workflow handoff |
| Status messages | Console output (inform user) |

### 8. Success Criteria

- Dependencies correctly validated (blocks when incomplete)
- Parallelization correctly decided based on "Can Parallel With" entries
- Environment set up correctly (worktree at `.worktrees/story-{id}/` or branch `story/{id}`)
- dev-story successfully invoked with story context
- User informed of all decisions and reasons

---

## Detailed Flow Logic

### STEP 1: GIT STATE CHECK

```
Check for uncommitted changes (git status --porcelain)
IF uncommitted changes exist:
  → Offer options:
    1. Stash changes (git stash push -m "dev-begin auto-stash")
    2. Commit changes (prompt for message)
    3. Discard changes (git checkout -- . && git clean -fd)
    4. Abort workflow
  → Handle user choice
```

### STEP 2: DETERMINE TARGET STORY

```
IF story-id provided by user:
  → Use that story
ELSE IF on story/* branch:
  → Extract story-id from branch name
ELSE IF in .worktrees/story-*/ directory:
  → Extract story-id from worktree path
ELSE (on staging or unknown):
  → Find next ready-for-dev story from sprint-status.yaml
```

### STEP 3: VALIDATE STORY STATE

```
Load story file
Check story status in sprint-status.yaml

IF status == "done" OR status == "review":
  → Check if branch/worktree is merged to staging
  → IF merged:
      "Story complete and merged. Finding next story..."
      → Go back to STEP 2 (find next ready-for-dev)
  → IF not merged:
      STOP: "Story is done/in-review but not merged.
             Merge PR first, then run dev-begin again."

IF status == "in-progress":
  → Resume mode - will continue on existing branch/worktree

IF status == "ready-for-dev":
  → Fresh start - will create new branch/worktree
```

### STEP 4: DEPENDENCY CHECK (hard stop)

```
Parse "Depends On" from story file
Check status of each dependency in sprint-status.yaml

IF ANY dependency is NOT "done":
  → STOP: "Cannot start Story X.Y"
  → List incomplete dependencies with their current status
  → EXIT workflow
```

### STEP 5: ENVIRONMENT DECISION & SETUP

#### Resume Mode (status == "in-progress")

```
Check if existing environment exists:

IF .worktrees/story-{id}/ exists:
  → cd .worktrees/story-{id}/
  → Inform: "Resuming in existing worktree"
  → SKIP to STEP 6

IF on story/{id} branch already:
  → Stay on branch
  → Inform: "Resuming on existing branch"
  → SKIP to STEP 6

IF branch story/{id} exists but not checked out:
  → git checkout story/{id}
  → Inform: "Switched to existing story branch"
  → SKIP to STEP 6
```

#### Fresh Start Mode (status == "ready-for-dev")

```
Parse "Can Parallel With" from story

IF "Can Parallel With" is NOT EMPTY:
  → Decision: WORKTREE
  → Reason: "Story can be parallelized with others"
  → IF not on staging: git checkout staging
  → git pull origin staging
  → git worktree add .worktrees/story-{id} -b story/{id}
  → cd .worktrees/story-{id}
  → Inform user of decision + active parallel worktrees (if any)

ELSE (Can Parallel With is empty):
  → Decision: BRANCH
  → Reason: "Story has no parallel siblings"
  → IF not on staging: git checkout staging
  → git pull origin staging
  → git checkout -b story/{id}
  → Inform user of decision
```

### STEP 6: INVOKE DEV-STORY

```
Pass to dev-story:
  - story_path: path to story file
  - story_id: extracted story ID
  - environment_type: "worktree" | "branch"
  - is_resume: true | false

dev-story receives clean environment, no git setup needed
```

---

## Decision Rules Summary

| Condition | Decision |
|-----------|----------|
| "Can Parallel With" has entries | WORKTREE |
| "Can Parallel With" is empty | BRANCH |
| Existing worktree for story | Resume in worktree |
| Existing branch for story | Resume on branch |
| Dependencies incomplete | STOP |
| Story done but not merged | STOP |

---

## Changes Required to dev-story

After dev-begin is created, dev-story Step 1 and Step 2 git/branch logic should be removed:
- Remove uncommitted changes check
- Remove branch detection logic
- Remove branch creation logic
- Remove story discovery logic (will receive story_path as input)
- Keep: commit-per-task logic
- Keep: all implementation steps (3-11)

---

## Tools Configuration

### Core BMAD Tools

- **Party-Mode**: ❌ Excluded - Not needed, no creative/collaborative phases
- **Advanced Elicitation**: ❌ Excluded - Not needed, no quality review points
- **Brainstorming**: ❌ Excluded - Not needed, no idea generation

### LLM Features

- **Web-Browsing**: ❌ Excluded - All data is local (git, files)
- **File I/O**: ✅ Included - Reading story files, sprint-status.yaml, parsing dependencies
- **Sub-Agents**: ❌ Excluded - Linear flow, no delegation needed
- **Sub-Processes**: ❌ Excluded - Sequential execution

### Memory Systems

- **Sidecar File**: ❌ Excluded - No session continuity needed, state lives in git/files

### External Integrations

- **Git Integration (MCP)**: ❌ Excluded - Native bash git commands are simpler, no install required

### Installation Requirements

- None - All tools are built-in or use native bash commands

---

## Workflow Design

### Architecture Decision

**Single instructions.xml approach** (matching dev-story pattern)
- Appropriate for autonomous workflow with minimal user interaction
- No step-to-step loading overhead
- Self-contained logic

### File Structure

```
.bmad/bmm/workflows/4-implementation/dev-begin/
├── workflow.yaml          # Configuration and variables
├── instructions.xml       # Main workflow logic (all steps)
└── workflow-plan.md       # This planning document (dev artifact)
```

No checklist.md needed - validation is inline within instructions.xml.

### Step Sequence (within instructions.xml)

| Step | Name | Purpose | User Input |
|------|------|---------|------------|
| 1 | Git State Check | Handle uncommitted changes | YES (if changes exist) |
| 2 | Determine Target Story | Find/validate story | NO |
| 3 | Validate Story State | Check done/review/in-progress | NO |
| 4 | Dependency Check | Verify "Depends On" complete | NO |
| 5 | Environment Decision | Worktree vs Branch | NO |
| 6 | Environment Setup | Create worktree/branch | NO |
| 7 | Invoke dev-story | Handoff to implementation | NO |

### Data Flow

```
INPUT:
  └─ story_id (optional, from user or auto-detect)

STEP 1 → working_tree_clean: bool
STEP 2 → story_id, story_path
STEP 3 → story_status, is_resume: bool
STEP 4 → dependencies_satisfied: bool (or STOP)
STEP 5 → environment_type: "worktree" | "branch"
STEP 6 → environment_path

OUTPUT TO DEV-STORY:
  └─ story_path
  └─ story_id
  └─ environment_type
  └─ is_resume
```

### Role Definition

| Aspect | Value |
|--------|-------|
| Role | Development Environment Orchestrator |
| Communication | Direct, informative, action-oriented |
| Collaboration | Minimal - mostly autonomous |

### Error Handling

| Scenario | Action |
|----------|--------|
| Uncommitted changes | Prompt: stash/commit/discard/abort |
| No story found | STOP with helpful message |
| Story done/review not merged | STOP: "Merge PR first" |
| Dependencies incomplete | STOP with list of blockers |
| Git command fails | STOP with error |
| Worktree exists for story | cd into it (resume mode) |

---

## Build Summary

### Files Created

| File | Path | Purpose |
|------|------|---------|
| workflow.yaml | `.bmad/bmm/workflows/4-implementation/dev-begin/workflow.yaml` | Configuration and variables |
| instructions.xml | `.bmad/bmm/workflows/4-implementation/dev-begin/instructions.xml` | Main workflow logic (7 steps) |
| workflow-plan.md | `.bmad/bmm/workflows/4-implementation/dev-begin/workflow-plan.md` | Planning document (this file) |

### Implementation Notes

- Single `instructions.xml` approach matching dev-story pattern
- 7 internal steps with XML structure
- Only Step 1 requires user input (uncommitted changes)
- All other steps are autonomous with informational output
- Uses goto/anchor pattern for flow control
- Integrates with sprint-status.yaml for status tracking
- Hands off to dev-story workflow at completion

### Next Steps

1. Review the generated workflow files
2. Test with a sample story
3. Update dev-story to remove redundant git/branch logic
4. Add workflow to available commands if needed

---

## Review Summary

### Validation Results

| Check | Status |
|-------|--------|
| File Structure | PASSED |
| Configuration | PASSED |
| Step Compliance | PASSED |
| Cross-File Consistency | PASSED |
| Requirements Verification | PASSED |
| Best Practices | PASSED |

### Workflow Status: COMPLETE

**Location:** `.bmad/bmm/workflows/4-implementation/dev-begin/`

**Invocation:** `/bmad:bmm:workflows:dev-begin`

### Recommended Testing

1. Fresh start on staging - let it find next ready-for-dev story
2. Resume on existing story/* branch
3. Worktree creation with "Can Parallel With" story
4. Dependency blocking test
5. Done/review story handling
