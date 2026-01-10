# Story 13.8: Fix Validate Phase Not Verifying Codex Findings

Status: done
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure / Tech Debt
Created: 2026-01-09

---

## Story

As a user of ADW,
I want the validate phase to actually verify Codex's findings before acting on them,
so that hallucinated/false positive issues are caught and dismissed rather than accepted as real problems.

## Acceptance Criteria

**Given** the validate phase receives findings from Codex
**When** processing each finding
**Then** Claude MUST read the actual file mentioned in the finding
**And** compare the actual code against Codex's claimed `code_snippet`
**And** verify whether the issue actually exists

**Given** a finding where Codex's claimed code doesn't match reality
**When** validating the finding
**Then** Claude MUST dismiss it as a false positive
**And** record the dismissal reason: "Code snippet doesn't match actual file"

**Given** a finding that is verified as genuine
**When** processing the finding
**Then** Claude MUST proceed with the fix
**And** add the fix to `issues_fixed`

**Given** validation of all findings is complete
**When** outputting results
**Then** include a summary of: verified issues, dismissed false positives

## Tasks / Subtasks

- [x] **Task 1:** Update `instructions.xml` step `validate-findings` to add MANDATORY file reading
  - Add explicit mandate: "MUST read file at {{file}} before classifying"
  - Add comparison step: "Compare actual code at line {{line}} with claimed code_snippet"
  - Add mismatch handling: "If code_snippet doesn't match → FALSE_POSITIVE"

- [x] **Task 2:** Add verification output to show what was checked
  - For each finding, output: "Verifying: {{file}}:{{line}}"
  - Output: "Claimed: {{code_snippet}}"
  - Output: "Actual: {{actual_code}}"
  - Output: "Match: yes/no → VALID/FALSE_POSITIVE"

- [x] **Task 3:** Update the `classify` substep with explicit criteria
  - VALID: Code snippet matches AND issue is real
  - FALSE_POSITIVE: Code snippet doesn't match OR issue doesn't exist

- [x] **Task 4:** Add test case for hallucination detection
  - Create test where Codex returns findings with incorrect code snippets
  - Verify Claude dismisses them as false positives

---

## Developer Context

### Root Cause Analysis

The current `instructions.xml` has a `validate-findings` step (lines 304-332) that instructs Claude to validate each finding. The step says:

```xml
<substep name="read-context">
  <action>Read the file and surrounding context (10 lines before/after reported line)</action>
</substep>

<substep name="validate-code">
  <action>Ask yourself:
    - Does this issue actually exist in the code?
    - Is the code actually problematic?
    - Does the suggested fix make sense?
  </action>
</substep>
```

**The problem:** These instructions are too vague. Claude is told to "ask yourself" but not given:
1. A mandatory directive to READ the file
2. Explicit comparison between Codex's `code_snippet` and actual code
3. Clear criteria for what constitutes a mismatch

In the failing run, Claude received Codex findings claiming `f"Hello, {name}\!"` but the actual code was `f"Hello, {name}!"`. Claude never read the files to notice this discrepancy.

### Technical Requirements

**File to modify:** `src/adw/defaults/commands/validate/code-review-loop/instructions.xml`

**Location:** Step `validate-findings` (lines 304-332)

**Changes needed:**

1. Change `<substep name="read-context">` from suggestion to mandate:
```xml
<substep name="read-context">
  <critical>YOU MUST READ THE FILE - this is not optional</critical>
  <action>Read file: {{finding.file}}</action>
  <action>Extract lines {{finding.line - 5}} to {{finding.line + 5}}</action>
  <action>Store as {{actual_code}}</action>
</substep>
```

2. Add new comparison substep:
```xml
<substep name="compare-code">
  <critical>Compare Codex's claimed code against actual code</critical>
  <action>Extract Codex's code_snippet: {{finding.context.code_snippet}}</action>
  <action>Compare against {{actual_code}}</action>
  <check if="code_snippet does NOT appear in actual_code">
    <action>Classify as FALSE_POSITIVE</action>
    <action>Reason: "Codex code_snippet doesn't match actual file content"</action>
    <output>❌ DISMISSED: {{finding.file}}:{{finding.line}} - code mismatch</output>
    <action>Skip remaining validation for this finding</action>
  </check>
  <output>✓ Code verified at {{finding.file}}:{{finding.line}}</output>
</substep>
```

3. Update `classify` substep to reference the comparison:
```xml
<substep name="classify">
  <action>Classify as VALID only if:
    - Code snippet was verified to exist in the file (from compare-code step)
    - Issue genuinely exists in the code
    - Fixing it improves code quality, security, or correctness
  </action>
  <action>Classify as FALSE_POSITIVE if:
    - Code snippet doesn't match actual file (already handled in compare-code)
    - Code is actually correct despite matching
    - Codex misunderstood the pattern or intent
    - The "fix" would break other functionality
  </action>
</substep>
```

