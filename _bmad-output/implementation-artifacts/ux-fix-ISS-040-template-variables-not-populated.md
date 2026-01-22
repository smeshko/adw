# Story: UX Fix ISS-040 - Template Variables Not Populated

Status: ready-for-dev
Linear Issue: not-configured
Epic: QA Fixes (2026-01-21 Run Analysis)
Created: 2026-01-22

---

## Story

As a **developer running full ADW pipeline executions**,
I want **template variables for PR information and build artifacts to be properly populated**,
so that **the LLM receives complete context for ship and document phases instead of unresolved placeholders**.

## Acceptance Criteria

### AC1: PR Variables Populated in Ship Phase
- [ ] `{{pr_number}}` resolves to the actual PR number from pre-hook output
- [ ] `{{pr_url}}` resolves to the actual PR URL from pre-hook output
- [ ] `{{pr_state}}` resolves to the PR state (OPEN, MERGED, CLOSED)
- [ ] `{{pr_mergeable}}` resolves to mergeability status
- [ ] Variables gracefully default to empty string if pre-hook fails or values missing
- [ ] No "Unknown template variable left as-is" warnings in logs for PR variables

### AC2: Build Artifacts Available in Document Phase
- [ ] `{{artifacts.build.diff_stats}}` resolves to diff stats JSON content when available
- [ ] `{{artifacts.build.diff}}` resolves to diff content when available
- [ ] Missing artifacts gracefully resolve to empty string (not placeholder text)
- [ ] BuildExtension artifact capture is validated to work correctly
- [ ] No "Unknown template variable left as-is" warnings for build artifacts

### AC3: Backward Compatibility
- [ ] Existing templates continue to work without modification
- [ ] `{{pre_hook_output}}` still contains raw stdout (for fallback)
- [ ] Phase execution timing unaffected by variable extraction

## Tasks / Subtasks

### Task 1: Parse PR Variables from Pre-Hook Output
**Goal:** Extract structured PR information from pre.sh stdout

1.1. Add regex parsing in `PhaseRunner._load_and_render_prompt()` to extract PR values from pre_hook_output
  - Pattern: `PR #(\d+):` for pr_number
  - Pattern: `URL: (.+)` for pr_url
  - Pattern: `State: (\w+)` for pr_state
  - Pattern: `Mergeable: (\w+)` for pr_mergeable

1.2. Add extracted values to template variables dict:
```python
# In _load_and_render_prompt after Step 2: Load and render prompt
pr_vars = self._parse_pr_variables(pre_hook_output)
variables.update(pr_vars)
```

1.3. Create `_parse_pr_variables(self, output: str) -> dict[str, str]` method

### Task 2: Handle Missing Build Artifacts Gracefully
**Goal:** Ensure artifact references don't produce warnings when artifacts don't exist

2.1. Verify BuildExtension.extra_artifacts() is called during build phase
  - Check extension_registry.call_extra_artifacts() in _capture_artifacts()
  - Confirm artifacts are stored with correct names: "diff.txt", "diff_stats.json"

2.2. Update template validation in `validate_artifact_references()` to handle optional artifacts
  - Document phase template references optional build artifacts
  - These should warn at DEBUG level, not WARN level
  - Or: mark certain artifact references as "optional" in templates

2.3. Alternative: Ensure artifact map always has entries for expected artifacts
  - In _build_artifacts_map(), add empty placeholders for known artifacts

### Task 3: Update Ship Phase Template Variables
**Goal:** Add PR variables to the template context for ship phase

3.1. In PhaseRunner._load_and_render_prompt(), detect ship phase
3.2. Parse pre_hook_output for PR information
3.3. Add pr_number, pr_url, pr_state, pr_mergeable to variables dict

### Task 4: Unit Tests
**Goal:** Comprehensive test coverage for new functionality

4.1. Test _parse_pr_variables() with valid pre-hook output
4.2. Test _parse_pr_variables() with missing/partial output
4.3. Test template rendering with PR variables
4.4. Test artifact validation with optional artifacts
4.5. Integration test: full pipeline with PR and build artifacts

---

## Developer Context

### Technical Requirements

**Root Cause Analysis:**

