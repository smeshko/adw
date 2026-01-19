# Epic 15: Ship Phase & Deployment

**Goal:** Complete the feature delivery lifecycle with an LLM-driven ship phase that provides intelligent pre-flight analysis, optional deployment command execution, release notes generation, failure diagnosis, and automated PR merge.

**Priority:** Post-MVP
**Dependencies:** Epic 9 (Git Integration), Epic 12 (Task Manager Integration), Epic 13 (Webhook Infrastructure), Epic 14 (Init Wizard - for Story 15.8)

---

## Design Overview

The Ship phase is **LLM-driven** (like plan/build/validate/document) rather than purely shell-based. This enables:

1. **Intelligent Pre-Flight Analysis** - Risk assessment, breaking change detection
2. **Release Notes Generation** - Categorized changelog from commit history
3. **Failure Diagnosis** - Specific error analysis with remediation suggestions
4. **Post-Deploy Verification** - Confirmation of successful deployment

All deployment commands are **optional**. If no commands are configured, the ship phase performs analysis, generates release notes, and merges the PR.

---

## Story 15.1: Ship Phase SDK Integration

As a developer,
I want the ship phase fully integrated into the ADW SDK,
So that it executes as part of the standard pipeline like other phases.

**Acceptance Criteria:**

### Phase Sequence Integration

**Given** the ADW phase sequence in `src/adw/core/constants.py`
**When** ship phase is added
**Then** PHASE_SEQUENCE becomes:
```python
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "validate",
    "document",
    "ship",  # NEW
)
```

**Given** files that use PHASE_SEQUENCE
**When** ship is added to the tuple
**Then** these files automatically support ship phase:
- `src/adw/core/orchestrator.py` - pipeline execution
- `src/adw/core/phase_runner.py` - phase execution
- `src/adw/core/resume_manager.py` - resume handling
- `src/adw/cli/progress.py` - progress display
- `src/adw/cli/status_display.py` - status display
- `src/adw/cli/dry_run.py` - dry run output
- `src/adw/cli/validators.py` - phase validation

### Configuration Model

**Given** ship phase configuration
**When** models are added to `src/adw/models/config.py`
**Then** the following models are created:

```python
class ShipCommandsConfig(BaseModel):
    """Configuration for optional ship deployment commands."""
    version_bump: str | None = Field(default=None)
    build: str | None = Field(default=None)
    publish: str | None = Field(default=None)

class ShipPRConfig(BaseModel):
    """Configuration for PR merge behavior."""
    auto_merge: bool = Field(default=True)
    merge_strategy: Literal["squash", "merge", "rebase"] = Field(default="squash")
    delete_branch: bool = Field(default=True)

class ShipConfig(BaseModel):
    """Ship phase configuration."""
    commands: ShipCommandsConfig = Field(default_factory=ShipCommandsConfig)
    post_publish: list[str] = Field(default_factory=list)
    pr: ShipPRConfig = Field(default_factory=ShipPRConfig)
```

**Given** ProjectConfig model
**When** ship field is added
**Then** it includes:
```python
ship: ShipConfig = Field(
    default_factory=ShipConfig,
    description="Ship phase configuration (deployment commands, PR merge)"
)
```

### Command Folder Structure

**Given** ship phase folder structure
**When** created at `src/adw/defaults/commands/ship/`
**Then** it contains:
```
ship/
├── config.yaml          # Phase timeout, artifact definitions
├── prompt.md            # Main prompt with workflow includes
├── pre.sh               # Validation only (PR exists check)
├── post.sh              # PR merge based on LLM output
└── ship/                # Workflow subfolder
    ├── workflow.yaml    # Workflow config (BMAD pattern)
    └── instructions.xml # BMAD-style XML instructions
```

**Given** ship phase config.yaml
**When** created
**Then** it defines:
```yaml
timeout_seconds: 900

artifacts:
  - name: ship_report
    pattern: "ship_report.md"
    required: true
    description: "Full deployment report from LLM"
  - name: release_notes
    pattern: "release_notes.md"
    required: false
    description: "Generated release notes"
```

### Phase Behavior

**Given** ship phase is disabled
**When** `phases.ship.enabled: false` in project.yaml
**Then** ship phase is skipped (pipeline ends at document)

**Given** ship phase enabled (default)
**When** document phase completes successfully
**Then** ship phase executes automatically

**Given** ship phase runs
**When** pre.sh executes
**Then** it validates PR exists (exits 1 if no PR)

