---
stepsCompleted: [1, 2, 3, 4, 6, 7, 8, 9]
outputDocument: false
status: COMPLETE
completionDate: 2025-12-09
---

# Workflow Creation Plan: code-review-loop

## Initial Project Context

- **Module:** bmm (BMAD Main Method)
- **Target Location:** _bmad/bmm/workflows/4-implementation/code-review-loop/
- **Created:** 2025-12-09
- **Creator:** Ivo

## Problem Statement

Automate the code review and fix cycle. Currently, the code-review process requires manual ping-pong between review and fix cycles. The desired state is an automated loop that runs: review → find issues → fix → re-review until all issues are resolved.

## Primary User

Ivo (expert developer) - for use after completing story implementations.

## Related Workflows

- `code-review` - The existing adversarial code review workflow (reference for review criteria)
- `dev-story` - Story implementation workflow (runs before code-review-loop)

---

## Requirements (Gathered Step 2)

### Workflow Type & Pattern

| Aspect | Decision |
|--------|----------|
| Type | Meta-workflow + Autonomous |
| Pattern | Loop with safety cap |
| Max Iterations | 2 cycles |
| Interaction | Fully autonomous |

### Architecture: Dual-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│  code-review-loop (Main Agent - Opus/Sonnet)                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Spawn Codex agent → "Review this code"           │    │
│  │         ↓                                           │    │
│  │    [Codex returns findings]                         │    │
│  │         ↓                                           │    │
│  │ 2. Main validates: "Is issue X real?"               │    │
│  │    - Check against codebase                         │    │
│  │    - Check against story requirements               │    │
│  │    - Dismiss false positives                        │    │
│  │         ↓                                           │    │
│  │ 3. Fix valid issues                                 │    │
│  │         ↓                                           │    │
│  │ 4. Commit fixes (after each cycle)                  │    │
│  │         ↓                                           │    │
│  │ 5. Loop → spawn Codex again (max 2 cycles)          │    │
│  │         ↓                                           │    │
│  │ 6. Exit when clean OR cap reached                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Why Dual-Agent

- Codex reviews with fresh eyes each time (no memory of previous cycles)
- Main agent validates findings - prevents hallucinated issues
- Natural exit: Codex finds nothing OR Main validates nothing as real
- No infinite loop risk

### Validation Criteria

Main agent validates issues against:
1. Codebase (does the issue actually exist in the code?)
2. Story requirements (is this relevant to acceptance criteria?)

### Exit Conditions

- Codex finds 0 issues, OR
- Main validates 0 issues as real, OR
- Max 2 cycles reached

### Input Requirements

| Input | Source | Required |
|-------|--------|----------|
| Story file | Sprint artifacts folder | Yes |
| Code changes | Git diff / file list | Yes |
| Architecture | docs/architecture.md | Yes |
| Project context | project-context.md | Optional |

### Output Requirements

1. **Terminal Summary** (inline, not a file):
   - Issues fixed (with short fix descriptions)
   - Issues skipped/dismissed (with reasons)
   - Manual validation checklist for full story

2. **Story Status Update**
   - Update story file status to "done"

3. **PR Creation**
   - Always create PR at end (via `gh pr create`)
   - Even if max cycles reached with issues remaining

**Note:** No output document/file - all reporting is inline terminal output.

### Commit Strategy

- Commit after EACH fix cycle (not just at end)
- This creates checkpoint commits for each review round

### Instruction Style

- Prescriptive for the loop control logic
- Intent-based for validation decisions

### Success Criteria

- All valid issues identified and fixed
- No hallucinated issues acted upon
- Story marked done
- PR created with comprehensive summary
- Clean git history with per-cycle commits

---

## Tools Configuration (Step 3)

### Core BMAD Tools

| Tool | Included | Rationale |
|------|----------|-----------|
| Party-Mode | No | Autonomous workflow, not collaborative |
| Advanced Elicitation | No | Validation is code-based, not elicitation |
| Brainstorming | No | Execution workflow, not ideation |

### LLM Features

| Feature | Included | Use Case |
|---------|----------|----------|
| Web-Browsing | No | All data is local |
| File I/O | **Yes** | Read code, edit files, update story status |
| Sub-Agents | **Yes** | Spawn Codex for adversarial review |
| Sub-Processes | No | Sequential flow, not parallel |

### Memory Systems

| System | Included | Rationale |
|--------|----------|-----------|
| Sidecar File | No | Each run is independent/self-contained |

### External Integrations

| Integration | Method | Rationale |
|-------------|--------|-----------|
| Git operations | Bash (git CLI) | No installation required |
| PR creation | Bash (gh CLI) | No installation required |

### Installation Requirements

- **None** - All tools are built-in or already available
- No MCP servers required
- Uses standard git and gh CLI commands

---

## Workflow Design (Step 6)

### Architecture: Step-File (3 Steps)