**Problem 1: PR Variables (Ship Phase)**
- The ship phase pre.sh hook outputs PR information to stdout
- The hook exports environment variables (ADW_PR_NUMBER, etc.)
- **Issue:** Subprocess env vars don't persist to parent Python process
- **Issue:** Template engine receives raw `pre_hook_output` string, not parsed values
- Template expects `{{pr_number}}` but only `{{pre_hook_output}}` is available

**Problem 2: Build Artifacts (Document Phase)**
- BuildExtension.extra_artifacts() produces diff.txt and diff_stats.json
- These are stored as artifacts in `.adw/runs/<run_id>/artifacts/build/`
- Document phase template references `{{artifacts.build.diff}}` and `{{artifacts.build.diff_stats}}`
- **Issue:** Artifact file names don't match template references
  - File: `diff.txt` → Template: `{{artifacts.build.diff}}`
  - File: `diff_stats.json` → Template: `{{artifacts.build.diff_stats}}`
- **Issue:** When no changes exist, empty list returned (no artifacts created)

### Architecture Compliance

**Module Boundaries:**
- Template variable extraction: `src/adw/commands/template.py` OR `src/adw/core/phase_runner.py`
- Artifact capture: `src/adw/core/extensions/build.py`
- Template rendering: `src/adw/commands/template.py` (TemplateEngine class)

**Pydantic Models:**
- No new models required
- Variables are passed as `dict[str, Any]` to template engine

**Exception Handling:**
- Use existing ConfigError for template errors
- PR parsing failures should be silent (empty string defaults)

**Logging:**
- Use existing logger patterns: `logger.debug()` for parsing details
- Remove or downgrade WARN log for missing optional variables

### Library & Framework Requirements

**Python:** 3.13+ (use modern syntax: `X | None` not `Optional[X]`)
**Rich:** Not used in this fix (template engine is pure Python)
**Pydantic:** Only for model_dump() if needed
**Regex:** Standard library `re` module for parsing

### File Structure Requirements

**Files to Modify:**

1. `src/adw/core/phase_runner.py:364-383`
   - Add PR variable extraction for ship phase
   - Location: `_load_and_render_prompt()` method, variables dict construction

2. `src/adw/commands/template.py`
   - Option A: Add helper function `parse_pre_hook_variables(output: str) -> dict`
   - Option B: Modify `validate_artifact_references()` to handle optional refs

3. `src/adw/defaults/commands/ship/prompt.md:32-36`
   - Option: Remove direct PR variable refs and use `{{pre_hook_output}}` with LLM parsing
   - OR: Keep refs once variables are populated

4. `src/adw/defaults/commands/document/prompt.md:16-19`
   - Option: Mark artifact refs as optional
   - OR: Use conditional template syntax if supported

**Files to Read (No Changes):**

- `src/adw/core/extensions/build.py` - Understand artifact naming
- `src/adw/defaults/commands/ship/pre.sh` - Understand output format

### Testing Requirements

**Test Files:**
- `tests/unit/commands/test_template.py` - Add tests for PR variable parsing
- `tests/unit/core/test_phase_runner.py` - Add tests for variable population
- `tests/integration/` - Optional full pipeline test

**Test Patterns:**
```python
# Example test structure
def test_parse_pr_variables_from_pre_hook_output():
    output = """Ship phase pre-hook: Validating PR exists...
PR #123: Add feature X
URL: https://github.com/org/repo/pull/123
State: OPEN
Mergeable: MERGEABLE
"""
    result = parse_pre_hook_variables(output)
    assert result["pr_number"] == "123"
    assert result["pr_url"] == "https://github.com/org/repo/pull/123"
    assert result["pr_state"] == "OPEN"
    assert result["pr_mergeable"] == "MERGEABLE"
```

**Coverage Requirements:**
- Maintain >80% coverage
- Test both success and failure paths
- Test empty/missing output handling

---

## Previous Story Intelligence

N/A - This is a standalone QA fix, not part of an epic sequence.

**Related Previous Issues:**
- ISS-017: Template logic consolidation (FIXED) - Centralized template logic
- ISS-015: Phase-specific input context (FIXED) - Added input_files support
- ISS-029: Phase config not honored (FIXED) - Fixed timeout/enabled from configs

**Learnings from Related Fixes:**
- Template variables dict constructed in `_load_and_render_prompt()` (lines 364-383)
- Extension system handles phase-specific artifact capture
- Artifact naming: stem of filename becomes template key (plan.md → plan)

