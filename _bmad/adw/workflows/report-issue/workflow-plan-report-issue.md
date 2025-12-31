---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: complete
---

# Workflow Creation Plan: report-issue

## Initial Project Context

- **Module:** bmm (BMAD Method)
- **Target Location:** `{project-root}/_bmad/bmm/workflows/4-implementation/report-issue/`
- **Slash Command:** `/report-issue` (to be created in `.claude/commands/`)
- **Created:** 2025-12-10
- **Requested By:** Ivo

## Workflow Overview

**Name:** `report-issue`
**Purpose:** Capture, document, and route QA issues found during manual testing with structured tracking and automatic story generation.

---

## Gathered Requirements

### 1. Workflow Purpose and Scope

- **Problem Solved:** Captures QA issues found during manual testing in a structured, trackable format
- **Primary Users:** QA engineers, developers, product owners
- **Main Outcome:** Documented issue with clear path to resolution, integrated into sprint tracking

### 2. Workflow Type Classification

- **Type:** Action Workflow with Interactive elements
- Creates files, updates tracking, prompts for details
- Branching based on severity for story generation

### 3. Flow Pattern

**Linear with Branching:**
- Steps 1-4: Linear (describe → classify → document → track)
- Step 5: Branch based on severity (Critical/Major → create-story, Minor → backlog only)

### 4. User Interaction Style

- **Prescriptive prompts** for severity, type, reproduction steps
- Ensures consistent issue capture across reporters
- Clear decision points at severity classification

### 5. Instruction Style

- **Prescriptive** - specific prompts and templates for consistency
- Fixed fields ensure all issues have comparable information

### 6. Input Requirements

**Required:**
- Issue description
- Reproduction steps
- Severity (Critical/Major/Minor)
- Type (Bug/UX Issue/Regression)
- Affected component

**Optional:**
- Screenshot paths (will be copied to assets folder)
- Log file paths (will be copied to assets folder)
- Related Epic/Story
- Workaround

**Pre-filled Defaults (from project context):**
- OS: Windows 10/11
- App: text-extractor (version from git)
- Reporter: {user_name} from config

### 7. Output Specifications

**Primary Outputs:**
1. Issue file: `docs/sprint-artifacts/issues/ISS-{number}-{short-description}.md`
2. Updated `sprint-status.yaml`:
   - New `issues` section with issue status
   - New `issue_counter` field for auto-increment
   - For Critical/Major: adds bugfix/ux-fix entry to `development_status`

**For Critical/Major Issues:**
- Prompts user to run `create-story` workflow for the bugfix
- Story key format: `bugfix-ISS-{number}-{short-description}` or `ux-fix-ISS-{number}-{short-description}`

### 8. Success Criteria

- Issue documented with all required fields
- Issue tracked in sprint-status.yaml
- Clear next steps provided based on severity
- For Critical/Major: pathway to story creation is clear

---

## Technical Specifications

### Issue Counter Storage

Store in `sprint-status.yaml`:
```yaml
issue_counter: 3  # Next issue will be ISS-004
```

### Issues Directory

Create `docs/sprint-artifacts/issues/` if it doesn't exist.

### Screenshot/Evidence Management

When user provides paths to screenshots or log files:

1. Create `docs/sprint-artifacts/issues/assets/` if it doesn't exist
2. Copy provided files to assets folder with naming: `ISS-{number}-{original-filename}`
3. Update issue file with relative paths: `![description](./assets/ISS-{number}-filename.png)`

**Example:**
- User provides: `/tmp/screenshot.png`
- Copied to: `docs/sprint-artifacts/issues/assets/ISS-001-screenshot.png`
- In issue file: `![Screenshot](./assets/ISS-001-screenshot.png)`

### Sprint Status Integration

```yaml
# Issue counter
issue_counter: 0

# Issues tracking
issues:
  ISS-001-app-crash-on-extract: resolved
  ISS-002-parameter-chip-not-visible: in-progress

# Development status (bugfix stories added here)
development_status:
  # ... existing stories ...
  bugfix-ISS-001-app-crash-on-extract: done
  ux-fix-ISS-002-parameter-chip-not-visible: in-progress
```

### Create-Story Integration

For Critical/Major issues, after creating the issue file:
1. Add bugfix/ux-fix entry to `development_status` with status `backlog`
2. Prompt user: "Run `/bmad:bmm:workflows:create-story bugfix-ISS-XXX` to create the fix story?"
3. User can immediately create the story or defer

---

## Workflow Steps (Detailed)

