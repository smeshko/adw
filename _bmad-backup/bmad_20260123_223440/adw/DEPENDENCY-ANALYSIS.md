# ADW Module Dependency Analysis

**Generated:** 2025-12-29
**Module:** Agent Development Workflows (ADW)
**Source:** Extracted from BMM 4-implementation and bmad-quick-flow workflows

---

## Overview

This document provides a comprehensive analysis of the 12 workflows in the ADW module and their external dependencies on the BMAD system. This analysis determines what files are needed if these workflows are moved to a standalone location.

---

## Module Structure

```
_bmad/adw/
├── config.yaml
├── DEPENDENCY-ANALYSIS.md (this file)
└── workflows/
    ├── code-review/
    ├── code-review-loop/
    ├── create-epic/
    ├── create-story/
    ├── create-tech-spec/
    ├── dev-story/
    ├── document-feature/
    ├── gather-evidence/
    ├── quick-dev/
    ├── report-issue/
    ├── run-tests/
    └── ship/
```

---

## Workflows by Type

### XML-Based Workflows (use workflow.xml core engine)

| Workflow | Description |
|----------|-------------|
| `code-review` | Adversarial code review finding 3-10 issues per story |
| `create-story` | Create user stories from epics with enhanced context |
| `dev-story` | Execute story implementation with red-green-refactor |
| `report-issue` | Capture and document QA issues |
| `quick-dev` | Flexible development with optional planning |
| `create-tech-spec` | Conversational spec engineering |

### Step-File Architecture Workflows (direct markdown execution)

| Workflow | Description |
|----------|-------------|
| `code-review-loop` | Automated review loop with GLM subagent |
| `create-epic` | Create all stories for an epic with dependency analysis |
| `document-feature` | Verify and update project documentation |
| `gather-evidence` | Invoke platform-specific skills for evidence |
| `run-tests` | Run configured tests with auto-fix |
| `ship` | Execute deployment pipeline |

---

## Core Dependencies Required for All Workflows

### 1. BMAD Configuration File

**File:** `_bmad/bmm/config.yaml` (or `_bmad/adw/config.yaml`)

**Variables Required:**
```yaml
user_name: "string"
communication_language: "English"
document_output_language: "English"
user_skill_level: "expert"
planning_artifacts: "{project-root}/_bmad-output/project-planning-artifacts"
implementation_artifacts: "{project-root}/_bmad-output/implementation-artifacts"
output_folder: "{project-root}/_bmad-output"
```

**Used By:** All workflows

### 2. Core Workflow Engine

**File:** `_bmad/core/tasks/workflow.xml`

**Purpose:** Execution governance for XML-based workflows

**Used By:** code-review, create-story, dev-story, report-issue, quick-dev, create-tech-spec

### 3. Project Configuration

**File:** `_bmad/project-config.yaml`

**Sections Used:**
- `ship` - Deployment commands (version_bump, build, publish, post_publish)
- `test` - Test commands (unit, e2e, lint, typecheck, custom)
- `document` - Documentation settings
- `platform` - Platform type (backend, web, ios, android, cli)

**Used By:** gather-evidence, run-tests, ship, document-feature

---

## Workflow-Specific Dependencies

### CODE-REVIEW

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.xml`
- `checklist.md`

**External References:**
- `{implementation_artifacts}/sprint-status.yaml`
- `{output_folder}/*architecture*.md`
- `{output_folder}/*ux*.md`
- `{output_folder}/*epic*.md`
- `**/project-context.md`

**Git Commands Used:**
- `git branch --show-current`
- `git status --porcelain`
- `git diff`, `git diff --cached`
- `git log staging..HEAD --oneline`
- `git diff staging...HEAD`

---

### CODE-REVIEW-LOOP

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-init.md`
- `steps/step-02-loop.md`
- `steps/step-03-finalize.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/.worktrees`
- `{output_folder}/architecture.md`
- `{output_folder}/project-context.md`

**ADW SDK Integration:**
- Environment variable: `ADW_STATE_FILE`
- State fields: `story_id`

**Git Commands Used:**
- `git worktree list --porcelain`
- `git branch --show-current`
- `git merge-base origin/staging HEAD`
- `git diff --name-only`
- `git log --oneline origin/staging..HEAD`

---

