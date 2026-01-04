# Story 9.3: Capture Git Diff as Artifact

Status: drafted
Epic: 9 - Git Integration & Documentation
Created: 2026-01-04

---

## Story

As a developer,
I want the git diff captured as a Build phase artifact,
so that changes can be reviewed and included in PR description.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] Create `src/adw/hooks/git_diff.py` module
- [ ] Implement `capture_diff(since: str = "HEAD~1") -> str`
  - Use `git diff --stat` for summary
  - Use `git diff` for full content
- [ ] Implement `capture_staged_diff() -> str`
  - Use `git diff --cached` for uncommitted staged changes
- [ ] Implement `truncate_diff(diff: str, max_bytes: int = 102400) -> str`
  - Preserve file headers when truncating
  - Add truncation notice at end
- [ ] Implement `get_diff_stats(diff: str) -> DiffStats`
  - Parse insertions/deletions from --stat output
- [ ] Integrate diff capture into Build phase artifact collection
- [ ] Add diff to template variable namespace as `{{artifacts.build.diff}}`
- [ ] Write unit tests for diff parsing and truncation
- [ ] Write integration tests with actual git changes

---

## Developer Context

### Technical Requirements

- Diff output can be very large - stream to file, don't hold in memory
- Binary files should be noted but content skipped
- Colorized output must be disabled (`--no-color`)
- Handle repos with no commits (initial commit case)

### Architecture Compliance

- Artifacts stored in: `.agent/runs/<run_id>/artifacts/build/`
- Use ArtifactStore interface for saving
- Diff stats model in `src/adw/models/`

### Library & Framework Requirements

| Library | Usage |
|---------|-------|
| subprocess | Git diff execution |
| pathlib | Artifact path handling |

### File Structure Requirements

```
src/adw/hooks/
├── git_diff.py      # NEW

src/adw/models/
├── artifacts.py     # Add DiffStats model

.agent/runs/<run_id>/artifacts/build/
├── diff.txt         # Output location
└── diff_stats.json  # Parsed statistics
```

### Testing Requirements

- Unit tests: `tests/unit/hooks/test_git_diff.py`
- Test truncation preserves valid diff format
- Test binary file handling
- Test empty diff case

---

## Dependencies

- **Depends on:** None (Wave 1 - can start in parallel with 9.1)
- **Blocks:** 9.4 (Generate PR Description) - needs diff artifact

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Pydantic models for structured data (DiffStats)
- Context managers for file operations
- Full type annotations required

---

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List

