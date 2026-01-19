# Story 15.6: PR Merge & Completion

Status: in-progress
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want the PR automatically merged after successful ship,
So that my feature is delivered without manual intervention.

## Acceptance Criteria

**Given** LLM outputs `PR_MERGE_APPROVED: true`
**When** post.sh runs
**Then** it parses the status and proceeds with merge

**Given** merge strategy configured
**When** PR is merged
**Then** strategy is used: squash (default), merge, or rebase
```yaml
ship:
  pr:
    merge_strategy: squash
```

**Given** PR merge succeeds
**When** post.sh completes
**Then**:
- Merge commit includes "Shipped via ADW" message
- If version deployed, message includes version number
- Branch is deleted if `pr.delete_branch: true`

**Given** `ship.pr.auto_merge: false`
**When** post.sh runs
**Then** PR is left for manual merge, success logged

**Given** task manager configured
**When** ship completes with merge
**Then** source task is moved to "Done" state (existing Epic 12 integration)

**Given** merge fails
**When** error occurs
**Then** exit code 1, error message with manual merge instructions

## Tasks / Subtasks

### Task 1: Define Finalization Instructions (Step 6 in instructions.xml)
- [x] Create step 6 in `ship/instructions.xml` for finalization
- [x] Input: deployment status from steps 3/5
- [x] Determine PR_MERGE_APPROVED based on status
- [x] Set final status fields for post.sh parsing

### Task 2: Implement post.sh Status Parsing
- [ ] Parse ship_report.md for structured fields:
  - `DEPLOYMENT_STATUS: SUCCESS|FAILED|BLOCKED`
  - `PR_MERGE_APPROVED: true|false`
  - `VERSION_DEPLOYED: x.y.z|N/A`
- [ ] Use grep/awk to extract field values
- [ ] Validate required fields present

### Task 3: Implement PR Merge Execution
- [ ] Check if `PR_MERGE_APPROVED: true`
- [ ] Check if `ship.pr.auto_merge: true` (default)
- [ ] If both true, execute merge:
  ```bash
  gh pr merge $PR_NUMBER --squash --body "Shipped via ADW"
  ```
- [ ] Use configured merge_strategy (squash, merge, rebase)
- [ ] Include version in merge body if available

### Task 4: Implement Branch Deletion
- [ ] Check if `ship.pr.delete_branch: true` (default)
- [ ] If merge succeeded and delete_branch true:
  ```bash
  gh pr merge $PR_NUMBER --delete-branch
  ```
- [ ] Or handle separately after merge if needed
- [ ] Log branch deletion success/failure

### Task 5: Implement Auto-Merge Disabled Flow
- [ ] If `ship.pr.auto_merge: false`:
  - Skip gh pr merge
  - Log: "Auto-merge disabled, PR left open"
  - Exit code 0 (success)
- [ ] PR remains for manual review and merge
- [ ] Include PR URL in output for convenience

### Task 6: Implement Merge Error Handling
- [ ] Capture gh pr merge exit code
- [ ] On failure:
  - Parse error message from gh
  - Log specific error (conflicts, checks failed, etc.)
  - Provide manual merge instructions
  - Exit with code 1
- [ ] Common errors:
  - Merge conflicts
  - Required status checks failed
  - Branch protection rules violated

### Task 7: Implement Task Manager Integration
- [ ] Check if task manager is configured
- [ ] If configured and merge successful:
  - Get task ID from run context
  - Move task to "Done" state via TaskManager
  - Log task status update
- [ ] Use existing Epic 12 task_manager integration
- [ ] Continue even if task update fails (log warning)

### Task 8: Write Tests
- [ ] Test status parsing from ship_report
- [ ] Test PR merge execution with squash
- [ ] Test PR merge with merge strategy
- [ ] Test PR merge with rebase strategy
- [ ] Test branch deletion after merge
- [ ] Test auto_merge disabled flow
- [ ] Test merge error handling
- [ ] Test task manager integration

---

## Dependencies

- **Depends On:** 15.1, 15.2, 15.3, 15.5
- **Blocks:** 15.7 (Ship Report Generation)
- **Can Parallel With:** None

