# Story 15.2: Context Gathering & Pre-Flight Analysis

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want the LLM to analyze my changes before shipping,
So that I'm warned about risky deployments and breaking changes.

## Acceptance Criteria

**Given** ship phase starts
**When** LLM gathers context
**Then** it collects via tool calls:
- PR info: `gh pr view --json number,title,mergeable,mergeStateStatus,reviewDecision`
- Current version: reads package.json, pyproject.toml, Cargo.toml, or VERSION
- Commits since last tag: `git describe --tags` + `git log`
- Ship configuration from project_config

**Given** context is gathered
**When** LLM performs pre-flight analysis
**Then** it evaluates:
- Risk level: LOW / MEDIUM / HIGH with justification
- Breaking changes: API changes, schema migrations, config changes
- Security-sensitive modifications
- PR merge readiness (mergeable state, review status)

**Given** risk level is HIGH with blocking issues
**When** analysis completes
**Then** LLM sets `DEPLOYMENT_STATUS: BLOCKED` and `PR_MERGE_APPROVED: false`

**Given** PR is not in mergeable state
**When** analysis completes
**Then** LLM halts with specific reason (conflicts, pending reviews, failed checks)

## Tasks / Subtasks

### Task 1: Define Context Gathering Instructions (Step 1 in instructions.xml)
- [ ] Create step 1 in `ship/instructions.xml` for context gathering
- [ ] Instruction to run `gh pr view --json number,title,mergeable,mergeStateStatus,reviewDecision`
- [ ] Instruction to detect version file type and read current version
- [ ] Instruction to run `git describe --tags --abbrev=0` for last tag
- [ ] Instruction to run `git log <last_tag>..HEAD --oneline` for commits
- [ ] Store all gathered context in structured format

### Task 2: Define Version File Detection Logic
- [ ] Check for `package.json` → extract `version` field
- [ ] Check for `pyproject.toml` → extract `project.version` or `tool.poetry.version`
- [ ] Check for `Cargo.toml` → extract `package.version`
- [ ] Check for `VERSION` file → read entire contents
- [ ] If no version file found → set version to "unknown"
- [ ] Document detection order in instructions

### Task 3: Define Pre-Flight Analysis Instructions (Step 2 in instructions.xml)
- [ ] Create step 2 in `ship/instructions.xml` for pre-flight analysis
- [ ] Analyze commit messages for breaking change indicators:
  - `BREAKING:` prefix
  - `!` after type (e.g., `feat!:`, `fix!:`)
  - Keywords: "breaking", "migration", "schema change"
- [ ] Analyze file changes for security indicators:
  - Changes to auth/security files
  - Changes to .env, secrets, credentials
  - New dependencies
- [ ] Evaluate PR readiness:
  - `mergeable: true` required
  - `mergeStateStatus: CLEAN` or `MERGEABLE`
  - `reviewDecision: APPROVED` recommended

### Task 4: Define Risk Assessment Logic
- [ ] LOW risk criteria:
  - No breaking changes
  - No security-sensitive changes
  - PR approved and mergeable
  - All checks passing
- [ ] MEDIUM risk criteria:
  - Minor breaking changes with migration path
  - Changes to secondary security components
  - PR mergeable but not all reviews complete
- [ ] HIGH risk criteria:
  - Major breaking changes without migration
  - Changes to core auth/security
  - PR has conflicts or failed checks
  - Missing required reviews

### Task 5: Define Blocking Conditions
- [ ] BLOCKED status conditions:
  - PR has merge conflicts
  - Required checks are failing
  - Required reviews missing
  - Branch protection rules violated
- [ ] When BLOCKED:
  - Set `DEPLOYMENT_STATUS: BLOCKED`
  - Set `PR_MERGE_APPROVED: false`
  - Include specific reason in report
  - Provide remediation steps

### Task 6: Write Prompt Template for Context Display
- [ ] Create section in `prompt.md` for context gathering prompt
- [ ] Template for displaying gathered context:
  ```
  ## Ship Phase Context

  ### PR Information
  - PR #{{pr_number}}: {{pr_title}}
  - Mergeable: {{mergeable}}
  - State: {{merge_state_status}}
  - Review Decision: {{review_decision}}

  ### Version Information
  - Current Version: {{current_version}}
  - Version File: {{version_file_path}}

  ### Changes Since Last Release
  - Last Tag: {{last_tag}}
  - Commits: {{commit_count}}
  {{commit_list}}
  ```

### Task 7: Write Tests
- [ ] Test version file detection for each supported type
- [ ] Test risk assessment logic (LOW, MEDIUM, HIGH cases)
- [ ] Test blocking condition detection
- [ ] Test PR state parsing
- [ ] Test context gathering instruction execution (mocked)

---

## Dependencies

- **Depends On:** 15.1 (Ship Phase SDK Integration)
- **Blocks:** 15.3, 15.4, 15.5, 15.6
- **Can Parallel With:** None

### Dependency Rationale
- Requires ship phase infrastructure from 15.1
- Pre-flight must complete before command execution (15.3)
- Context needed for release notes generation (15.4)
- Risk assessment informs failure diagnosis (15.5)
- PR readiness check required before merge (15.6)

---

## Developer Context

### Technical Requirements

1. **GitHub CLI Integration**
   - Use `gh pr view --json` for structured PR data
   - Parse JSON output for specific fields
   - Handle case where PR doesn't exist (pre.sh should catch this)

