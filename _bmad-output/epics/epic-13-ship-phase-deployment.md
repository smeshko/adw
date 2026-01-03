# Epic 13: Ship Phase & Deployment

**Goal:** Automate PR approval, merge, and project-specific deployment hooks to complete the feature delivery lifecycle.

**Priority:** Post-MVP
**Dependencies:** Epic 9 (Git Integration), Epic 11 (Task Manager Integration)

---

## Story 13.1: Ship Phase Definition

As a developer,
I want a Ship phase that finalizes and delivers my feature,
So that the entire lifecycle from prompt to production is automated.

**Acceptance Criteria:**

**Given** Document phase completes
**When** Ship phase starts
**Then** it validates all prior phases passed

**Given** any prior phase failed
**When** Ship phase attempts to start
**Then** error is raised: "Cannot ship: [PHASE] did not pass"

**Given** Ship phase
**When** configured
**Then** it's optional and can be disabled:
```yaml
phases:
  ship:
    enabled: false  # Disable for manual PR workflow
```

---

## Story 13.2: PR Approval Automation

As a developer,
I want the Ship phase to approve the PR,
So that I don't need to manually click approve.

**Acceptance Criteria:**

**Given** PR exists for the run
**When** Ship phase runs
**Then** `gh pr review --approve` is executed

**Given** approval requires specific reviewers
**When** `auto_approve: false` in config
**Then** approval is skipped, PR left for manual review

**Given** approval fails (permissions, branch protection)
**When** error occurs
**Then** warning logged, Ship continues to next step

**Given** approval succeeds
**When** logged
**Then** approval timestamp and reviewer info stored in artifacts

---

## Story 13.3: PR Merge Automation

As a developer,
I want the Ship phase to merge the PR,
So that my feature is delivered without manual intervention.

**Acceptance Criteria:**

**Given** PR is approved
**When** Ship phase runs with `auto_merge: true`
**Then** PR is merged via `gh pr merge`

**Given** merge strategy
**When** configured
**Then** options are: squash (default), merge, rebase
```yaml
ship:
  merge_strategy: squash
```

**Given** merge conflicts exist
**When** merge is attempted
**Then** error raised with instructions to resolve manually

**Given** branch protection requires checks
**When** checks are pending
**Then** Ship waits up to `merge_timeout` seconds (default: 300)

**Given** merge succeeds
**When** logged
**Then** merge commit SHA and timestamp stored in artifacts

---

## Story 13.4: Project-Specific Deployment Hooks

As a developer,
I want to run custom deployment commands after merge,
So that my feature is deployed to the appropriate environment.

**Acceptance Criteria:**

**Given** post-merge hooks configured
**When** merge succeeds
**Then** hooks execute in order:
```yaml
ship:
  post_merge_hooks:
    - command: "npm run deploy:staging"
      name: "Deploy to Staging"
    - command: "./scripts/notify-team.sh"
      name: "Notify Team"
```

**Given** a hook fails
**When** error occurs
**Then** subsequent hooks still run, failures collected

**Given** hook execution
**When** complete
**Then** all hook outputs stored in `artifacts/ship/hooks/`

**Given** no hooks configured
**When** Ship phase runs
**Then** phase completes after merge (no-op)

---

## Story 13.5: Issue Closing

As a developer,
I want the source task closed after successful ship,
So that my task board reflects completed work.

**Acceptance Criteria:**

**Given** task manager configured
**When** Ship phase completes with merge
**Then** source task is moved to "Done" state

**Given** `auto_close: true` in task_manager_config
**When** task is closed
**Then** closing comment includes: PR link, run ID, artifacts link

**Given** issue closing fails
**When** API error occurs
**Then** warning logged with manual close instructions

---

## Story 13.6: Ship Phase Guards

As a developer,
I want safety checks before shipping,
So that broken code doesn't get merged.

**Acceptance Criteria:**

**Given** Ship phase starts
**When** pre-flight checks run
**Then** these are verified:
- All prior phases completed successfully
- No unresolved validation issues (ERROR severity)
- PR exists and is in mergeable state
- Branch is up to date with target

**Given** any guard fails
**When** checked
**Then** Ship phase aborts with specific failure reason

**Given** `--force-ship` flag
**When** provided
**Then** guards are logged as warnings but not enforced

---

## Configuration

```yaml
# .adw/project.yaml
phases:
  ship:
    enabled: true

ship:
  # PR handling
  auto_approve: true
  auto_merge: true
  merge_strategy: squash        # squash | merge | rebase
  merge_timeout: 300            # Seconds to wait for checks

  # Target branch
  target_branch: main           # Default merge target

  # Deployment hooks
  post_merge_hooks:
    - command: "npm run deploy:staging"
      name: "Deploy to Staging"
      timeout: 600
    - command: "./scripts/notify-team.sh"
      name: "Notify Team"
      continue_on_failure: true

  # Safety
  require_passing_checks: true
  require_up_to_date: true
```

---

## Ship Phase Flow

```
Ship Phase Start
       │
       ▼
[Pre-flight Guards]
       │
       ├── All phases passed? ──────▶ NO ──▶ ABORT
       │
       ├── PR exists? ──────────────▶ NO ──▶ ABORT
       │
       ├── Branch up to date? ──────▶ NO ──▶ ABORT (or auto-rebase)
       │
       ▼
[Approve PR]
       │
       ├── Success ─────────────────▶ Continue
       │
       └── Failure ─────────────────▶ Log warning, continue
       │
       ▼
[Merge PR]
       │
       ├── Success ─────────────────▶ Continue
       │
       └── Failure ─────────────────▶ ABORT with instructions
       │
       ▼
[Post-Merge Hooks]
       │
       ├── Run each hook
       │
       └── Collect results
       │
       ▼
[Close Task]
       │
       ▼
Ship Complete
```

---

## Dependency Flowchart

```
     Story 13.1 (Phase Definition)
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  13.6     13.2     13.4
 Guards   Approve   Hooks
     │        │        │
     └────────┼────────┘
              ▼
     Story 13.3 (Merge)
              │
              ▼
     Story 13.5 (Close Task)
```

---
