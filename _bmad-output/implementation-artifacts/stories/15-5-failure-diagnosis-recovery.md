# Story 15.5: Failure Diagnosis & Recovery

Status: done
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want specific diagnosis when deployment fails,
So that I can quickly fix the issue and retry.

## Acceptance Criteria

**Given** any deployment command fails
**When** LLM analyzes the error
**Then** it provides:
- **Failed Step**: Which command failed (version_bump, build, publish)
- **Error Output**: Raw error from command
- **Diagnosis**: Specific analysis of what went wrong
- **Remediation**: Concrete steps to fix the issue

**Given** version_bump fails
**When** diagnosed
**Then** common causes are identified:
- Uncommitted changes preventing version update
- Invalid version format
- Git tag conflicts

**Given** build fails
**When** diagnosed
**Then** common causes are identified:
- Missing dependencies
- Compilation/transpilation errors
- Test failures (if build includes tests)

**Given** publish fails
**When** diagnosed
**Then** common causes are identified:
- Authentication/permission issues
- Package already exists (version conflict)
- Network/registry issues

**Given** failure occurs
**When** report generated
**Then** PR is NOT merged (`PR_MERGE_APPROVED: false`)

## Tasks / Subtasks

### Task 1: Define Failure Diagnosis Instructions (Step 5 in instructions.xml)
- [ ] Create step 5 in `ship/instructions.xml` for failure diagnosis
- [ ] Input: failed command, exit code, stdout, stderr from step 3
- [ ] Output: structured diagnosis with remediation steps
- [ ] Only execute if `DEPLOYMENT_STATUS: FAILED`

### Task 2: Implement Version Bump Failure Analysis
- [ ] Detect common version_bump failures:
  - "Git working directory not clean" → uncommitted changes
  - "Invalid version" → version format issue
  - "Tag already exists" → git tag conflict
  - "Permission denied" → file access issue
- [ ] Provide specific remediation:
  - Uncommitted: "Commit or stash changes before shipping"
  - Invalid version: "Check version format in {version_file}"
  - Tag conflict: "Delete existing tag: git tag -d {tag}"
  - Permission: "Check file permissions on {version_file}"

### Task 3: Implement Build Failure Analysis
- [ ] Detect common build failures:
  - "Module not found" → missing dependency
  - "Cannot find module" → import error
  - "Compilation failed" → syntax/type error
  - "Test failed" → test failures during build
  - "ENOENT" → missing file
- [ ] Provide specific remediation:
  - Missing dep: "Run: npm install / uv sync"
  - Import error: "Check import paths and module names"
  - Compilation: "Fix compilation errors in {file}:{line}"
  - Test failure: "Fix failing tests before shipping"
  - Missing file: "Ensure {file} exists"

### Task 4: Implement Publish Failure Analysis
- [ ] Detect common publish failures:
  - "403 Forbidden" → authentication issue
  - "401 Unauthorized" → missing credentials
  - "409 Conflict" → version already exists
  - "Payment Required" → npm paid feature
  - "ECONNREFUSED" → network/registry issue
  - "Rate limit" → API rate limiting
- [ ] Provide specific remediation:
  - Auth issue: "Check NPM_TOKEN / PYPI_TOKEN environment variable"
  - Missing creds: "Run: npm login / twine configure"
  - Version conflict: "Bump version again or use --force"
  - Network: "Check registry URL and network connection"
  - Rate limit: "Wait and retry, or use different credentials"

### Task 5: Implement Diagnosis Output Format
- [ ] Structure diagnosis report:
  ```markdown
  ## Deployment Failure Diagnosis

  ### Failed Step
  **Command:** ship.commands.{step}
  **Exit Code:** {exit_code}

  ### Error Output
  ```
  {stderr or stdout with error}
  ```

  ### Diagnosis
  {LLM analysis of what went wrong}

  ### Remediation
  1. {First step to fix}
  2. {Second step if applicable}
  3. {Third step if applicable}

  ### Status
  DEPLOYMENT_STATUS: FAILED
  PR_MERGE_APPROVED: false
  ```

### Task 6: Implement Recovery Suggestions
- [ ] Provide actionable recovery path:
  - For fixable issues: specific fix commands
  - For config issues: what to change in project.yaml
  - For auth issues: credential setup instructions
  - For conflicts: resolution steps
- [ ] Include "retry ship" instruction after fixes
- [ ] Note that PR remains open for manual merge if needed

### Task 7: Write Tests
- [ ] Test version_bump failure detection
- [ ] Test build failure detection
- [ ] Test publish failure detection
- [ ] Test diagnosis output format
- [ ] Test remediation suggestions
- [ ] Test PR_MERGE_APPROVED: false on failure

---

## Dependencies

- **Depends On:** 15.1 (Ship Phase SDK Integration), 15.3 (Deployment Command Execution)
- **Blocks:** 15.6, 15.7
- **Can Parallel With:** None

### Dependency Rationale
- Requires ship phase infrastructure from 15.1
- Command execution (15.3) provides failure context
- Failure diagnosis determines PR merge decision (15.6)
- Diagnosis included in final ship report (15.7)

---

## Developer Context

### Technical Requirements

1. **Error Pattern Matching**
   - LLM analyzes error output for known patterns
   - Not hardcoded regex, LLM interpretation
   - Handle variations in error messages

