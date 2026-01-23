---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: complete
---

# Workflow Creation Plan: create-epic

## Initial Project Context

- **Module:** BMM (BMAD Method)
- **Target Location:** `bmad-custom-src/workflows/create-epic/`
- **Created:** 2025-12-09
- **Author:** Ivo

## Problem Statement

The current `create-story` workflow only creates one story at a time. This requires multiple manual invocations and lacks cross-story context. Key missing capabilities:

1. **Batch Story Creation** - Cannot create all stories in an epic at once
2. **Dependency Tracking** - Stories don't know which other stories they depend on
3. **Parallelization Visibility** - No way to see which stories can run in parallel
4. **Epic-Level View** - No flowchart or visualization of story relationships

## Proposed Solution

Create a `create-epic` workflow that:

1. Takes an epic (from epics.md) that doesn't have story files created yet
2. Analyzes all stories in that epic for dependencies
3. Creates ALL story files by **invoking the existing `create-story` workflow** for each
4. Adds dependency metadata to each story file
5. Generates a parallelization flowchart for the epic

---

## Requirements (Gathered in Step 2)

### 1. Workflow Classification
- **Type:** Meta-Workflow (orchestrates other workflows)
- **Pattern:** Linear, autonomous execution

### 2. Input Requirements
- **Required Input:** Epic number (passed as command argument, e.g., `/create-epic 2`)
- **Source Files:**
  - `epics.md` - Contains epic definitions with story outlines
  - Existing `create-story` workflow at `_bmad/bmm/workflows/4-implementation/create-story/`

### 3. Output Specifications
- **Primary Outputs:**
  - Multiple story files (one per story in the epic)
  - ASCII flowchart showing dependency graph and parallelization opportunities
- **Flowchart Location:** Embedded in `epics.md` under the relevant epic section
- **Story File Additions:** Each story file will include a Dependencies section:
  ```markdown
  ## Dependencies

  - **Depends On:** [Story 2.1, Story 2.3]
  - **Blocks:** [Story 2.5]
  - **Can Parallel With:** [Story 2.2, Story 2.4]
  ```

### 4. User Interaction Style
- **Fully Autonomous** - No user input required during execution
- User can review results at the end and make adjustments if needed
- Epic number is the only required input (passed as argument)

### 5. Dependency Analysis
- **AI-Driven** - Workflow infers dependencies from story content
- No user confirmation required during analysis
- User reviews final output

### 6. Flowchart Format
- **ASCII Art** - Simple, readable by humans and AI
- No external tools or formats required
- Shows which stories can run in parallel vs. must be sequential

### 7. Instruction Style
- **Intent-based** for analysis step (AI reasons about dependencies)
- **Prescriptive** for output formats (consistent story files and flowchart)

### 8. Key Integration Requirement
- **MUST reuse** the existing `create-story` workflow (invoke it, not copy it)
- Preserves any modifications already made to `create-story`
- `create-epic` acts as an orchestrator that calls `create-story` for each story

### 9. Success Criteria
- All stories for the epic are created with proper formatting
- Dependencies are accurately inferred from story content
- ASCII flowchart clearly shows parallel vs. sequential execution paths
- No manual intervention required during execution
- Existing `create-story` workflow is reused (not duplicated)

---

## Tools Configuration

### Core BMAD Tools
- **Party-Mode**: Excluded - Not needed for autonomous execution
- **Advanced Elicitation**: Excluded - No user review points during execution
- **Brainstorming**: Excluded - Dependencies are inferred, not brainstormed

### LLM Features
- **Web-Browsing**: Excluded - All data comes from local `epics.md`
- **File I/O**: **Included** - Read `epics.md`, write story files, create flowchart
- **Sub-Agents**: **Included** - Invoke `create-story` workflow for each story
- **Sub-Processes**: Excluded - Sequential execution preferred for cleaner output

### Memory Systems
- **Sidecar File**: Excluded - Single-run workflow, no session continuity needed

### External Integrations
- None required - all operations are local file-based

### Installation Requirements
- No additional installations required
- All tools are built-in LLM capabilities

---

## Output Format Design

### Format Type: Structured

### Output 1: Dependencies Section (added to each story file)

**Location:** Appended to each story file after creation

**Format:**
```markdown
## Dependencies

- **Depends On:** Story X.Y, Story X.Z
- **Blocks:** Story X.W
- **Can Parallel With:** Story X.A, Story X.B

### Dependency Rationale
- Story X.Y: [concise reason - 1 line max]
- Story X.Z: [concise reason - 1 line max]
```

**Rules:**
- Rationale must be concise (one line per dependency)
- Only include non-empty fields (omit "Blocks" if none)

### Output 2: ASCII Flowchart (added to epics.md)

**Location:** Embedded in `epics.md` under the relevant epic section

**Format Style:** Wave-based box diagram with parallel tracks

