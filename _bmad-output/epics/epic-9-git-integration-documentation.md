# Epic 9: Git Integration & Documentation

**Goal:** Support git workflows through hooks (feature branches, commits) and generate PR-ready documentation in the Document phase.

## Story 9.1: Create Feature Branch via Pre-Hook

As a user,
I want a feature branch created automatically when a run starts,
So that my work is isolated from the main branch.

**Acceptance Criteria:**

**Given** git integration enabled in project.yaml
**When** run starts
**Then** the bundled pre-hook creates branch `feature/<sanitized-feature-name>`

**Given** feature name "Add user authentication"
**When** branch name is generated
**Then** it becomes `feature/add-user-authentication`

**Given** the branch already exists
**When** pre-hook runs
**Then** it switches to the existing branch instead of failing

**Given** uncommitted changes exist
**When** branch creation is attempted
**Then** HookError is raised with suggestion to commit or stash

**Given** git integration disabled
**When** run starts
**Then** no branch operations occur

---

## Story 9.2: Stage and Commit Changes via Post-Hook

As a user,
I want changes automatically staged and committed after each phase,
So that my work is preserved incrementally.

**Acceptance Criteria:**

**Given** Build phase completes successfully
**When** post-hook runs
**Then** changed files are staged and committed with message "[adw] Build: <feature>"

**Given** commit message template
**When** generating
**Then** it includes: phase name, feature description, run_id reference

**Given** no changes to commit
**When** post-hook runs
**Then** commit is skipped silently (not an error)

**Given** commit fails (e.g., pre-commit hook rejects)
**When** post-hook runs
**Then** HookError is raised with the failure details

**Given** auto-commit disabled in project.yaml
**When** phase completes
**Then** no commit is made

---

## Story 9.3: Capture Git Diff as Artifact

As a developer,
I want the git diff captured as a Build phase artifact,
So that changes can be reviewed and included in PR description.

**Acceptance Criteria:**

**Given** Build phase completes
**When** artifacts are captured
**Then** `git diff HEAD~1` output is saved to `artifacts/build/diff.txt`

**Given** the diff artifact
**When** accessed by Document phase
**Then** it's available as `{{artifacts.build.diff}}`

**Given** diff is very large (>100KB)
**When** capturing
**Then** it's truncated with summary of total lines changed

**Given** no commits made during Build
**When** diff is captured
**Then** staged changes diff is captured instead

---

## Story 9.4: Generate PR Description

As a user,
I want a PR-ready description generated,
So that I can quickly create a pull request.

**Acceptance Criteria:**

**Given** Document phase executes
**When** LLM generates output
**Then** it produces structured PR description with: Summary, Changes, Testing, Screenshots (if applicable)

**Given** the PR description
**When** saved as artifact
**Then** it's at `artifacts/document/pr_description.md`

**Given** evidence manifest from Verify phase
**When** generating PR description
**Then** relevant evidence items are referenced

**Given** run completion panel
**When** displayed
**Then** it includes link to generated PR description artifact

---

## Story 9.5: Support PR Creation Command

As a user,
I want to create a PR directly from the completed run,
So that I can quickly share my work for review.

**Acceptance Criteria:**

**Given** command `adw pr <run_id>`
**When** run is complete
**Then** it opens PR creation with pre-filled title and description

**Given** GitHub CLI (gh) is available
**When** pr command runs
**Then** it uses `gh pr create` with generated description

**Given** gh is not available
**When** pr command runs
**Then** it outputs the description and instructions for manual PR

**Given** run is not complete
**When** pr command is attempted
**Then** ConfigError is raised with "Run must be complete to create PR"

**Given** pr creation succeeds
**When** complete
**Then** PR URL is displayed and stored in run artifacts

---

## Epic 9: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately (PARALLEL x2)                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [9-1] Create Feature Branch    ║    [9-3] Capture Git Diff      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
            │                                    │
            ▼                                    │
╔═══════════════════════════════╗                │
║  WAVE 2: After 9-1            ║                │
╠═══════════════════════════════╣                │
║                               ║                │
║  [9-2] Stage and Commit       ║                │
║                               ║                │
╚═══════════════════════════════╝                │
            │                                    │
            └──────────────┬─────────────────────┘
                           ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 9-2 AND 9-3                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [9-4] Generate PR Description                                    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                           │
                           ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 9-4                                                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [9-5] Support PR Creation Command                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

**Wave Summary:**
- **Wave 1:** 9-1, 9-3 (can run in parallel - no dependencies)
- **Wave 2:** 9-2 (depends on 9-1)
- **Wave 3:** 9-4 (depends on both 9-2 and 9-3)
- **Wave 4:** 9-5 (depends on 9-4)