```
code-review-loop/
├── workflow.md              # Main entry point
├── workflow-plan-*.md       # This plan
└── steps/
    ├── step-01-init.md      # Load story, context, init counters
    ├── step-02-loop.md      # Review→Validate→Fix→Commit loop
    └── step-03-finalize.md  # Update status, create PR, summary
```

### Step 1: Initialize (`step-01-init.md`)

**Goal:** Load context and prepare for review loop

**Actions:**
1. Load story file from sprint-artifacts (auto-detect from branch)
2. Read story acceptance criteria and dev notes
3. Identify code changes (git diff against base branch)
4. Load architecture/project context
5. Initialize cycle counter = 0
6. Initialize tracking arrays (issues_fixed, issues_skipped)
7. Auto-proceed to step 2

**Interaction:** None (auto-proceed)

### Step 2: Review Loop (`step-02-loop.md`)

**Goal:** Execute review→validate→fix→commit cycle (max 2 times)

**Actions:**
1. Increment cycle counter
2. **Run Codex via `/codex-review` (report-only mode):**
   ```bash
   codex exec --full-auto \
     -c 'headless=true' \
     -c 'auto_fix_mode="report-only"' \
     "Run the /bmad:bmm:workflows:code-review workflow on the current branch"
   ```
   Note: Do NOT specify a model with `-m` flag - use Codex's configured default.
3. **Parse Codex output** for findings
4. **Main validates each finding:**
   - Read relevant code
   - Check against story requirements
   - Classify as VALID or FALSE_POSITIVE
5. **If valid issues exist:**
   - Fix each valid issue
   - Track in issues_fixed array
   - Track skipped in issues_skipped array
   - Commit: `git add -A && git commit -m "fix(review): cycle {N} - {summary}"`
6. **Check exit conditions:**
   - If no valid issues → proceed to step 3
   - If cycle >= 2 → proceed to step 3
   - Otherwise → loop back to action 1

**Interaction:** None (auto-loop)

### Step 3: Finalize (`step-03-finalize.md`)

**Goal:** Complete workflow with status update, PR, and summary

**Actions:**
1. Update story file status → "done"
2. Update sprint-status.yaml
3. Create PR: `gh pr create --title "..." --body "..."`
4. Print terminal summary:
   - Total cycles run
   - Issues fixed (with descriptions)
   - Issues skipped (with reasons)
   - Manual validation checklist
5. Report completion

**Interaction:** None (complete)

### Flow Diagram

```
┌─────────────────────────────────────┐
│  step-01-init                       │
│  • Load story + context             │
│  • Identify code changes            │
│  • Initialize counters              │
│  └──────────► auto-proceed          │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  step-02-loop                       │
│  ┌────────────────────────────────┐ │
│  │ 1. Run /codex-review           │ │
│  │ 2. Parse findings              │ │
│  │ 3. Validate each issue         │ │
│  │ 4. Fix valid issues            │ │
│  │ 5. Commit fixes                │ │
│  │ 6. Check: clean OR cycle >= 2? │ │
│  │    NO  → loop back to 1        │ │
│  │    YES → proceed to step 3     │ │
│  └────────────────────────────────┘ │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  step-03-finalize                   │
│  • Update story status → done       │
│  • Create PR                        │
│  • Print summary                    │
│  • Complete                         │
└─────────────────────────────────────┘
```

### Continuation Support

**Not needed** - fully autonomous, single-session workflow.

### Codex Integration

- Uses existing `/codex-review` command
- Runs in `report-only` mode (Codex reports, Main fixes)
- Codex invoked via `codex exec` CLI

---

## Build Summary (Step 7)

### Files Created

| File | Path | Purpose |
|------|------|---------|
| workflow.md | `_bmad/bmm/workflows/4-implementation/code-review-loop/workflow.md` | Main entry point |
| step-01-init.md | `steps/step-01-init.md` | Load story, context, initialize state |
| step-02-loop.md | `steps/step-02-loop.md` | Review→Validate→Fix→Commit loop |
| step-03-finalize.md | `steps/step-03-finalize.md` | Update status, create PR, summary |

### Directory Structure

```
_bmad/bmm/workflows/4-implementation/code-review-loop/
├── workflow.md
├── workflow-plan-code-review-loop.md
└── steps/
    ├── step-01-init.md
    ├── step-02-loop.md
    └── step-03-finalize.md
```

### Key Implementation Details

1. **Autonomous Execution**: All steps auto-proceed without user interaction
2. **Codex Integration**: Uses `codex exec` CLI with `report-only` mode
3. **Validation Logic**: Main agent validates each Codex finding before fixing
4. **Commit Strategy**: Commits after each cycle with descriptive messages
5. **PR Creation**: Always creates PR with detailed summary

### Manual Steps Needed

None - workflow is ready to use.

### Testing the Workflow

1. Checkout a story branch: `git checkout story/{story-key}`
2. Run the workflow: `/bmad:bmm:workflows:code-review-loop`
3. Monitor terminal output for cycle progress
4. Verify PR is created with summary

### Usage

```
/bmad:bmm:workflows:code-review-loop
```

Or invoke via slash command once registered.