**Example Template:**
```
## Epic X: Dependency Flowchart

╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [X-1] Story Title                                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After X-1 (PARALLEL)                                     ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [X-2] Story A Title          ║     [X-3] Story B Title           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Design Rules:**
- Use double-line box characters (╔ ╗ ╚ ╝ ═ ║)
- Group parallel stories in same WAVE box
- Label waves with dependencies (e.g., "After X-1")
- Note parallel count when >2 stories (e.g., "PARALLEL x6")
- Use │ and ▼ for flow connections between waves
- Split into parallel tracks (side-by-side boxes) when dependency chains diverge
- Story format: [Epic-Story] Story Title (e.g., [3-2] Basic Value Extraction)

---

## Workflow Structure Design

### Overview
- **Steps:** 3 (linear, autonomous)
- **Continuation Support:** No - runs to completion
- **Error Handling:** Skip failed stories, continue with others, report all errors at end

### Step 1: Initialize & Analyze (`step-01-init`)

**Goal:** Load the specified epic and analyze story dependencies

**Actions:**
1. Accept epic number from command argument
2. Load `epics.md` and extract the specified epic
3. Identify all stories in the epic
4. Analyze dependencies between stories (AI-driven inference)
5. Build dependency graph in memory
6. Auto-proceed to Step 2

**Interaction:** None - auto-proceeds after analysis

### Step 2: Generate Stories (`step-02-generate`)

**Goal:** Create all story files by invoking `create-story` workflow

**Actions:**
1. For each story in the epic (sequentially):
   - Invoke the existing `create-story` workflow at `_bmad/bmm/workflows/4-implementation/create-story/`
   - Pass story context (epic number, story number, title, acceptance criteria)
   - Wait for completion
   - If error: log error, continue to next story
2. Track which stories succeeded/failed
3. Auto-proceed to Step 3 when loop completes

**Interaction:** None - loops autonomously

### Step 3: Finalize (`step-03-finalize`)

**Goal:** Add dependencies and generate flowchart

**Actions:**
1. For each successfully created story file:
   - Append the Dependencies section with rationale
2. Generate ASCII flowchart (wave-based format) from dependency graph
3. Insert flowchart into `epics.md` under the epic section
4. Display completion summary:
   - Stories created successfully
   - Stories that failed (if any)
   - Flowchart location
5. End workflow

**Interaction:** None - displays summary and ends

### File Structure

```
bmad-custom-src/workflows/create-epic/
├── workflow.md                    # Main workflow config
├── steps/
│   ├── step-01-init.md           # Load & analyze dependencies
│   ├── step-02-generate.md       # Create stories via create-story
│   └── step-03-finalize.md       # Add dependencies & flowchart
└── workflow-plan-create-epic.md  # This planning document
```

### Data Flow

```
[Epic Number Arg]
       │
       ▼
┌─────────────────┐
│ Step 1: Init    │ ──► Read epics.md ──► Build dependency graph
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Step 2: Generate│ ──► Loop: invoke create-story for each ──► Story files created
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ Step 3: Finalize│ ──► Append dependencies ──► Generate flowchart ──► Update epics.md
└─────────────────┘
       │
       ▼
[Completion Summary]
```

### AI Role

- **Role:** Autonomous orchestrator and dependency analyst
- **Tone:** Minimal output during execution, clear summary at end
- **Expertise:** Story dependency inference, parallel execution planning

---

## Build Summary (Step 7)

### Files Created

| File | Path | Purpose |
|------|------|---------|
| `workflow.md` | `bmad-custom-src/workflows/create-epic/workflow.md` | Main workflow configuration |
| `step-01-init.md` | `bmad-custom-src/workflows/create-epic/steps/step-01-init.md` | Load epic & analyze dependencies |
| `step-02-generate.md` | `bmad-custom-src/workflows/create-epic/steps/step-02-generate.md` | Create stories via create-story |
| `step-03-finalize.md` | `bmad-custom-src/workflows/create-epic/steps/step-03-finalize.md` | Add dependencies & flowchart |

### Directory Structure

```
bmad-custom-src/workflows/create-epic/
├── workflow.md
├── workflow-plan-create-epic.md
└── steps/
    ├── step-01-init.md
    ├── step-02-generate.md
    └── step-03-finalize.md
```

### Build Notes

- No templates created (reuses existing `create-story` workflow)
- No continuation support (runs to completion)
- All step files follow BMAD step-file architecture
- Auto-proceed pattern used (no user menus during execution)

### Next Steps for Testing

1. Ensure `epics.md` exists with epic definitions
2. Invoke with: `/create-epic N` (where N is the epic number)
3. Verify story files are created in sprint_artifacts folder
4. Check Dependencies section appended to each story
5. Verify flowchart inserted in epics.md

---

## Review Summary (Step 8)

### Validation Results

| Category | Result |
|----------|--------|
| Configuration validation | PASSED |
| Step compliance | PASSED |
| Cross-file consistency | PASSED |
| Requirements verification | PASSED |

### Issues Found
- **Critical Issues:** None
- **Warnings:** None
- **Suggestions:** None

### Final Approval
- **Status:** APPROVED
- **Date:** 2025-12-09
- **Reviewer:** create-workflow automation

---

## Completion (Step 9)

### Workflow Location
`bmad-custom-src/workflows/create-epic/`

### Invocation Command
```
/create-epic N
```
Where N is the epic number (e.g., `/create-epic 2`)

### Prerequisites
- `epics.md` must exist in output folder with epic definitions
- `create-story` workflow available at `_bmad/bmm/workflows/4-implementation/create-story/`

### Expected Outputs
1. Story files in sprint_artifacts folder (one per story)
2. Dependencies section appended to each story file
3. ASCII flowchart inserted into epics.md under the epic section
