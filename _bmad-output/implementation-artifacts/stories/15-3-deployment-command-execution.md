# Story 15.3: Deployment Command Execution

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want to run optional deployment commands during ship phase,
So that I can automate version bumps, builds, and publishing.

## Acceptance Criteria

**Given** no commands configured in `ship.commands`
**When** ship phase runs
**Then** execution step is skipped, proceeds to release notes

**Given** commands are configured
**When** ship phase runs
**Then** commands execute in order:
1. `ship.commands.version_bump` (optional)
2. `ship.commands.build` (optional)
3. `ship.commands.publish` (optional)

**Given** a command fails
**When** error occurs
**Then** LLM:
- Captures error output
- Sets `DEPLOYMENT_STATUS: FAILED`
- Sets `PR_MERGE_APPROVED: false`
- Proceeds to failure diagnosis (Story 15.5)

**Given** all commands succeed
**When** execution completes
**Then** LLM:
- Captures new version (if version_bump ran)
- Sets `DEPLOYMENT_STATUS: SUCCESS`
- Proceeds to release notes

**Given** `ship.post_publish` hooks configured
**When** publish succeeds
**Then** hooks run in order (continue on failure, log warnings)

## Tasks / Subtasks

### Task 1: Define Command Execution Instructions (Step 3 in instructions.xml)
- [x] Create step 3 in `ship/instructions.xml` for command execution
- [x] Check if `ship.commands` has any configured commands
- [x] If no commands configured, skip to step 4 (release notes)
- [x] Document execution order: version_bump → build → publish

### Task 2: Implement Version Bump Execution
- [x] Check if `ship.commands.version_bump` is set
- [x] If set, execute command via bash tool
- [x] Capture stdout/stderr for logging
- [x] After success, re-read version file to capture new version
- [x] Store new version for release notes header
- [x] On failure, capture error and proceed to failure diagnosis