### CREATE-STORY

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.xml`
- `template.md`
- `validation-prompt.md`

**External References:**
- `{implementation_artifacts}/sprint-status.yaml`
- `{planning_artifacts}/epics.md`
- `{planning_artifacts}/PRD.md`
- `{planning_artifacts}/architecture.md`
- `{planning_artifacts}/ux.md`
- `{project-root}/.linear`
- `{project-root}/docs/CONDITIONAL_DOCS.md`
- `~/.claude/skills/linear/scripts/`

**Linear Scripts Required:**
```bash
get_teams.py --detailed --json
create_issue.py --title --description --json
update_issue.py <issue_id> --state-id <state_id>
```

**ADW SDK Integration:**
- Environment variables: `ADW_STATE_FILE`, `ADW_ISSUE_BODY`
- State fields: `story_id`, `plan_file`, `linear_issue_id`

---

### CREATE-EPIC

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-init.md`
- `steps/step-02-generate.md`
- `steps/step-03-finalize.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`
- `{output_folder}/epics.md`

**Cross-Workflow Call:**
- Invokes `create-story` for each story in the epic

---

### CREATE-TECH-SPEC

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.md`

**External References:**
- `{project-root}/_bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.yaml`
- `{project-root}/_bmad/core/workflows/party-mode/workflow.md`
- `{project-root}/_bmad/core/tasks/advanced-elicitation.xml`

**Output:**
- `{sprint_artifacts}/tech-spec-{slug}.md`

---

### DEV-STORY

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.xml`
- `checklist.md`

**External References:**
- `{implementation_artifacts}/sprint-status.yaml`
- `{project-root}/docs/CONDITIONAL_DOCS.md`
- `**/project-context.md`
- `{project-root}/_bmad/core/tasks/advanced-elicitation.xml`
- `{project-root}/_bmad/core/workflows/party-mode/workflow.md`
- `~/.claude/skills/linear/scripts/`

**Linear Scripts Required:**
```bash
get_teams.py --detailed --json
update_issue.py <issue_id> --state-id <state_id>
```

**ADW SDK Integration:**
- Environment variable: `ADW_STATE_FILE`
- State fields: `story_id`

**Git Commands Used:**
- `git branch --show-current`
- `git add -A`
- `git commit -m`
- `git rev-parse HEAD`

---

### DOCUMENT-FEATURE

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-init.md`
- `steps/step-02-analyze.md`
- `steps/step-03-update.md`
- `steps/step-04-report.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/_bmad/project-config.yaml`
- `{project-root}/docs/CONDITIONAL_DOCS.md`
- `{project-root}/docs/features/`

---

### GATHER-EVIDENCE

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-execute.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/project-config.yaml`

**Platform-Skill Mapping:**
| Platform | Skill |
|----------|-------|
| backend | `review-backend-service` |
| web | null (future) |
| ios | null (future) |
| android | null (future) |
| cli | null (future) |

---

### QUICK-DEV

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.md`
- `checklist.md`

**External References:**
- `{project-root}/_bmad/bmm/workflows/bmad-quick-flow/create-tech-spec/workflow.yaml`
- `{project-root}/_bmad/core/workflows/party-mode/workflow.md`
- `{project-root}/_bmad/core/tasks/advanced-elicitation.xml`
- `{project-root}/_bmad/bmm/workflows/workflow-status/project-levels.yaml`
- `{project-root}/_bmad/bmm/workflows/workflow-status/init/workflow.yaml`
- `**/project-context.md`

---

### REPORT-ISSUE

**Type:** XML-based
**Files:**
- `workflow.yaml`
- `instructions.xml`
- `template.md`
- `checklist.md`

**External References:**
- `{sprint_artifacts}/issues/`
- `{sprint_artifacts}/issues/assets/`
- `{sprint_artifacts}/sprint-status.yaml`
- `**/project-context.md`

**Output:**
- `{issues_dir}/ISS-{issue_number}-{issue_slug}.md`

---

### RUN-TESTS

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-init.md`
- `steps/step-02-execute.md`
- `steps/step-03-fix.md`
- `steps/step-04-report.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/_bmad/project-config.yaml`

**Project Config Section Required:**
```yaml
test:
  pre_commands: []
  unit: "npm test"
  e2e: "npm run e2e"
  lint: "npm run lint"
  typecheck: "npm run typecheck"
  custom: []
```

---

### SHIP

**Type:** Step-file architecture
**Files:**
- `workflow.md`
- `steps/step-01-init.md`
- `steps/step-02-execute.md`
- `steps/step-03-report.md`

**External References:**
- `{project-root}/_bmad/bmm/config.yaml`
- `{project-root}/_bmad/project-config.yaml`

**Project Config Section Required:**
```yaml
ship:
  type: "npm" | "docker" | "custom"
  version_bump: "npm version patch"
  build: "npm run build"
  publish: "npm publish"
  post_publish: []
  pre_checks: []
```

---

## Cross-Workflow Dependencies