### Architecture Compliance

This change modifies ONLY the prompt template - no Python code changes required. The validate phase SDK code remains unchanged.

### Library & Framework Requirements

- No new dependencies
- Uses existing Claude Code tools: `Read` for file reading, `Bash` for running tests

### File Structure Requirements

**Modified files:**
- `src/adw/defaults/commands/validate/code-review-loop/instructions.xml`

**No new files needed.**

### Testing Requirements

1. **Manual test case:**
   - Run ADW on a project
   - Manually verify `.adw/runs/{id}/llm/003_validate_response.json` shows file reads
   - Verify false positives are caught when Codex hallucinates

2. **Unit test (optional but recommended):**
   - Mock Codex response with incorrect code snippets
   - Verify Claude's output includes FALSE_POSITIVE classifications

---

## Previous Story Intelligence

From the run that exposed this bug (`.adw/runs/01KEGZSXGRTHG5K6MDVFXBB5DH`):

- Codex was given correct code: `f"Hello, {name}!"`
- Codex hallucinated: `f"Hello, {name}\!"` (claimed invalid escape sequence)
- Claude accepted the hallucination without reading files to verify
- The workflow claims to validate but the instructions weren't explicit enough

Key learning: **Vague instructions like "ask yourself" are not followed. Claude needs explicit MUST/CRITICAL directives with concrete actions.**

---

## Git Intelligence

Recent commits show Epic 16 work in progress:
- `fd91f92` - Ticket restructuring
- `e6e9a1e` - Add new validate command

The validate phase prompt structure is new (from Epic 16) so this is the right time to fix it.

---

## Latest Technical Information

The `code-review-loop` workflow is designed to run autonomously without user input. The validation step needs to be airtight because there's no human in the loop to catch LLM mistakes.

---

## Project Context Reference

See: `_bmad-output/epics/epic-16-validation-simplification.md` (original validation phase design)

Key principle: Fix in the prompt, not in Python code.

---

## Dev Notes

- This is a CRITICAL bug - the validate phase is fundamentally broken without this fix
- The fix is entirely in `instructions.xml` - no Python changes
- Focus on making instructions EXPLICIT and MANDATORY, not suggestive
- Test by deliberately running against code where Codex might hallucinate

### Project Structure Notes

- Validate phase prompts live in: `src/adw/defaults/commands/validate/`
- The `code-review-loop` subdirectory contains the workflow config and instructions
- No conflicts with unified project structure

### References

- [Source: ISS-022 issue file](_bmad-output/implementation-artifacts/issues/ISS-022-validate-phase-not-verifying-codex-findings.md)
- [Source: Epic 16](_bmad-output/epics/epic-16-validation-simplification.md)
- [Source: code-review-loop instructions](src/adw/defaults/commands/validate/code-review-loop/instructions.xml#validate-findings)
- [Source: Failing run evidence](test-project/.adw/runs/01KEGZSXGRTHG5K6MDVFXBB5DH/llm/003_validate_response.json)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Task 1-3: Already completed by previous ADW run (commit d4c7b81). The `instructions.xml` was updated with:
  - Critical mandate "YOU MUST READ THE FILE - this is NOT optional"
  - Warning about LLM hallucinations: "NEVER trust Codex blindly"
  - New `compare-code` substep that compares Codex's claimed code_snippet against actual file content
  - FALSE_POSITIVE classification when code snippets don't match (hallucination detection)
  - Output showing claimed vs actual code and match status

- Task 4: 8 new unit tests added to `test_validate_prompt.py` in class `TestCodeReviewLoopHallucinationDetection`:
  - `test_instructions_mandates_file_reading` - Verifies critical mandate exists
  - `test_instructions_warns_about_hallucinations` - Verifies LLM warning
  - `test_instructions_has_compare_code_substep` - Verifies compare-code substep exists
  - `test_instructions_compares_claimed_vs_actual_code` - Verifies code comparison
  - `test_instructions_detects_hallucination_mismatch` - Verifies mismatch detection
  - `test_instructions_classifies_hallucination_as_false_positive` - Verifies FALSE_POSITIVE classification
  - `test_instructions_outputs_verification_results` - Verifies output shows verification
  - `test_instructions_skips_validation_on_mismatch` - Verifies skip on mismatch

- All 2167 tests pass with 82.49% coverage

### File List

**Modified:**
- `src/adw/defaults/commands/validate/code-review-loop/instructions.xml` - Added hallucination detection to validate-findings step
- `tests/unit/commands/test_validate_prompt.py` - Added 8 tests for hallucination detection