**Given** ship phase runs
**When** post.sh executes
**Then** it parses LLM output for:
- `DEPLOYMENT_STATUS: SUCCESS|FAILED|BLOCKED`
- `PR_MERGE_APPROVED: true|false`
- `VERSION_DEPLOYED: x.y.z|N/A`

### Test Coverage

**Given** ship phase integration
**When** tests are written
**Then** coverage includes:
- `test_constants.py`: ship in PHASE_SEQUENCE
- `test_config.py`: ShipConfig, ShipCommandsConfig, ShipPRConfig models
- `test_phase_runner.py`: ship phase execution
- `test_orchestrator.py`: full pipeline with ship
- Hook tests: pre.sh and post.sh behavior

---

## Story 15.2: Context Gathering & Pre-Flight Analysis

As a developer,
I want the LLM to analyze my changes before shipping,
So that I'm warned about risky deployments and breaking changes.

**Acceptance Criteria:**

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

---

## Story 15.3: Deployment Command Execution

As a developer,
I want to run optional deployment commands during ship phase,
So that I can automate version bumps, builds, and publishing.

**Acceptance Criteria:**

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

---

## Story 15.4: Release Notes Generation

As a developer,
I want release notes generated from my commits,
So that I have documentation for what was shipped.

**Acceptance Criteria:**

**Given** commits since last tag are available
**When** LLM generates release notes
**Then** commits are categorized:
- **Added**: feat:, feature:, add:
- **Changed**: refactor:, update:, change:, improve:
- **Fixed**: fix:, bugfix:, patch:, resolve:
- **Docs**: docs:, doc:
- **Other**: chore:, ci:, test:, style:

**Given** release notes are generated
**When** formatted
**Then** output follows Keep a Changelog format:
```markdown
## [version] - YYYY-MM-DD

### Added
- Feature descriptions

### Changed
- Modification descriptions

### Fixed
- Bug fix descriptions
```

**Given** version bump was executed
**When** release notes header generated
**Then** it uses the new version number

**Given** no version bump configured
**When** release notes header generated
**Then** it uses "Unreleased" as version

**Given** ship phase completes
**When** artifacts are saved
**Then** `release_notes.md` is captured as artifact

---

## Story 15.5: Failure Diagnosis & Recovery

As a developer,
I want specific diagnosis when deployment fails,
So that I can quickly fix the issue and retry.

**Acceptance Criteria:**

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

---

## Story 15.6: PR Merge & Completion

As a developer,
I want the PR automatically merged after successful ship,
So that my feature is delivered without manual intervention.

**Acceptance Criteria:**

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

---

## Story 15.7: Ship Report Generation

As a developer,
I want a comprehensive ship report as an artifact,
So that I have a record of what was deployed and how.

**Acceptance Criteria:**

**Given** ship phase completes (success or failure)
**When** report generated
**Then** it includes structured fields for post.sh parsing:
```
DEPLOYMENT_STATUS: SUCCESS | FAILED | BLOCKED
PR_MERGE_APPROVED: true | false
VERSION_DEPLOYED: x.y.z | N/A
PR_NUMBER: 123
```

**Given** report is generated
**When** saved as artifact
**Then** `ship_report.md` contains:
- Pre-flight summary with risk assessment
- Execution log (commands and results)
- Release notes
- Failure analysis (if applicable)
- Verification recommendations

**Given** ship phase completes
**When** artifacts captured
**Then** config.yaml defines:
```yaml
artifacts:
  - name: ship_report
    pattern: "ship_report.md"
    required: true
  - name: release_notes
    pattern: "release_notes.md"
    required: false
```

---

## Story 15.8: Init Wizard Ship Phase Integration

As a user running `adw init` with the wizard,
I want to configure ship phase settings during setup,
So that deployment commands and PR merge behavior are ready from the start.

**Acceptance Criteria:**

### Wizard Step Addition

**Given** the init wizard flow (Epic 14 implemented)
**When** ship phase step is added
**Then** it appears after Phase Customization (Step 5) as a new optional step

**Given** user reaches ship phase step
**When** prompted
**Then** wizard asks: "Configure ship phase settings? [y/N]"

**Given** user selects No
**When** wizard continues
**Then** ship phase uses defaults (no commands, auto-merge enabled, squash strategy)

### Deployment Commands Configuration

**Given** user selects Yes to configure ship phase
**When** commands section presented
**Then** wizard prompts:
- "Version bump command: [none] (Enter to skip or type command)"
- "Build command: [none] (Enter to skip or type command)"
- "Publish command: [none] (Enter to skip or type command)"