### Inter-Workflow Calls

| Source Workflow | Target Workflow |
|-----------------|-----------------|
| `create-epic` | `create-story` |
| `create-tech-spec` | `quick-dev` |
| `dev-story` | `code-review` (suggested next step) |

### Shared Task References

| Task | Used By |
|------|---------|
| `advanced-elicitation.xml` | create-tech-spec, quick-dev, dev-story, create-story |
| `party-mode/workflow.md` | create-tech-spec, quick-dev, dev-story |

---

## External Tool & Service Integrations

### Linear Integration

**Location:** `~/.claude/skills/linear/scripts/`

**Scripts Required:**
- `get_teams.py` - Get team workflow states
- `create_issue.py` - Create Linear issues
- `update_issue.py` - Update issue state

**Config File:** `.linear` in project root (optional)

**Workflows Using Linear:**
- create-story
- dev-story

### Git/VCS Integration

**Used By:** All workflows

**Key Commands:**
- `git branch --show-current`
- `git status --porcelain`
- `git diff [--cached] [--name-only]`
- `git log [--oneline] <branch>..<branch>`
- `git merge-base <branch1> <branch2>`
- `git worktree list --porcelain`
- `git add -A` / `git commit -m`
- `git rev-parse HEAD`

### ADW SDK Integration

**Environment Variables:**
- `ADW_STATE_FILE` - Path to ADW state JSON
- `ADW_ISSUE_BODY` - Issue body from ADW

**Workflows Using ADW:**
- create-story
- dev-story
- code-review-loop

**State JSON Fields:**
- `story_id`
- `plan_file`
- `linear_issue_id`

---

## Data File Patterns

### Planning Artifacts (`{planning_artifacts}`)

| File | Purpose |
|------|---------|
| `epics.md` | Epic definitions with stories and BDD |
| `PRD.md` | Product requirements (fallback) |
| `architecture.md` | Technical architecture |
| `ux.md` | UX design specifications |
| `CONDITIONAL_DOCS.md` | Feature documentation guide |

### Implementation Artifacts (`{implementation_artifacts}`)

| File/Directory | Purpose |
|----------------|---------|
| `sprint-status.yaml` | Story and epic tracking |
| `stories/*.md` | Individual story files |
| `issues/` | QA issues |
| `issues/assets/` | Screenshots and logs |

---

## Minimum Files for Standalone Migration

To make these workflows work independently:

```
standalone-adw/
├── _bmad/
│   ├── adw/
│   │   ├── config.yaml
│   │   └── workflows/          # All 12 workflows
│   └── core/
│       ├── tasks/
│       │   ├── workflow.xml    # Core execution engine
│       │   └── advanced-elicitation.xml
│       └── workflows/
│           └── party-mode/
│               └── workflow.md
├── _bmad/project-config.yaml   # For run-tests, ship, document-feature
└── .claude/
    └── commands/bmad/adw/workflows/  # Slash commands
```

### External Dependencies (Not Bundled)

| Dependency | Location | Required By |
|------------|----------|-------------|
| Linear Scripts | `~/.claude/skills/linear/scripts/` | create-story, dev-story |
| Git | System PATH | All workflows |
| ADW SDK | Environment variables | create-story, dev-story, code-review-loop |

### Project-Specific Data (Stay in Original Location)

- `epics.md`, `PRD.md`, `architecture.md`, `ux.md`
- `sprint-status.yaml`
- Story files and issue tracking
- `project-context.md`

---

## Path Pattern Reference

### Template Variables

| Pattern | Description |
|---------|-------------|
| `{project-root}` | Project root directory |
| `{config_source}` | Path to config.yaml |
| `{planning_artifacts}` | Planning document directory |
| `{implementation_artifacts}` | Implementation/sprint directory |
| `{output_folder}` | General output directory |
| `{sprint_artifacts}` | Sprint-specific artifacts |
| `{workflow_path}` | Current workflow directory |

### Story Key Patterns

| Pattern | Example |
|---------|---------|
| `{{story_key}}` | `1-2-user-authentication` |
| `{{story_id}}` | `1.2` |
| `{{epic_num}}` | `1` |
| `{{story_num}}` | `2` |

---

## Summary

The ADW module contains 12 implementation-focused workflows that can operate semi-independently but require:

1. **Core BMAD infrastructure** (workflow.xml, tasks, party-mode)
2. **Configuration framework** (config.yaml with standard variables)
3. **Project configuration** (project-config.yaml for CI/CD workflows)
4. **External integrations** (Linear, Git, optional ADW SDK)

All workflows are designed with graceful fallback when optional dependencies are missing.
