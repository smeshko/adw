# Story 9.4: Generate PR Description

Status: drafted
Epic: 9 - Git Integration & Documentation
Created: 2026-01-04

---

## Story

As a user,
I want a PR-ready description generated,
so that I can quickly create a pull request.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] Create PR description prompt template `defaults/commands/document/prompt.md`
- [ ] Define PR description sections:
  - Summary (1-2 sentences)
  - Changes (bullet list from diff stats)
  - Testing (from test results artifact)
  - Evidence (from evidence manifest if exists)
  - Screenshots (placeholder links if evidence includes images)
- [ ] Implement PR description artifact saving
- [ ] Add `{{artifacts.verify.evidence_manifest}}` to template variables
- [ ] Create `PRDescription` Pydantic model for structured output
- [ ] Update run completion panel to show PR description path
- [ ] Implement schema validation for PR description output
- [ ] Write unit tests for PR description model
- [ ] Write integration tests for Document phase with PR output

---

## Developer Context

### Technical Requirements

- PR description must be valid GitHub-flavored Markdown
- Links to evidence should be relative paths
- Handle missing evidence manifest gracefully
- Max length: ~4000 chars (GitHub PR description limit)

### Architecture Compliance

- Prompt templates in: `defaults/commands/document/`
- Artifacts in: `.agent/runs/<run_id>/artifacts/document/`
- Use structured output schema for LLM response

### Library & Framework Requirements

| Library | Usage |
|---------|-------|
| Pydantic | PRDescription model |
| jinja2 | Template rendering (if needed) |

### File Structure Requirements

```
defaults/commands/document/
├── prompt.md        # NEW - PR description prompt
├── config.yaml      # Phase config
└── schema.json      # NEW - PR description schema

src/adw/models/
├── pr.py            # NEW - PRDescription model

.agent/runs/<run_id>/artifacts/document/
└── pr_description.md  # Output location
```

### Testing Requirements

- Unit tests: `tests/unit/models/test_pr.py`
- Integration tests: `tests/integration/test_document_phase.py`
- Test with/without evidence manifest
- Test truncation for long descriptions

---

## Dependencies

- **Depends On:** 9.2 (Stage and Commit), 9.3 (Capture Git Diff)
- **Blocks:** 9.5 (Support PR Creation Command)
- **Can Parallel With:** None

### Dependency Rationale
- 9.2: Needs commit history for the Changes section
- 9.3: Needs diff stats artifact for the Changes section
- 9.5: PR creation command uses the generated description

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- All models in `src/adw/models/`
- Schema validation for LLM output
- Rich for CLI output

---

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List