**Given** commands are entered
**When** wizard validates
**Then** it checks command format is non-empty string (no validation of actual command)

### Post-Publish Hooks Configuration

**Given** user is configuring ship phase
**When** post-publish section presented
**Then** wizard prompts: "Add post-publish hooks? [y/N]"

**Given** user selects Yes
**When** adding hooks
**Then** wizard loops: "Hook command (empty to finish): ____"

**Given** user enters empty line
**When** loop evaluates
**Then** hook collection ends, continues to next section

### PR Merge Settings Configuration

**Given** user is configuring ship phase
**When** PR settings section presented
**Then** wizard shows:
```
─── PR Merge Settings ───
```

**Given** PR settings section active
**When** prompts displayed
**Then** wizard asks:
- "Auto-merge after successful ship? [Y/n]"
- "Merge strategy: [squash] / merge / rebase"
- "Delete branch after merge? [Y/n]"

**Given** merge strategy prompt
**When** user responds
**Then** accepts: "squash", "merge", "rebase", or Enter for default (squash)

### Summary Display Update

**Given** wizard reaches summary step (Story 14.10)
**When** ship phase was configured
**Then** summary panel includes ship section:
```
Ship: ✓ Enabled
  Commands: version_bump ✓, build ✓, publish ✓
  Post-hooks: 2 configured
  PR: squash merge, auto-delete branch
```

**Given** ship phase uses defaults
**When** summary displayed
**Then** shows: "Ship: Default (no commands, squash merge)"

### Files to Generate

**Given** wizard completes with ship configuration
**When** files generated
**Then** `project.yaml` includes ship section:
```yaml
ship:
  commands:
    version_bump: "npm version patch"  # if configured
    build: "npm run build"             # if configured
    publish: "npm publish"             # if configured
  post_publish:                        # if configured
    - "git push --tags"
  pr:
    auto_merge: true
    merge_strategy: squash
    delete_branch: true
```

### Test Coverage

**Given** wizard ship step implementation
**When** tests written
**Then** coverage includes:
- `test_wizard_ship.py`: All ship prompts and validation
- `test_wizard_summary.py`: Ship section in summary display
- `test_wizard_generation.py`: Ship config in generated project.yaml

---

## Configuration

```yaml
# .adw/project.yaml
phases:
  ship:
    enabled: true
    timeout_seconds: 900

ship:
  # All commands are OPTIONAL
  # If none configured, only PR merge happens
  commands:
    version_bump: "npm version patch"     # optional
    build: "npm run build"                # optional
    publish: "npm publish"                # optional

  # Post-publish hooks (optional, continue on failure)
  post_publish:
    - "git push --tags"
    - "./scripts/notify-slack.sh"

  # PR merge settings
  pr:
    auto_merge: true           # Set false for manual merge
    merge_strategy: squash     # squash | merge | rebase
    delete_branch: true        # Delete feature branch after merge
```

---

## Ship Phase Flow

```
Ship Phase Start
       │
       ▼
┌─────────────────────────────────────┐
│  pre.sh: Validate PR exists         │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  LLM Step 1: Gather Context         │
│  - gh pr view (PR info)             │
│  - Read version file                │
│  - git log (commits since tag)      │
│  - Extract ship config              │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  LLM Step 2: Pre-Flight Analysis    │
│  - Risk assessment (LOW/MED/HIGH)   │
│  - Breaking change detection        │
│  - PR merge readiness check         │
└─────────────────────────────────────┘
       │
       ├── PR not mergeable? ─────────▶ BLOCKED
       │
       ▼
┌─────────────────────────────────────┐
│  LLM Step 3: Execute Commands       │
│  (OPTIONAL - skip if none config)   │
│  - version_bump                     │
│  - build                            │
│  - publish                          │
│  - post_publish hooks               │
└─────────────────────────────────────┘
       │
       ├── Command failed? ───────────▶ Failure Diagnosis
       │                                      │
       ▼                                      ▼
┌─────────────────────────────────────┐  ┌──────────────┐
│  LLM Step 4: Release Notes          │  │ FAILED       │
│  - Categorize commits               │  │ PR NOT merged│
│  - Generate changelog               │  └──────────────┘
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  LLM Step 5: Finalize               │
│  - Set DEPLOYMENT_STATUS: SUCCESS   │
│  - Set PR_MERGE_APPROVED: true      │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  LLM Step 6: Ship Report            │
│  - Output structured report         │
│  - Include all analysis & results   │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  post.sh: PR Merge                  │
│  - Parse DEPLOYMENT_STATUS          │
│  - Parse PR_MERGE_APPROVED          │
│  - Execute gh pr merge              │
│  - Save artifacts                   │
└─────────────────────────────────────┘
       │
       ▼
   Ship Complete
```