### Task 3: Implement Build Command Execution
- [x] Check if `ship.commands.build` is set
- [x] If set, execute command via bash tool
- [x] Capture stdout/stderr for logging
- [x] Build typically produces artifacts (don't parse, just run)
- [x] On failure, capture error and proceed to failure diagnosis

### Task 4: Implement Publish Command Execution
- [ ] Check if `ship.commands.publish` is set
- [ ] If set, execute command via bash tool
- [ ] Capture stdout/stderr for logging
- [ ] This is the critical deployment step
- [ ] On failure, capture error and proceed to failure diagnosis
- [ ] On success, set `DEPLOYMENT_STATUS: SUCCESS`

### Task 5: Implement Post-Publish Hooks
- [ ] Check if `ship.post_publish` list is non-empty
- [ ] Execute each hook in order
- [ ] Continue on failure (log warning, don't abort)
- [ ] Capture output for each hook
- [ ] Common hooks: `git push --tags`, notification scripts

### Task 6: Define Error Handling Flow
- [ ] On any command failure:
  - Capture full error output (stdout + stderr)
  - Identify which command failed
  - Set `DEPLOYMENT_STATUS: FAILED`
  - Set `PR_MERGE_APPROVED: false`
  - Store error context for failure diagnosis
  - Skip remaining commands in sequence
  - Proceed to failure diagnosis step

### Task 7: Write Tests
- [ ] Test skip logic when no commands configured
- [ ] Test execution order (version_bump → build → publish)
- [ ] Test failure handling for each command type
- [ ] Test post_publish hook execution
- [ ] Test continue-on-failure for post_publish
- [ ] Integration test with mocked commands

---

## Dependencies

- **Depends On:** 15.1 (Ship Phase SDK Integration), 15.2 (Context Gathering)
- **Blocks:** 15.5, 15.6
- **Can Parallel With:** 15.4 (Release Notes Generation)

### Dependency Rationale
- Requires ship phase infrastructure from 15.1
- Pre-flight analysis from 15.2 must pass before commands run
- Command failures feed into failure diagnosis (15.5)
- Command success/failure determines PR merge decision (15.6)
- Release notes (15.4) can be written in parallel as it uses commit history

---

## Developer Context

### Technical Requirements

1. **Command Execution via Bash Tool**
   - LLM executes commands using bash tool calls
   - Each command is independent execution
   - Working directory is project root

2. **Sequential Execution with Early Exit**
   - Commands run in strict order
   - First failure stops further command execution
   - Post-publish hooks continue despite failures

3. **Output Capture**
   - All stdout/stderr captured for logging
   - Version bump output parsed for new version
   - Error output essential for diagnosis

4. **Configuration Access**
   - Read `ship.commands` from project config
   - Read `ship.post_publish` for hook list
   - All values may be empty/null

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/ship/instructions.xml  # Step 3
```

**No New SDK Code:** This story defines LLM instructions for command execution.

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| bash | any | Command execution |
| npm/pip/cargo | varies | Package manager commands |

### File Structure Requirements

**Instructions.xml Structure (Step 3):**
```xml
<step n="3" goal="Execute deployment commands">
  <check if="no commands configured">
    <action>Skip to step 4 (release notes)</action>
  </check>

  <check if="ship.commands.version_bump is set">
    <action>Run: {{ship.commands.version_bump}}</action>
    <action>Re-read version file to capture new version</action>
    <check if="command failed">
      <action>Capture error: {{error_output}}</action>
      <action>Set DEPLOYMENT_STATUS: FAILED</action>
      <action>Set PR_MERGE_APPROVED: false</action>
      <action>GOTO failure diagnosis step</action>
    </check>
  </check>

  <check if="ship.commands.build is set">
    <action>Run: {{ship.commands.build}}</action>
    <check if="command failed">
      <!-- Same failure handling -->
    </check>
  </check>

  <check if="ship.commands.publish is set">
    <action>Run: {{ship.commands.publish}}</action>
    <check if="command failed">
      <!-- Same failure handling -->
    </check>
    <check if="command succeeded">
      <action>Set DEPLOYMENT_STATUS: SUCCESS</action>
    </check>
  </check>

  <check if="ship.post_publish is not empty">
    <iterate>For each hook in ship.post_publish:</iterate>
    <action>Run hook (continue on failure)</action>
    <check if="hook failed">
      <action>Log warning: "Post-publish hook failed: {{hook}}"</action>
      <!-- Continue to next hook -->
    </check>
  </check>
</step>
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_command_execution.py
class TestCommandExecution:
    def test_skip_when_no_commands(self):
        """Skips execution when ship.commands is empty."""

    def test_execution_order(self):
        """Commands execute in order: version_bump, build, publish."""

    def test_version_bump_captures_new_version(self):
        """New version is captured after version_bump succeeds."""

    def test_failure_stops_sequence(self):
        """First command failure skips remaining commands."""

    def test_failure_sets_status(self):
        """Command failure sets DEPLOYMENT_STATUS: FAILED."""

    def test_post_publish_continues_on_failure(self):
        """Post-publish hooks continue even if one fails."""

    def test_all_success_sets_status(self):
        """All commands succeeding sets DEPLOYMENT_STATUS: SUCCESS."""
```

---

## Previous Story Intelligence

**From Story 15.1:**
- ShipCommandsConfig defines command fields
- All command fields are optional (str | None)
- post_publish is list[str]

**From Story 15.2:**
- Pre-flight analysis provides risk assessment
- Current version is known before version_bump
- BLOCKED status prevents command execution

**Relevant Patterns:**
- Commands executed via bash tool in LLM context
- Output capture is automatic in Claude Code
- Error handling uses structured output fields

---

## Git Intelligence

**Established Patterns:**
- Shell commands in LLM instructions use bash tool
- Conditional execution via `<check if="">` blocks
- Error handling with early exit pattern

---

## Latest Technical Information

**Common Deployment Commands (2025):**
```yaml
# npm projects
ship:
  commands:
    version_bump: "npm version patch"
    build: "npm run build"
    publish: "npm publish"

# Python projects (uv)
ship:
  commands:
    version_bump: "uv version patch"
    build: "uv build"
    publish: "uv publish"

# Python projects (traditional)
ship:
  commands:
    version_bump: "bumpversion patch"
    build: "python -m build"
    publish: "twine upload dist/*"
```

**Post-Publish Common Hooks:**
```yaml
post_publish:
  - "git push --tags"
  - "git push origin HEAD"
  - "./scripts/notify-slack.sh"
  - "gh release create v${VERSION}"
```

---

## Project Context Reference

See: `_bmad-output/architecture.md`

Key patterns and rules from project context:
- **Commands from config**: Read from project_config.ship.commands
- **Bash tool for execution**: LLM uses bash tool for shell commands
- **Structured status output**: DEPLOYMENT_STATUS field for post.sh

---

## Dev Notes

### Implementation Approach

1. Check configuration for commands
2. Execute version_bump if configured
3. Capture new version after bump
4. Execute build if configured
5. Execute publish if configured
6. Run post_publish hooks
7. Set appropriate status

### Key Design Decisions

1. **All commands optional**: Ship works even with no commands
2. **Strict order**: version_bump → build → publish (logical progression)
3. **Early exit on failure**: Don't continue sequence after failure
4. **Post-publish continues**: Hooks are best-effort, not critical
5. **Version capture**: Important for release notes header

### Error Context Structure

```
Failed Command: ship.commands.publish
Command: npm publish
Exit Code: 1
Error Output:
  npm ERR! 402 Payment Required
  npm ERR! You must be a paid subscriber...

This error will be analyzed in the failure diagnosis step.
```

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.3]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]
- [Source: npm/pip/cargo documentation]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.3

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- Task 1: Created Step 3 in ship/instructions.xml with complete command execution logic
  - Added substep 3a for checking if commands are configured (skip logic)
  - Added substep 3b for version_bump execution with version re-read
  - Added substep 3c for build execution
  - Added substep 3d for publish execution
  - Added substep 3e for post-publish hooks (continue-on-failure)
  - Added substep 3f for execution summary
- Task 2: Version bump execution already implemented in substep 3b of Task 1
- Task 3: Build command execution already implemented in substep 3c of Task 1

### File List

- src/adw/defaults/commands/ship/instructions.xml (modified)