### Dependency Rationale
- Requires ship phase infrastructure from 15.1
- Pre-flight analysis (15.2) validates PR state
- Command execution (15.3) determines success/failure
- Failure diagnosis (15.5) may set PR_MERGE_APPROVED: false
- Merge result included in final report (15.7)

---

## Developer Context

### Technical Requirements

1. **post.sh Implementation**
   - Bash script executed after LLM phase
   - Parses structured output from ship_report.md
   - Executes gh CLI commands based on config

2. **GitHub CLI Merge Commands**
   ```bash
   # Squash merge (default)
   gh pr merge $PR_NUMBER --squash --body "Shipped via ADW v1.2.3"

   # Regular merge
   gh pr merge $PR_NUMBER --merge --body "Shipped via ADW"

   # Rebase merge
   gh pr merge $PR_NUMBER --rebase

   # With branch deletion
   gh pr merge $PR_NUMBER --squash --delete-branch
   ```

3. **Configuration Access**
   - Read ship.pr config from project.yaml
   - Use ADW_ARTIFACTS_DIR for ship_report location
   - Use ADW_RUN_ID for task manager context

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/post.sh           # PR merge implementation
src/adw/defaults/commands/ship/ship/instructions.xml  # Step 6 (finalization)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| gh CLI | any | PR merge operations |
| grep/awk | POSIX | Status parsing |
| jq | optional | JSON config parsing |

### File Structure Requirements

**post.sh Implementation:**
```bash
#!/bin/bash
# Ship Phase Post-Hook: PR Merge

set -e

# Parse ship report for status
SHIP_REPORT="$ADW_ARTIFACTS_DIR/ship/ship_report.md"

# Extract status fields
DEPLOYMENT_STATUS=$(grep "^DEPLOYMENT_STATUS:" "$SHIP_REPORT" | cut -d' ' -f2)
PR_MERGE_APPROVED=$(grep "^PR_MERGE_APPROVED:" "$SHIP_REPORT" | cut -d' ' -f2)
VERSION_DEPLOYED=$(grep "^VERSION_DEPLOYED:" "$SHIP_REPORT" | cut -d' ' -f2)
PR_NUMBER=$(grep "^PR_NUMBER:" "$SHIP_REPORT" | cut -d' ' -f2)

# Check if merge is approved
if [ "$PR_MERGE_APPROVED" != "true" ]; then
  echo "PR merge not approved: DEPLOYMENT_STATUS=$DEPLOYMENT_STATUS"
  exit 0  # Not an error, just skip merge
fi

# Check auto_merge config (default true)
# Would need to read from project config
AUTO_MERGE="${ADW_SHIP_AUTO_MERGE:-true}"
if [ "$AUTO_MERGE" != "true" ]; then
  echo "Auto-merge disabled, PR left open"
  exit 0
fi

# Get merge strategy (default squash)
MERGE_STRATEGY="${ADW_SHIP_MERGE_STRATEGY:-squash}"
DELETE_BRANCH="${ADW_SHIP_DELETE_BRANCH:-true}"

# Build merge command
MERGE_BODY="Shipped via ADW"
if [ "$VERSION_DEPLOYED" != "N/A" ]; then
  MERGE_BODY="Shipped via ADW v$VERSION_DEPLOYED"
fi

# Execute merge
case "$MERGE_STRATEGY" in
  squash)
    gh pr merge "$PR_NUMBER" --squash --body "$MERGE_BODY" ${DELETE_BRANCH:+--delete-branch}
    ;;
  merge)
    gh pr merge "$PR_NUMBER" --merge --body "$MERGE_BODY" ${DELETE_BRANCH:+--delete-branch}
    ;;
  rebase)
    gh pr merge "$PR_NUMBER" --rebase ${DELETE_BRANCH:+--delete-branch}
    ;;
esac

echo "PR #$PR_NUMBER merged successfully"
```

