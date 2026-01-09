# Story ISS-021: Remove Evidence Gathering Completely

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure (Tech Debt)
Created: 2026-01-09
Issue Reference: ISS-021-remove-evidence-gathering-completely.md

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer,
I want all evidence gathering code removed from the SDK,
so that the codebase is simpler and dead code is eliminated.

## Acceptance Criteria

**Given** the existing evidence gathering subsystem in SDK
**When** this story is complete
**Then** all evidence gathering code is removed from the codebase

**Given** the validate phase execution
**When** called by orchestrator
**Then** no evidence gathering, manifest generation, or optimization occurs

**Given** imports from `adw.evidence` or `adw.models.evidence`
**When** any code attempts to import them
**Then** import errors occur (modules don't exist)

**Given** test suite execution
**When** `pytest` is run
**Then** all tests pass with no evidence-related test failures

## Tasks / Subtasks

- [ ] **Task 1: Remove evidence module directory**
  - Delete `src/adw/evidence/` directory entirely (13 files)
  - Verify no dangling imports

- [ ] **Task 2: Remove evidence models**
  - Delete `src/adw/models/evidence.py` entirely (~1350 lines)
  - Update `src/adw/models/__init__.py`:
    - Remove imports (lines 49-81)
    - Remove from `__all__` list (lines 140-176)
    - Remove `model_rebuild()` calls if only for evidence models

- [ ] **Task 3: Remove orchestrator evidence integration**
  - In `src/adw/core/orchestrator.py`:
    - Remove evidence imports (lines 28-54)
    - Remove `_detect_and_store_platform()` method (lines 1486-1526)
    - Remove `_gather_evidence()` method (lines 1528-1796)
    - Remove `_optimize_evidence()` method (lines 1798-1846)
    - Remove call sites:
      - Line 1356: `context = self._detect_and_store_platform(context)`
      - Line 1366: `self._gather_evidence(context)`
      - Line 1370: `self._optimize_evidence(context)`

- [ ] **Task 4: Remove evidence test directory**
  - Delete `tests/unit/evidence/` directory entirely (16 test files)
  - Verify test suite still passes

- [ ] **Task 5: Verify and clean up any remaining references**
  - Search codebase for any remaining `evidence` imports
  - Search for `PlatformType`, `EvidenceStrategy`, etc. references
  - Clean up any configuration references in project.yaml templates

- [ ] **Task 6: Run full test suite and verify**
  - Run `pytest` to ensure all tests pass
  - Run `uv run mypy src/adw` to verify type checking passes
  - Run `uv run ruff check src/adw` to verify linting passes

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** Epic 8 (Evidence Gathering) - Being removed by this refactor

The existing evidence system includes:
- Platform detection (CLI, WEB, MOBILE, BACKEND)
- CLI terminal output capture
- Web screenshot capture via Playwright
- Mobile screenshot capture via iOS Simulator/Android Emulator
- API request/response capture via httpx
- Evidence manifest generation
- Evidence file optimization (image compression, text truncation)

All of this is dead code since Epic 16 removed the validation loop that consumed evidence.

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
1. **Complete removal**: Every file related to evidence gathering must be deleted
2. **No orphan imports**: All import statements for evidence modules must be removed
3. **No broken tests**: Test suite must pass after removal
4. **No type errors**: `mypy` must pass with no new errors
5. **No lint errors**: `ruff` must pass with no new errors

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From Epic 16 philosophy:**
- SDK orchestration = minimal
- LLM handles validation internally
- Evidence gathering was designed for old multi-phase validation loop
- With single-prompt validation, evidence is not needed

**Module dependency analysis:**
```
BEFORE:
orchestrator.py
├── imports adw.evidence (16 imports)
├── imports adw.models.evidence (4 imports)
├── _detect_and_store_platform()
├── _gather_evidence()
└── _optimize_evidence()

AFTER:
orchestrator.py
├── (no evidence imports)
└── (no evidence methods)
```

**Files to DELETE entirely:**
```
src/adw/evidence/           # 13 files, ~2000 lines
├── __init__.py
├── api_capture.py
├── cli_capture.py
├── cli_gatherer.py
├── config_loader.py
├── detector.py
├── evidence_writer.py
├── file_writer.py
├── manifest.py
├── mobile_capture.py
├── optimizer.py
├── summary_generator.py
└── web_capture.py

src/adw/models/evidence.py  # 1 file, ~1350 lines

tests/unit/evidence/        # 16 test files
├── test_api_capture.py
├── test_cli_capture.py
├── test_cli_gatherer.py
├── test_config_loader.py
├── test_detector.py
├── test_evidence_integration.py
├── test_evidence_writer.py
├── test_file_writer.py
├── test_manifest.py
├── test_mobile_capture.py
├── test_optimizer.py
├── test_summary_generator.py
└── test_web_capture.py
```

**Files to MODIFY:**
```
src/adw/core/orchestrator.py
├── Remove 20 import lines (lines 28-54)
├── Remove _detect_and_store_platform() (~40 lines)
├── Remove _gather_evidence() (~270 lines)
├── Remove _optimize_evidence() (~50 lines)
└── Remove 3 call sites

src/adw/models/__init__.py
├── Remove 33 lines of imports (lines 49-81)
└── Remove 37 lines from __all__ (lines 140-176)
```

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

**Optional dependencies that may become unused after removal:**
- `httpx` - Was used for API evidence capture (check if used elsewhere)
- `Playwright` - Was used for web screenshots (check if used elsewhere)
- `Pillow` - Was used for image optimization (check if used elsewhere)

**Note:** Do NOT remove these from pyproject.toml unless confirmed unused elsewhere.

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**DELETE these paths:**
```bash
# Evidence module (entire directory)
rm -rf src/adw/evidence/

# Evidence models
rm src/adw/models/evidence.py

# Evidence tests (entire directory)
rm -rf tests/unit/evidence/
```

**MODIFY these files:**
```
src/adw/core/orchestrator.py     # Remove imports and methods
src/adw/models/__init__.py       # Remove evidence exports
```

**VERIFY no remaining references in:**
```
src/adw/**/*.py                  # Any source file
tests/**/*.py                    # Any test file
*.yaml                           # Configuration files
```

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **No new tests needed** - This is a deletion story

2. **Verify test suite passes after deletion:**
   ```bash
   uv run pytest tests/ -v
   ```

3. **Verify type checking passes:**
   ```bash
   uv run mypy src/adw
   ```

4. **Verify linting passes:**
   ```bash
   uv run ruff check src/adw
   ```

5. **Verify no import errors:**
   ```bash
   uv run python -c "from adw.core.orchestrator import Orchestrator; print('OK')"
   ```

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

**From Story 16-1 (Remove SDK Validation Loop):**
- Deletion stories follow a clear pattern: DELETE → MODIFY imports → RUN tests
- Total code removed: ~850 lines from validation loop
- Commit pattern: `refactor(epic-16): Remove X infrastructure (Story Y)`
- Coordinate with other Epic 16 stories - this aligns with simplification goal

**From Issue ISS-021:**
- Evidence gathering runs after validate phase but serves no purpose
- Logs show:
  ```
  09:08:31 [INFO ] [phase] Starting evidence gathering
  09:08:31 [INFO ] [phase] CLI evidence gathered
  09:08:31 [INFO ] [phase] Evidence manifest generated
  09:08:31 [INFO ] [phase] Evidence copied to validate artifacts
  09:08:31 [INFO ] [phase] Evidence optimization completed
  ```
- User impact: Unnecessary processing time, confusing logs, dead code burden

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Recent Epic 16 commits:**
- `fd91f92` Ticket restructuring
- `e6e9a1e` Add new validate command

**Related Epic 8 commits (what we're removing):**
- All evidence gathering was implemented in Epic 8
- Evidence integration added in ISS-010 bugfix

**Commit pattern to follow:**
```
refactor(epic-16): Remove evidence gathering subsystem (ISS-021)

- Delete src/adw/evidence/ directory (13 files, ~2000 lines)
- Delete src/adw/models/evidence.py (~1350 lines)
- Delete tests/unit/evidence/ directory (16 files)
- Remove evidence integration from orchestrator.py (~360 lines)
- Remove evidence exports from models/__init__.py (~70 lines)

Lines removed: ~3800
Closes ISS-021
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Simplification approach aligns with:**
- Epic 16's goal: "Maximum simplicity" - SDK orchestration = minimal
- Claude Code's native validation capabilities
- ADW principle: "LLM does the work, SDK orchestrates"
- Reduced maintenance burden and cognitive overhead

**Evidence gathering was designed for:**
- Old multi-phase validation loop (verify → triage → fix → repeat)
- Visual evidence for human review
- Platform-specific capture (screenshots, terminal output, API responses)

**With Epic 16's single-prompt validation:**
- LLM validates and fixes in one pass
- No need to capture evidence for triage decisions
- No human-in-the-loop review requiring screenshots

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: Project root for architecture patterns

Key patterns and rules from project context:
- **Deletion approach:** Delete files first, then clean imports, then run tests
- **Import cleanup:** Remove from `__all__` lists AND import statements
- **Type safety:** Ensure `mypy` passes after removal
- **Lint compliance:** Ensure `ruff` passes after removal

---

## Dev Notes

- This story is about DELETION and SIMPLIFICATION
- Goal: Remove ~3800 lines of dead code
- Evidence gathering was the largest subsystem in ADW
- After this, the codebase will be significantly leaner
- Optional dependencies (httpx, Playwright, Pillow) may become unused - DO NOT remove from pyproject.toml without verification

### Project Structure Notes

- Evidence module was fully isolated - no cross-dependencies except orchestrator
- Models were also isolated in evidence.py
- Tests were self-contained in tests/unit/evidence/

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-021-remove-evidence-gathering-completely.md]
- [Source: _bmad-output/epics/epic-16-validation-simplification.md]
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md] (what's being removed)
- [Source: src/adw/core/orchestrator.py] (integration points)
- [Source: src/adw/evidence/__init__.py] (current exports)

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created by BMAD create-story workflow with exhaustive artifact analysis.

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

Files to DELETE:
- src/adw/evidence/ (entire directory - 13 files)
- src/adw/models/evidence.py
- tests/unit/evidence/ (entire directory - 16 files)

Files to MODIFY:
- src/adw/core/orchestrator.py
- src/adw/models/__init__.py

---

## Dependencies

- **Depends On:** Story 16.1 (Remove SDK Validation Loop) - DONE
- **Blocks:** None
- **Can Parallel With:** Story 16.3, ISS-022, ISS-023
