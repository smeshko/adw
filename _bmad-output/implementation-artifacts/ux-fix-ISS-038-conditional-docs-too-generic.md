# Story ISS-038: Make Conditional Docs Conditions Feature-Specific

Status: ready-for-dev
Linear Issue: not-configured
Epic: N/A - UX Fix (LLM Prompt Instructions)
Created: 2026-01-21

---

## Story

As a **developer using ADW workflows**,
I want **conditional docs conditions to be specific to the feature being documented**,
so that **CONDITIONAL_DOCS.md remains useful and doesn't trigger irrelevant documentation for unrelated work**.

## Acceptance Criteria

- [ ] **AC1:** Conditions generated for CONDITIONAL_DOCS.md must include the feature name or domain context
- [ ] **AC2:** Generic patterns like "When adding admin endpoints" are transformed to "When adding admin endpoints **for [feature name]**"
- [ ] **AC3:** The instructions.xml includes explicit good/bad examples to guide LLM behavior
- [ ] **AC4:** No other behavior changes - only the quality of generated conditions improves

## Tasks / Subtasks

- [ ] **Task 1:** Add explicit guidance against generic conditions in `instructions.xml`
  - Add IMPORTANT directive after the condition generation action
  - Include BAD/GOOD examples for common generic patterns
  - Emphasize including feature name in every condition

- [ ] **Task 2:** Test the change manually
  - Run a document phase with a test feature
  - Verify conditions are feature-specific

---

## Relevant Feature Documentation

**Matched from CONDITIONAL_DOCS.md:**
- docs/CONDITIONAL_DOCS.md itself (this is the target file affected by the generated conditions)

**Key Insight:** The current CONDITIONAL_DOCS.md shows the pattern we want - conditions are specific to their feature area. The problem is when LLM generates new conditions, it sometimes produces generic patterns.

---

## Developer Context

### Technical Requirements

**Nature of Change:** LLM prompt instruction enhancement

This is a **prompt engineering fix**, not a code fix. The change involves:
1. Adding explicit guidance text to an XML instruction file
2. No Python code changes
3. No Pydantic model changes
4. No test changes required (prompt quality is validated through manual runs)

**File Type:** XML (workflow instructions for LLM)

### Architecture Compliance

This change aligns with ADW's architecture:

1. **Defaults Command Structure:** The file being modified is in `src/adw/defaults/commands/document/document-feature/instructions.xml`
2. **XML Instruction Format:** Uses the established `<action>` tag format for LLM directives
3. **No SDK Changes:** This is purely a prompt/instruction change within the defaults folder

**Key Constraint:** The instructions.xml file is processed by the LLM as guidance text. Changes must be in natural language that LLMs can follow.

### Library & Framework Requirements

N/A - This is an XML text file containing LLM prompts, not executable code.

### File Structure Requirements

**File to Modify:**
```
src/adw/defaults/commands/document/document-feature/instructions.xml
```

**Location within file:** Lines 263-271 (the condition generation action)

**Current Implementation:**
```xml
<action>Generate suggested conditions for conditional docs guide:
  {{analysis.suggested_conditions}} = [
    "When working with [feature area]",
    "When implementing [related functionality]",
    "When modifying [affected components]",
    "When troubleshooting [specific issues]"
  ]
  Generate 3-5 specific, actionable conditions based on the actual changes.
</action>
```

**Target Implementation:**
```xml
<action>Generate suggested conditions for conditional docs guide:
  {{analysis.suggested_conditions}} = [
    "When working with [feature area]",
    "When implementing [related functionality]",
    "When modifying [affected components]",
    "When troubleshooting [specific issues]"
  ]
  Generate 3-5 specific, actionable conditions based on the actual changes.

  IMPORTANT: Conditions must be SPECIFIC to this feature, not generic patterns.
  - BAD: "When implementing caching strategies" (too generic)
  - GOOD: "When implementing caching for remote config endpoints"
  - BAD: "When adding admin endpoints" (too generic)
  - GOOD: "When adding admin endpoints for the remote config module"
  - BAD: "When creating public API endpoints" (too generic)
  - GOOD: "When creating public endpoints for app configuration"

  Always include the feature name or domain in the condition.
</action>
```

### Testing Requirements

**No automated tests required** - This is an LLM prompt change that affects generated content quality.

**Manual Verification:**
1. Run ADW with a feature that introduces common patterns
2. Complete through document phase
3. Check generated conditions in `docs/CONDITIONAL_DOCS.md`
4. Verify conditions include feature-specific context

---

## Previous Story Intelligence

N/A - This is a standalone UX fix issue, not part of an epic sequence.

---

## Git Intelligence

**Recent Commits (for context):**
- `fix(ISS-031): Move PR creation to after document phase` - Shows document phase is actively maintained
- `fix(ISS-030): Honor project config.yaml without prompt.md` - Configuration-related fix pattern

**Commit Pattern for This Fix:**
```
fix(ISS-038): Make conditional docs conditions feature-specific

Add explicit guidance in document-feature instructions.xml to ensure
generated conditions include the feature name/domain, preventing
generic conditions that pollute CONDITIONAL_DOCS.md.

- Add IMPORTANT directive with BAD/GOOD examples
- Emphasize feature name inclusion in every condition
```

---

## Latest Technical Information

N/A - No external library or API changes relevant to this prompt text fix.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

**Relevant Rule:** None directly applicable - this is an XML prompt file, not Python code.

**Indirect Relevance:** The fix follows the established pattern of using explicit examples and directives in instruction files to guide LLM behavior.

---

## Dev Notes

### Key Implementation Details

1. **Single File Change:** Only `src/adw/defaults/commands/document/document-feature/instructions.xml` needs modification

2. **Exact Location:** Lines 263-271, specifically after the "Generate 3-5 specific, actionable conditions" text

3. **Pattern to Follow:** Use BAD/GOOD contrasting examples - this is an effective LLM prompting technique

4. **Preserve Structure:** Keep the existing template structure, only add the IMPORTANT block after the existing text

### Project Structure Notes

- The `defaults/commands/` folder contains LLM instruction templates
- Each command has a `instructions.xml` file that guides LLM behavior
- Changes here affect ALL projects using ADW defaults (no per-project config)

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-038-conditional-docs-too-generic.md] - Original issue report with proposed fix
- [Source: src/adw/defaults/commands/document/document-feature/instructions.xml:263-271] - Current implementation
- [Source: docs/CONDITIONAL_DOCS.md] - Example of desired condition specificity

---

## Dev Agent Record

### Context Reference

Story created from ISS-038 issue report.

### Agent Model Used

<!-- To be filled by dev agent -->

### Debug Log References

<!-- To be filled by dev agent -->

### Completion Notes List

<!-- To be filled by dev agent -->

### File List

| File | Action | Notes |
|------|--------|-------|
| `src/adw/defaults/commands/document/document-feature/instructions.xml` | EDIT | Add IMPORTANT block with BAD/GOOD examples at lines 269-271 |