---

## Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-1] Ship Phase SDK Integration                                ║
║         (PHASE_SEQUENCE, config models, command folder)           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 15.1                                               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-2] Context Gathering & Pre-Flight Analysis                   ║
║         (LLM instructions for context + risk assessment)          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 15.2 (PARALLEL x2)                                 ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-3] Deployment Commands    ║    [15-4] Release Notes          ║
║  (version_bump, build, pub)    ║    (commit categorization)       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 15.3                                               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-5] Failure Diagnosis & Recovery                              ║
║         (error analysis + remediation steps)                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 5: After 15.5                                               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-6] PR Merge & Completion                                     ║
║         (post.sh merge execution + task manager)                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 6: After 15.6 + 15.4 (PARALLEL x2)                          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [15-7] Ship Report Generation  ║  [15-8] Init Wizard Integration ║
║  (ship_report.md artifact)      ║  (wizard step + summary update) ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Wave Summary

| Wave | Stories | Parallelization | Description |
|------|---------|-----------------|-------------|
| 1 | 15.1 | None | Foundation infrastructure |
| 2 | 15.2 | None | Context & pre-flight analysis |
| 3 | 15.3, 15.4 | **Parallel** | Commands + Release Notes |
| 4 | 15.5 | None | Failure diagnosis |
| 5 | 15.6 | None | PR merge & completion |
| 6 | 15.7, 15.8 | **Parallel** | Report generation + Wizard integration |

---

## LLM Value-Add Summary

| Capability | Value |
|------------|-------|
| Pre-Flight Analysis | Catches risky deployments, breaking changes before they ship |
| Release Notes | Generates human-readable changelog that scripts can't produce well |
| Failure Diagnosis | Provides specific remediation instead of generic "command failed" |
| Risk Assessment | Helps developers make informed decisions about deployment |

---

## Files to Create/Modify

### SDK Core Changes

| File | Change |
|------|--------|
| `src/adw/core/constants.py` | Add `"ship"` to `PHASE_SEQUENCE` tuple |
| `src/adw/models/config.py` | Add `ShipCommandsConfig`, `ShipPRConfig`, `ShipConfig` models |
| `src/adw/models/config.py` | Add `ship: ShipConfig` field to `ProjectConfig` |

### Command Folder Structure

```
src/adw/defaults/commands/ship/
├── config.yaml          # Phase timeout (900s), artifact definitions
├── prompt.md            # Main prompt with workflow includes
├── pre.sh               # Validate PR exists
├── post.sh              # Parse LLM output, merge PR
└── ship/                # Workflow subfolder (BMAD pattern)
    ├── workflow.yaml    # Workflow configuration
    └── instructions.xml # 6-step LLM instructions
```

### Init Wizard Files (Story 15.8)

| File | Change |
|------|--------|
| `src/adw/cli/wizard/ship.py` | New file - ship phase wizard step |
| `src/adw/cli/wizard/flow.py` | Add ship step after phase customization |
| `src/adw/cli/wizard/summary.py` | Add ship section to summary panel |

### Test Files

| File | Coverage |
|------|----------|
| `tests/unit/core/test_constants.py` | Ship in PHASE_SEQUENCE |
| `tests/unit/models/test_config.py` | ShipConfig model validation |
| `tests/unit/core/test_phase_runner.py` | Ship phase execution |
| `tests/integration/test_orchestrator.py` | Full pipeline with ship |
| `tests/unit/hooks/test_ship_hooks.py` | pre.sh and post.sh behavior |
| `tests/unit/cli/wizard/test_wizard_ship.py` | Ship step prompts and validation |
| `tests/unit/cli/wizard/test_wizard_summary.py` | Ship section in summary display |

### Files Automatically Updated (via PHASE_SEQUENCE)

These files use `PHASE_SEQUENCE` and will automatically support ship:
- `src/adw/core/orchestrator.py`
- `src/adw/core/phase_runner.py`
- `src/adw/core/resume_manager.py`
- `src/adw/cli/progress.py`
- `src/adw/cli/status_display.py`
- `src/adw/cli/dry_run.py`
- `src/adw/cli/validators.py`

---