| Step | Action                       | Output                                              |
|------|------------------------------|-----------------------------------------------------|
| 1    | User describes issue         | Classification (severity, type)                     |
| 2    | Workflow prompts for details | Reproduction steps, impact, environment             |
| 3    | Create issue file            | docs/sprint-artifacts/issues/ISS-XXX-description.md |
| 4    | Update sprint-status.yaml    | Issue added to tracking, counter incremented        |
| 5    | Route based on severity      | Critical/Major → add bugfix entry, prompt for story |
| 6    | Summary                      | Issue ready for triage, next steps provided         |

## Severity Routing Rules

| Severity | Impact | Action |
|----------|--------|--------|
| Critical | App crash, data loss, complete feature failure | Add `bugfix-ISS-XXX` to development_status, prompt to run create-story |
| Major | Significant UX problems, hard to use | Add `ux-fix-ISS-XXX` to development_status, prompt to run create-story |
| Minor | Polish, minor annoyances | Log to issues only, address in Epic 7 or polish sprint |

## Issue File Template

```markdown
# Issue: {Title}

**ID:** ISS-{number}
**Severity:** Critical | Major | Minor
**Type:** Bug | UX Issue | Regression
**Status:** reported | triaging | in-progress | resolved | verified
**Reported:** {date}
**Reporter:** {name}

## Related
- **Epic:** {epic number or "N/A"}
- **Story:** {story number or "N/A"}
- **Component:** {e.g., "Parameter Input", "Extraction Engine", "Document Panel"}

## Description
{Clear description of the issue}

## Reproduction Steps
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Expected Behavior
{What should happen}

## Actual Behavior
{What actually happens}

## Impact
{How this affects the user / blocks functionality}

## User Impact Score
- **Users Affected:** {estimate}
- **Frequency:** {how often users hit this}

## Workaround
{Temporary way around the issue, or "None"}

## Environment
- **OS:** Windows 10/11
- **App Version:** {version or commit}
- **DPI Scaling:** {100%, 125%, 150%}

## Evidence
- Screenshots:
  - ![Description](./assets/ISS-{number}-filename.png)
  - {or "N/A" if none provided}
- Logs:
  - [Log file](./assets/ISS-{number}-logfile.txt)
  - {or "N/A" if none provided}
- Screen recording: {path or "N/A"}

## Resolution
- **Fix Story:** {bugfix-ISS-xxx.md or ux-fix-ISS-xxx.md or "N/A - Minor"}
- **Fixed In:** {commit hash or "Pending"}
- **Verified By:** {name or "Pending"}
- **Verified Date:** {date or "Pending"}

## Notes
{Any additional context}
```

## Resolution Workflow (Post-Report)

1. Developer picks up bugfix/ux-fix story (created via create-story workflow)
2. Implements fix using `dev-story` workflow
3. Runs code review via `/codex-review`
4. QA verifies fix against reproduction steps
5. Update issue status to `verified` in sprint-status.yaml
6. Close linked story

## Triage Ownership

- **Initial Classification:** Reporter assigns based on judgment
- **Final Authority:** Product Owner has final say
- **Review Cadence:** Daily standup or async review catches misclassified issues
- **Re-classification:** Update severity in issue file and move linked story if needed

## Integration Points

- **create-story workflow:** Invoked for Critical/Major issues to create bugfix/ux-fix stories
- **dev-story workflow:** Used by developers to implement fixes
- **code-review workflow:** For reviewing fix implementations
- **sprint-status.yaml:** Central tracking for issues and related fix stories

---

## Tools Configuration

### Core BMAD Tools

- **Party-Mode**: Excluded - Not needed for structured data capture workflow
- **Advanced Elicitation**: Excluded - Prescriptive prompts, not exploratory
- **Brainstorming**: Excluded - Fixed workflow, not ideation

### LLM Features

- **Web-Browsing**: Excluded - All data is local project files
- **File I/O**: **Included** - Required for creating issue files and updating sprint-status.yaml
- **Sub-Agents**: Excluded - Simple linear workflow
- **Sub-Processes**: Excluded - No parallel processing required

### Memory Systems

- **Sidecar File**: Excluded - No session continuity required

### External Integrations

- None required

### Installation Requirements

- No additional installations required
- **User Installation Preference**: N/A
- **Alternative Options**: N/A

---

## Output Format Design

**Format Type**: Structured

**Output Requirements**:
- Document type: Issue report (markdown)
- File format: `.md` (Markdown)
- Frequency: Single file per issue

**Structure Specifications**:
- Required sections with specific fields
- Flexible content within each section
- Consistent format across all issues for comparability

