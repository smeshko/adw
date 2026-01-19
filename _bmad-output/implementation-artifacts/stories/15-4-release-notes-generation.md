# Story 15.4: Release Notes Generation

Status: Ready for Review
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want release notes generated from my commits,
So that I have documentation for what was shipped.

## Acceptance Criteria

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

## Tasks / Subtasks

### Task 1: Define Release Notes Instructions (Step 4 in instructions.xml)
- [x] Create step 4 in `ship/instructions.xml` for release notes
- [x] Input: commit list from step 1 (context gathering)
- [x] Input: new version from step 3 (if version_bump ran)
- [x] Output: formatted release notes in Keep a Changelog format

### Task 2: Implement Commit Categorization
- [x] Parse commit messages for conventional commit prefixes
- [x] **Added** category:
  - `feat:`, `feat(scope):`, `feature:`, `add:`
- [x] **Changed** category:
  - `refactor:`, `refactor(scope):`, `update:`, `change:`, `improve:`
- [x] **Fixed** category:
  - `fix:`, `fix(scope):`, `bugfix:`, `patch:`, `resolve:`
- [x] **Documentation** category:
  - `docs:`, `doc:`
- [x] **Other** category (collapsed into single section):
  - `chore:`, `ci:`, `test:`, `style:`, `build:`
- [x] Handle commits without conventional prefix (categorize as "Other")

### Task 3: Implement Version Header Logic
- [x] If version_bump executed successfully:
  - Use captured new version number
  - Format: `## [1.2.3] - 2026-01-18`
- [x] If no version_bump configured:
  - Use "Unreleased" as version
  - Format: `## [Unreleased] - 2026-01-18`
- [x] Always include current date (YYYY-MM-DD format)

### Task 4: Implement Keep a Changelog Format
- [x] Generate release notes following format:
  ```markdown
  ## [version] - YYYY-MM-DD

  ### Added
  - Feature descriptions from feat: commits

  ### Changed
  - Modification descriptions from refactor:/update: commits

  ### Fixed
  - Bug fix descriptions from fix: commits

  ### Documentation
  - Documentation updates from docs: commits

  ### Other
  - Maintenance tasks from chore:/ci:/test: commits
  ```
- [x] Omit empty sections (if no commits in category)
- [x] Clean commit messages (remove prefix, capitalize first letter)

### Task 5: Implement Commit Message Cleaning
- [x] Remove conventional commit prefix: `feat: add auth` → `Add auth`
- [x] Remove scope: `feat(api): new endpoint` → `New endpoint`
- [x] Capitalize first letter
- [x] Remove trailing punctuation if present
- [x] Handle multi-line commits (use first line only)
- [x] Deduplicate if squash commits include original messages

### Task 6: Implement Artifact Output
- [x] Save release notes to `release_notes.md` in artifacts
- [x] Artifact path: `.adw/runs/{run_id}/artifacts/ship/release_notes.md`
- [x] Mark as optional artifact (defined in config.yaml)
- [x] Include in ship_report.md as embedded section (deferred to Story 15.7)

### Task 7: Write Tests
- [x] Test commit categorization for each prefix type
- [x] Test version header with new version
- [x] Test version header with "Unreleased"
- [x] Test empty section omission
- [x] Test commit message cleaning
- [x] Test Keep a Changelog format output
- [x] Test artifact file creation

---

## Dependencies

- **Depends On:** 15.1 (Ship Phase SDK Integration), 15.2 (Context Gathering)
- **Blocks:** 15.7 (Ship Report Generation)
- **Can Parallel With:** 15.3 (Deployment Command Execution)

### Dependency Rationale
- Requires ship phase infrastructure from 15.1
- Commit list gathered in step 1 (15.2)
- Can run in parallel with command execution (15.3) since it uses commit history
- Release notes included in final ship report (15.7)

---

## Developer Context

### Technical Requirements

1. **Conventional Commit Parsing**
   - Parse prefix pattern: `type(scope)?: description`
   - Handle with/without scope
   - Handle breaking change indicator (`!`)

2. **Keep a Changelog Format**
   - Standard format from keepachangelog.com
   - Semantic versioning compatibility
   - Human-readable sections

3. **Artifact Management**
   - Save to ship artifacts directory
   - Optional artifact (ship can succeed without it)
   - Embed in ship_report.md

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/ship/instructions.xml  # Step 4
```

**Artifact Location:**
```
.adw/runs/{run_id}/artifacts/ship/release_notes.md
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| None | - | Pure LLM text generation |

### File Structure Requirements

**Instructions.xml Structure (Step 4):**
```xml
<step n="4" goal="Generate release notes">
  <action>Categorize commits from step 1 context:</action>
  <categories>
    <category name="Added" prefixes="feat:, feature:, add:" />
    <category name="Changed" prefixes="refactor:, update:, change:, improve:" />
    <category name="Fixed" prefixes="fix:, bugfix:, patch:, resolve:" />
    <category name="Documentation" prefixes="docs:, doc:" />
    <category name="Other" prefixes="chore:, ci:, test:, style:, build:" />
  </categories>

  <action>Determine version header:</action>
  <check if="version_bump executed">
    <action>Use new version: {{new_version}}</action>
  </check>
  <check if="no version_bump">
    <action>Use "Unreleased"</action>
  </check>

  <action>Generate release notes in Keep a Changelog format</action>
  <action>Clean commit messages (remove prefix, capitalize)</action>
  <action>Omit empty sections</action>
  <action>Save to release_notes.md artifact</action>
</step>
```