**Instructions.xml Structure (Step 6):**
```xml
<step n="6" goal="Finalize and prepare for merge">
  <action>Determine final status based on execution results</action>

  <check if="DEPLOYMENT_STATUS == SUCCESS">
    <action>Set PR_MERGE_APPROVED: true</action>
  </check>

  <check if="DEPLOYMENT_STATUS == FAILED or BLOCKED">
    <action>Set PR_MERGE_APPROVED: false</action>
  </check>

  <action>Output structured status for post.sh:</action>
  <output>
    DEPLOYMENT_STATUS: {{status}}
    PR_MERGE_APPROVED: {{approved}}
    VERSION_DEPLOYED: {{version}}
    PR_NUMBER: {{pr_number}}
  </output>
</step>
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_pr_merge.py
class TestPRMerge:
    def test_parse_status_from_report(self):
        """Parses status fields from ship_report.md."""

    def test_merge_with_squash(self):
        """Executes squash merge when approved."""

    def test_merge_with_merge_strategy(self):
        """Executes merge commit when strategy=merge."""

    def test_merge_with_rebase(self):
        """Executes rebase when strategy=rebase."""

    def test_skip_when_not_approved(self):
        """Skips merge when PR_MERGE_APPROVED: false."""

    def test_skip_when_auto_merge_disabled(self):
        """Skips merge when auto_merge: false."""

    def test_branch_deletion(self):
        """Deletes branch when delete_branch: true."""

    def test_preserve_branch(self):
        """Preserves branch when delete_branch: false."""

    def test_merge_error_handling(self):
        """Handles merge failures with instructions."""
```

---

## Previous Story Intelligence

**From Story 15.1:**
- ShipPRConfig defines merge settings
- post.sh is the merge execution point

**From Story 15.2:**
- PR state validated in pre-flight
- Mergeable state confirmed before ship

**From Story 15.3/15.5:**
- DEPLOYMENT_STATUS set based on command results
- Failure diagnosis prevents merge

**From Epic 12:**
- TaskManager integration exists
- update_status method for state transitions

---

## Git Intelligence

**Merge Strategies:**
- squash: Combines all commits into one
- merge: Creates merge commit
- rebase: Replays commits on target

**ADW Commit Convention:**
- "Shipped via ADW" identifies automated merges
- Version in message for traceability

---

## Latest Technical Information

**GitHub CLI Merge (2025):**
```bash
# Full command reference
gh pr merge [<number>] [flags]

Flags:
  --auto              Enable auto-merge
  --body string       Body text for the merge commit
  --delete-branch     Delete the local and remote branch after merge
  --merge             Merge the commits with the base branch
  --rebase            Rebase the commits onto the base branch
  --squash            Squash the commits into one commit
```

**Environment Variables in post.sh:**
- `ADW_RUN_ID`: Current run identifier
- `ADW_PHASE`: Current phase (ship)
- `ADW_ARTIFACTS_DIR`: Path to artifacts
- `ADW_CONTEXT_FILE`: Full context JSON

---

## Project Context Reference

See: `_bmad-output/architecture.md#Hook Execution Environment`

Key patterns and rules from project context:
- **post.sh execution**: After LLM phase completes
- **Environment variables**: ADW_* set by orchestrator
- **Exit codes**: 0 success, non-zero failure
- **Task manager**: Epic 12 integration for status updates

---

## Dev Notes

### Implementation Approach

1. LLM step 6 determines final status
2. Output structured fields for post.sh
3. post.sh parses ship_report.md
4. Execute gh pr merge if approved
5. Handle branch deletion
6. Update task manager if configured
7. Return appropriate exit code

### Key Design Decisions

1. **LLM determines approval**: Based on all prior steps
2. **post.sh executes merge**: Separation of concerns
3. **Auto-merge default true**: Streamlined workflow
4. **Squash default**: Clean commit history
5. **Branch deletion default**: Clean up after merge

### Merge Message Format

```
Shipped via ADW v1.2.3

PR #123: Add user authentication
```

### Error Recovery

If merge fails:
```
ERROR: PR merge failed

Reason: Required status checks have not passed

Manual merge instructions:
1. Wait for checks to complete
2. Run: gh pr merge 123 --squash
   OR
3. Merge via GitHub web interface
```

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.6]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]
- [Source: gh CLI documentation - gh pr merge]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.6

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