2. **Contextual Remediation**
   - Suggestions based on project type (npm, pip, cargo)
   - Include actual file paths when known
   - Provide runnable fix commands

3. **Status Flag Setting**
   - Always set `DEPLOYMENT_STATUS: FAILED`
   - Always set `PR_MERGE_APPROVED: false`
   - Include in structured output for post.sh

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/ship/instructions.xml  # Step 5
```

**No New SDK Code:** This story defines LLM instructions for failure analysis.

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| None | - | Pure LLM reasoning |

### File Structure Requirements

**Instructions.xml Structure (Step 5):**
```xml
<step n="5" goal="Failure diagnosis">
  <critical>Only execute if DEPLOYMENT_STATUS == FAILED</critical>

  <action>Analyze error output from failed command</action>

  <check if="version_bump failed">
    <action>Check for version_bump error patterns:</action>
    <patterns>
      <pattern match="not clean">Uncommitted changes</pattern>
      <pattern match="Invalid version">Version format error</pattern>
      <pattern match="already exists">Tag conflict</pattern>
    </patterns>
  </check>

  <check if="build failed">
    <action>Check for build error patterns:</action>
    <patterns>
      <pattern match="Module not found">Missing dependency</pattern>
      <pattern match="Compilation failed">Syntax error</pattern>
      <pattern match="Test failed">Test failure</pattern>
    </patterns>
  </check>

  <check if="publish failed">
    <action>Check for publish error patterns:</action>
    <patterns>
      <pattern match="403|401">Authentication issue</pattern>
      <pattern match="409">Version conflict</pattern>
      <pattern match="ECONNREFUSED">Network issue</pattern>
    </patterns>
  </check>

  <action>Generate diagnosis report with remediation steps</action>
  <action>Confirm DEPLOYMENT_STATUS: FAILED</action>
  <action>Confirm PR_MERGE_APPROVED: false</action>
</step>
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_failure_diagnosis.py
class TestFailureDiagnosis:
    def test_diagnose_uncommitted_changes(self):
        """Detects uncommitted changes in version_bump failure."""

    def test_diagnose_missing_dependency(self):
        """Detects missing dependency in build failure."""

    def test_diagnose_auth_failure(self):
        """Detects authentication issue in publish failure."""

    def test_diagnose_version_conflict(self):
        """Detects version conflict in publish failure."""

    def test_provides_remediation(self):
        """Provides actionable remediation steps."""

    def test_sets_failed_status(self):
        """Sets DEPLOYMENT_STATUS: FAILED."""

    def test_prevents_pr_merge(self):
        """Sets PR_MERGE_APPROVED: false."""
```

---

## Previous Story Intelligence

**From Story 15.3:**
- Command execution captures stdout/stderr
- Exit codes available for each command
- Failed command identified (version_bump, build, publish)

**Relevant Patterns:**
- Error analysis via LLM reasoning
- Structured output format for post.sh
- Remediation as actionable steps

---

## Git Intelligence

**Common Error Patterns (from project history):**
- Build failures often from import errors
- Publish failures often from auth/version
- Version bump failures often from dirty git state

---

## Latest Technical Information

**npm Error Codes (2025):**
- E402: Payment Required (private packages)
- E403: Forbidden (permissions)
- E404: Not Found (package name)
- E409: Conflict (version exists)

**pip/twine Error Patterns:**
- HTTPError 400: Bad request (invalid metadata)
- HTTPError 403: Forbidden (auth)
- HTTPError 409: Conflict (version exists)

**Cargo Publish Errors:**
- "could not find crate" → name mismatch
- "failed to verify" → checksum error
- "ownership" → crates.io permissions

---

## Project Context Reference

See: `_bmad-output/architecture.md`

Key patterns and rules from project context:
- **Actionable errors**: NFR10 requires actionable suggestions
- **Structured output**: Status fields for post.sh parsing
- **LLM diagnosis**: Use reasoning for error interpretation

---

## Dev Notes

### Implementation Approach

1. Check if DEPLOYMENT_STATUS is FAILED
2. Identify which command failed
3. Analyze error output for patterns
4. Generate diagnosis with explanation
5. Provide specific remediation steps
6. Confirm failure status flags

### Key Design Decisions

1. **LLM interpretation**: Not hardcoded patterns, LLM analyzes
2. **Contextual remediation**: Based on actual error and project type
3. **Always prevent merge**: Failed deployment never merges PR
4. **Recovery path**: Clear steps to fix and retry

### Error Pattern Examples

**Version Bump:**
```
error: Your local changes to the following files would be overwritten by merge:
        package.json
```
→ Diagnosis: Uncommitted changes
→ Remediation: git stash or git commit

**Build:**
```
error[E0433]: failed to resolve: use of undeclared crate or module `serde`
```
→ Diagnosis: Missing dependency
→ Remediation: Add serde to Cargo.toml

**Publish:**
```
npm ERR! 403 Forbidden - PUT https://registry.npmjs.org/@org/pkg
npm ERR! You do not have permission to publish "@org/pkg".
```
→ Diagnosis: Permission denied
→ Remediation: Check npm org membership or package name

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.5]
- [Source: npm documentation - Error codes]
- [Source: PyPI documentation - HTTP errors]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.5

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