**Release Notes Output Format:**
```markdown
## [1.2.3] - 2026-01-18

### Added
- User authentication with OAuth2 support
- Dashboard widget for quick stats
- API endpoint for bulk operations

### Changed
- Improved database query performance
- Updated error messages for clarity

### Fixed
- Login redirect loop on expired sessions
- File upload size validation

### Documentation
- Added API reference for new endpoints
- Updated installation guide
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_release_notes.py
class TestReleaseNotes:
    def test_categorize_feat_commits(self):
        """feat: commits go to Added section."""

    def test_categorize_fix_commits(self):
        """fix: commits go to Fixed section."""

    def test_categorize_refactor_commits(self):
        """refactor: commits go to Changed section."""

    def test_categorize_unknown_prefix(self):
        """Commits without prefix go to Other section."""

    def test_version_header_with_new_version(self):
        """Header uses new version when version_bump ran."""

    def test_version_header_unreleased(self):
        """Header uses 'Unreleased' when no version_bump."""

    def test_empty_section_omitted(self):
        """Sections with no commits are not included."""

    def test_commit_message_cleaning(self):
        """Commit messages cleaned: remove prefix, capitalize."""

    def test_keep_a_changelog_format(self):
        """Output matches Keep a Changelog specification."""
```

---

## Previous Story Intelligence

**From Story 15.1:**
- Artifact definitions in config.yaml (release_notes optional)
- ShipConfig structure for configuration access

**From Story 15.2:**
- Commit list gathered via `git log <tag>..HEAD`
- Last tag identified via `git describe --tags`
- Current version known from version file detection

**Relevant Patterns:**
- Artifacts saved to `.adw/runs/{run_id}/artifacts/{phase}/`
- LLM generates formatted markdown output
- Text processing via LLM reasoning

---

## Git Intelligence

**Established Patterns:**
- Conventional commits used throughout project
- Commit format: `type(scope): description`
- Breaking changes marked with `!`

**Recent Commit Examples:**
```
feat(wizard): Story 14-4 - Port Configuration Step
fix(validation): handle empty artifact list
refactor(orchestrator): simplify phase transitions
docs(readme): update installation instructions
chore(deps): bump pydantic to 2.12.1
```

---

## Latest Technical Information

**Keep a Changelog Standard (v1.1.0):**
- Format: https://keepachangelog.com/en/1.1.0/
- Sections: Added, Changed, Deprecated, Removed, Fixed, Security
- Date format: YYYY-MM-DD
- Version format: [Semantic Version]

**Conventional Commits (v1.0.0):**
- Format: `type(scope)?: description`
- Breaking change: `type!:` or `BREAKING CHANGE:` footer
- Types: feat, fix, docs, style, refactor, test, chore

---

## Project Context Reference

See: `_bmad-output/architecture.md`

Key patterns and rules from project context:
- **Artifacts in phase folder**: ship artifacts in `artifacts/ship/`
- **Markdown output**: LLM generates clean markdown
- **Optional artifacts**: release_notes not required for success

---

## Dev Notes

### Implementation Approach

1. Parse commits into categories
2. Determine version header
3. Generate each section
4. Omit empty sections
5. Clean commit messages
6. Format as markdown
7. Save artifact

### Key Design Decisions

1. **Keep a Changelog format**: Industry standard, widely recognized
2. **Conventional commit mapping**: Standard prefix → section mapping
3. **Optional artifact**: Ship can succeed without release notes
4. **First line only**: Multi-line commits use first line
5. **Prefix removal**: Cleaner reading experience

### Commit Prefix Mapping

| Prefix | Section |
|--------|---------|
| feat:, feature:, add: | Added |
| fix:, bugfix:, patch:, resolve: | Fixed |
| refactor:, update:, change:, improve: | Changed |
| docs:, doc: | Documentation |
| chore:, ci:, test:, style:, build: | Other |
| (no prefix) | Other |
| BREAKING: | Note in relevant section |

### Message Cleaning Examples

| Original | Cleaned |
|----------|---------|
| `feat: add auth` | Add auth |
| `fix(api): null check` | Null check |
| `feat!: breaking change` | Breaking change |
| `FEAT: UPPERCASE` | Uppercase |

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.4]
- [Source: keepachangelog.com/en/1.1.0/]
- [Source: conventionalcommits.org/en/v1.0.0/]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.4

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - clean implementation without debug issues

### Completion Notes List

1. **Task 1**: Added Step 4 to ship/instructions.xml with 6 substeps for release notes generation
2. **Task 2**: Commit categorization implemented via conventional commit prefix matching (Added, Changed, Fixed, Documentation, Other)
3. **Task 3**: Version header logic uses new_version from Step 3 or "Unreleased" fallback with YYYY-MM-DD date
4. **Task 4**: Keep a Changelog format with conditional section rendering (empty sections omitted)
5. **Task 5**: Commit message cleaning rules (remove prefix, scope, capitalize, first line only, dedupe)
6. **Task 6**: Artifact saved to artifacts_dir/ship/release_notes.md; already configured as optional in config.yaml
7. **Task 7**: Created 42 tests validating instruction structure, prefix coverage, and format compliance

**Implementation Approach**: This story implements release notes generation as LLM instructions (instructions.xml) rather than Python code, since the feature is executed by an LLM during the ship phase. Tests validate the instruction structure and content.

### File List

**Created:**
- `tests/unit/ship/__init__.py` - Test package init
- `tests/unit/ship/test_release_notes.py` - 42 tests for release notes instructions

**Modified:**
- `src/adw/defaults/commands/ship/instructions.xml` - Added Step 4: Release Notes Generation
- `_bmad-output/implementation-artifacts/stories/15-4-release-notes-generation.md` - Task checkboxes and dev record
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Status updated to in-progress