**Template Information**:
- Template source: Created from retro discussion (already in plan)
- Template file: Will be `template.md` in workflow folder
- Placeholders: `{Title}`, `{number}`, `{date}`, `{name}`, etc.

**Special Considerations**:
- Screenshots/logs copied to assets folder with relative paths
- Issue counter auto-incremented from sprint-status.yaml
- Pre-filled defaults for environment fields

---

## Workflow Structure Design

### Architecture Decision

**Single-file instructions** (like create-story workflow) - simpler for this linear action workflow.

### File Structure

```
_bmad/bmm/workflows/4-implementation/report-issue/
├── workflow.yaml          # Workflow configuration
├── instructions.xml       # Main workflow instructions
├── template.md            # Issue file template
└── checklist.md           # Validation checklist
```

### Continuation Support

**Not needed** - This is a quick-capture workflow (2-5 minutes) that should complete in a single session.

### Workflow Steps (within instructions.xml)

| Step | Name | Purpose | User Input | AI Action |
|------|------|---------|------------|-----------|
| 1 | Init | Load config, read sprint-status.yaml, get issue counter | None | Auto-proceed |
| 2 | Capture | Gather issue details | Description, severity, type, repro steps, component, evidence paths | Prescriptive prompts |
| 3 | Document | Create issue file, copy assets, update tracking | Confirm details | Create files |
| 4 | Route | Branch by severity, show summary | Optional: run create-story | Show next steps |

### Data Flow

```
sprint-status.yaml → [read issue_counter] → Step 1
                                              ↓
User input → [severity, type, description...] → Step 2
                                              ↓
Step 2 data → [create ISS-XXX.md, copy assets] → Step 3
                                              ↓
severity → [branch: Critical/Major adds bugfix entry] → Step 4
                                              ↓
                                        [summary + next steps]
```

### Interaction Pattern

- Steps 1, 3, 4: Auto-proceed (action steps, not collaborative)
- Step 2: Prescriptive prompts for each required field

### Role Definition

- **Role:** QA Issue Reporter / Documentation Assistant
- **Tone:** Efficient, professional, prescriptive
- **Style:** Quick prompts, minimal conversation, focused on accurate data capture

### Validation Checklist

- Required fields provided (description, severity, type, component)
- Screenshot paths validated before copying
- Issue counter incremented correctly
- sprint-status.yaml updated with issue entry
- For Critical/Major: bugfix/ux-fix entry added to development_status

### Slash Command

Create `/report-issue` command in `.claude/commands/report-issue.md` that invokes the workflow.

---

## Build Summary

### Files Generated

| File | Path | Purpose |
|------|------|---------|
| workflow.yaml | `_bmad/bmm/workflows/4-implementation/report-issue/workflow.yaml` | Workflow configuration |
| instructions.xml | `_bmad/bmm/workflows/4-implementation/report-issue/instructions.xml` | Main workflow instructions (4 steps) |
| template.md | `_bmad/bmm/workflows/4-implementation/report-issue/template.md` | Issue file template |
| checklist.md | `_bmad/bmm/workflows/4-implementation/report-issue/checklist.md` | Validation checklist |
| report-issue.md | `.claude/commands/report-issue.md` | Slash command |

### Build Date
2025-12-10

### Testing Instructions

1. Run `/report-issue` to start the workflow
2. Test with each severity level (Critical, Major, Minor)
3. Verify issue file created in `docs/sprint-artifacts/issues/`
4. Verify sprint-status.yaml updated correctly
5. Test screenshot copying by providing a valid image path
6. For Critical/Major, verify bugfix/ux-fix entry added to development_status

---

## Review Summary

### Validation Results

| Validation | Result |
|------------|--------|
| Configuration validation | PASSED |
| Step compliance | PASSED |
| Cross-file consistency | PASSED |
| Requirements verification | PASSED |

### Issues Found

**None** - Workflow is complete and ready for use.

### Recommendations

- Test with real QA issues during next sprint
- Monitor sprint-status.yaml for correct updates
- Consider adding DPI scaling detection in future iteration

---

## Completion Status

**Status:** COMPLETE
**Completed:** 2025-12-10
**Approved By:** Ivo

### Usage

Invoke the workflow with:
```
/report-issue
```

Or with initial description:
```
/report-issue "App crashes when clicking extract button"
```

### Integration Points

- `/bmad:bmm:workflows:create-story` - For creating bugfix/ux-fix stories
- `/bmad:bmm:workflows:dev-story` - For implementing fixes
- `/codex-review` - For code review of fixes