---

## Git Intelligence

**Recent Commits:**
- `b45bf41` chore: bump version to 0.1.36
- `db84a58` Fix prompt
- `d62305d` refactor(logging): improve log levels and reduce noise (#148)

**Code Patterns Observed:**
- Logging refactoring in progress (d62305d)
- Template/prompt fixes being made (db84a58)
- Use structured logging with extra={} dict
- Use snake_case for all identifiers

---

## Latest Technical Information

**Python 3.13 Patterns:**
- Use `X | None` for optional types (not `Optional[X]`)
- Use `list[str]` not `List[str]`
- Use `dict[str, Any]` not `Dict[str, Any]`

**Regex for PR Parsing:**
```python
import re

PR_NUMBER_PATTERN = re.compile(r"PR #(\d+):")
PR_URL_PATTERN = re.compile(r"URL: (https?://\S+)")
PR_STATE_PATTERN = re.compile(r"State: (\w+)")
PR_MERGEABLE_PATTERN = re.compile(r"Mergeable: (\w+)")

def parse_pre_hook_variables(output: str) -> dict[str, str]:
    """Extract PR information from pre-hook stdout."""
    result: dict[str, str] = {
        "pr_number": "",
        "pr_url": "",
        "pr_state": "",
        "pr_mergeable": "",
    }

    if match := PR_NUMBER_PATTERN.search(output):
        result["pr_number"] = match.group(1)
    if match := PR_URL_PATTERN.search(output):
        result["pr_url"] = match.group(1)
    if match := PR_STATE_PATTERN.search(output):
        result["pr_state"] = match.group(1)
    if match := PR_MERGEABLE_PATTERN.search(output):
        result["pr_mergeable"] = match.group(1)

    return result
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in `models/`** - No new models needed for this fix
- **Exception hierarchy** - Use `ConfigError` for template errors
- **Type annotations required** - Full annotations on all functions
- **Rich for CLI output** - Not applicable (template engine is internal)
- **Structured logging** - Use `logger.debug()` with extra={} dict

---

## Dev Notes

### Implementation Strategy

**Option A: Parse Pre-Hook Output (Recommended)**
- Add `_parse_pr_variables()` method to PhaseRunner
- Extract PR info using regex patterns
- Add to variables dict before template rendering
- Pros: Clean separation, testable, explicit
- Cons: Regex parsing can be fragile

**Option B: Structured Hook Output**
- Modify pre.sh to output JSON
- Parse JSON in PhaseRunner
- Pros: More robust parsing
- Cons: Requires hook changes, backward compat

**Option C: Template-Side Handling**
- Keep current variables
- Let LLM extract from `{{pre_hook_output}}`
- Pros: No code changes
- Cons: Less explicit, LLM may fail to extract

**Recommended: Option A** - Parse pre-hook output with regex

### Artifact Naming Investigation

Current artifact storage in BuildExtension:
```python
artifacts.append(("diff.txt", diff_content))
artifacts.append(("diff_stats.json", stats_content))
```

Template access pattern:
```
{{artifacts.build.diff_stats}}  # Expects: diff_stats (without .json)
{{artifacts.build.diff}}        # Expects: diff (without .txt)
```

Artifact loading in `_load_phase_artifacts()`:
```python
# Strip extension: plan.md -> plan
name = Path(artifact["name"]).stem
```

So `diff.txt` → `diff` and `diff_stats.json` → `diff_stats` - naming should work.

**Investigate:** Why are artifacts not being found?
- Check if BuildExtension is registered in extension_registry
- Check if artifacts are actually created during build phase
- Check if artifact map is correctly built for document phase

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming) ✓
- No conflicts detected
- Follows existing patterns in phase_runner.py

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-040-template-variables-not-populated.md] - Original issue
- [Source: src/adw/core/phase_runner.py:364-383] - Template variables construction
- [Source: src/adw/commands/template.py] - Template engine implementation
- [Source: src/adw/defaults/commands/ship/pre.sh] - Pre-hook output format
- [Source: src/adw/core/extensions/build.py:70-141] - Build artifact capture

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

<!-- Populated by dev agent -->

### Debug Log References

### Completion Notes List

### File List