2. **Version Detection**
   - Support multiple package managers/languages
   - Follow detection order: package.json → pyproject.toml → Cargo.toml → VERSION
   - Graceful fallback to "unknown" if no version file

3. **Git History Analysis**
   - Use `git describe --tags --abbrev=0` for latest tag
   - If no tags exist, analyze all commits on branch
   - Parse conventional commit prefixes for categorization

4. **Risk Assessment Algorithm**
   - Weighted scoring based on change types
   - Clear criteria for each risk level
   - Actionable output for developers

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/prompt.md       # Context display template
src/adw/defaults/commands/ship/ship/instructions.xml  # Steps 1-2
```

**No New SDK Code:** This story defines LLM instructions, not SDK implementation.

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| gh CLI | any | PR information retrieval |
| git | any | Version history analysis |
| jq | optional | JSON parsing in bash (if needed) |

### File Structure Requirements

**Instructions.xml Structure (Steps 1-2):**
```xml
<workflow>
  <step n="1" goal="Gather ship context">
    <action>Run: gh pr view --json number,title,mergeable,mergeStateStatus,reviewDecision</action>
    <action>Detect and read version file</action>
    <action>Run: git describe --tags --abbrev=0</action>
    <action>Run: git log {{last_tag}}..HEAD --oneline</action>
    <action>Extract ship configuration from project config</action>
  </step>

  <step n="2" goal="Pre-flight analysis">
    <action>Analyze commits for breaking changes</action>
    <action>Check for security-sensitive modifications</action>
    <action>Evaluate PR merge readiness</action>
    <action>Calculate risk level: LOW | MEDIUM | HIGH</action>
    <check if="risk_level == HIGH and has_blocking_issues">
      <action>Set DEPLOYMENT_STATUS: BLOCKED</action>
      <action>Set PR_MERGE_APPROVED: false</action>
    </check>
  </step>
</workflow>
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_version_detection.py
class TestVersionDetection:
    def test_detect_package_json(self, tmp_path):
        """Detects version from package.json."""
        (tmp_path / "package.json").write_text('{"version": "1.2.3"}')
        # Test detection logic

    def test_detect_pyproject_toml(self, tmp_path):
        """Detects version from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "2.0.0"')
        # Test detection logic

    def test_fallback_to_unknown(self, tmp_path):
        """Returns 'unknown' when no version file exists."""
        # Test fallback

# tests/unit/ship/test_risk_assessment.py
class TestRiskAssessment:
    def test_low_risk_clean_pr(self):
        """Clean PR with no breaking changes is LOW risk."""

    def test_medium_risk_breaking_with_migration(self):
        """Breaking change with migration path is MEDIUM risk."""

    def test_high_risk_security_changes(self):
        """Changes to auth/security files is HIGH risk."""

    def test_blocked_when_conflicts(self):
        """PR with conflicts results in BLOCKED status."""
```

---

## Previous Story Intelligence

**From Story 15.1:**
- PHASE_SEQUENCE includes "ship"
- ShipConfig models provide configuration structure
- pre.sh validates PR exists before ship phase runs

**Relevant Patterns:**
- LLM instructions use BMAD XML format
- Context gathering via bash tool calls
- Structured output for post.sh parsing

---

## Git Intelligence

**Established Patterns:**
- Instructions.xml follows BMAD workflow pattern
- Steps numbered sequentially (1, 2, 3...)
- Actions are explicit LLM directives
- Checks provide conditional logic

---

## Latest Technical Information

**GitHub CLI JSON Fields (2025):**
```bash
gh pr view --json number,title,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
```
- `mergeable`: boolean - can PR be merged
- `mergeStateStatus`: CLEAN, BLOCKED, BEHIND, DIRTY, HAS_HOOKS, UNKNOWN
- `reviewDecision`: APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, null

**Conventional Commits Breaking Change Indicators:**
- `BREAKING CHANGE:` in commit footer
- `!` after type: `feat!:`, `fix!:`, `refactor!:`
- Commit body contains "BREAKING:"

---

## Project Context Reference

See: `_bmad-output/architecture.md`

Key patterns and rules from project context:
- **LLM gathers context via tool calls**: Use bash for external commands
- **Structured output format**: LLM produces parseable report
- **Risk assessment is advisory**: BLOCKED status prevents merge

---

## Dev Notes

### Implementation Approach

1. Define context gathering instructions first
2. Add version detection logic with fallbacks
3. Define pre-flight analysis criteria
4. Document risk assessment algorithm
5. Define blocking conditions clearly
6. Test each component independently

### Key Design Decisions

1. **LLM-driven analysis**: Not hardcoded rules, LLM interprets changes
2. **Advisory risk levels**: LOW/MEDIUM are informational, HIGH may block
3. **BLOCKED is definitive**: BLOCKED status always prevents merge
4. **Graceful degradation**: Missing version file doesn't block ship

### Risk Assessment Guidelines

| Indicator | LOW | MEDIUM | HIGH |
|-----------|-----|--------|------|
| Breaking changes | None | Minor with docs | Major without migration |
| Security files | None touched | Non-critical | Core auth/security |
| PR state | Approved, clean | Mergeable | Conflicts/blocked |
| Tests | All passing | Some skipped | Failures |

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.2]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]
- [Source: GitHub CLI Documentation - gh pr view]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.2

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
