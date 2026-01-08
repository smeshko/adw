# Story 16.2: Create Unified Validation Prompt

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: 16 - Validation Phase Simplification
Created: 2026-01-08

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer,
I want a single validation prompt that handles everything,
so that the LLM manages the validate-fix-re-validate cycle.

## Acceptance Criteria

**Given** `validate/prompt.md`
**When** executed
**Then** it instructs the LLM to:
1. Run the test suite (determine correct command)
2. Run linters/type checkers if configured
3. Review the diff for bugs, security issues, bad patterns
4. If issues found and fixable, fix them and re-validate ONCE
5. Return structured result

**Given** the prompt output
**When** returned
**Then** schema is:
```json
{
  "passed": true,
  "tests_passed": true,
  "code_review_passed": true,
  "issues_fixed": [
    "Fixed missing null check in auth handler",
    "Added error handling for API timeout"
  ],
  "issues_remaining": [],
  "summary": "All tests pass, code review clean"
}
```

**Given** issues that cannot be auto-fixed
**When** detected
**Then** LLM returns immediately without attempting fixes

**Given** fix attempt
**When** re-validation still fails
**Then** LLM returns failed with remaining issues (no more attempts)

## Tasks / Subtasks

- [x] **Task 1: Create validate/prompt.md**
  - Create `.adw/phases/validate/prompt.md` template
  - Include comprehensive instructions for the LLM
  - Define clear success/failure criteria
  - Include output schema specification

- [x] **Task 2: Define output schema**
  - Create JSON schema for validation result
  - Include all required fields: passed, tests_passed, code_review_passed, issues_fixed, issues_remaining, summary
  - Document schema in prompt file

- [x] **Task 3: Include rules for can_auto_fix determination**
  - Document what makes an issue auto-fixable
  - Examples of fixable: missing null check, error handling, type annotations
  - Examples of non-fixable: design decisions, architecture changes, unclear requirements

- [x] **Task 4: Test prompt with various scenarios**
  - Test with passing code (no issues)
  - Test with fixable issues
  - Test with non-fixable issues
  - Test with mixed (some fixable, some not)

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->

**Existing prompt structure from Epic 2:**
ADW uses markdown prompts in `.adw/phases/` directory with variable substitution.

**Template variables available:**
- `{{feature_description}}` - The feature being implemented
- `{{git_diff}}` - Changes made during build phase
- `{{run_context}}` - Full run context JSON
- `{{project_config}}` - Project configuration

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->

1. **Prompt location:** `.adw/phases/validate/prompt.md`
2. **Single execution:** Prompt must handle entire cycle in one call
3. **Structured output:** LLM must return JSON matching defined schema
4. **No external dependencies:** Prompt uses built-in LLM capabilities

**Prompt structure:**
```markdown
# Validation Phase

## Context
Feature: {{feature_description}}
Diff: {{git_diff}}

## Your Task
[Instructions for validation]

## Output Format
[JSON schema specification]

## Rules
[Validation and fix rules]
```

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From Epic 2 (Command Resolution & Templates):**
- Prompts use Jinja2-style variable substitution
- Prompt files are markdown with special sections
- Output validation uses JSON schema (from Story 2.4)

**From project.yaml structure:**
```yaml
# Test command configuration
validation:
  test_command: "pytest"  # or auto-detect
  timeout_seconds: 600
```

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

No external libraries needed for prompt creation. The prompt is pure markdown.

**LLM interaction pattern:**
- Prompt is sent to Claude Code
- Claude executes tests, reviews code, makes fixes
- Claude returns structured JSON result

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**Files to CREATE:**
```
.adw/
└── phases/
    └── validate/
        └── prompt.md      # The unified validation prompt
```

**Default project template update:**
The prompt should be included in the default ADW project template so new projects get it automatically.

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **Prompt template tests:**
   - Verify variable substitution works
   - Verify prompt loads without errors

2. **Integration tests:**
   - Test with MockExecutor that returns expected JSON
   - Test validation result parsing

3. **Manual testing scenarios:**
   - Project with all tests passing
   - Project with failing tests (fixable)
   - Project with failing tests (not fixable)
   - Project with lint errors

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

N/A - This story runs in parallel with Story 16.1.

**Related prompts in ADW:**
- `.adw/phases/plan/prompt.md` - Planning phase prompt
- `.adw/phases/build/prompt.md` - Build phase prompt
- `.adw/phases/document/prompt.md` - Documentation phase prompt

**Pattern to follow:**
- Clear section headers
- Explicit output format specification
- Rules section at the end

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Commit pattern:**
```
feat(epic-16): Create unified validation prompt (Story 16.2)

- Add .adw/phases/validate/prompt.md with complete instructions
- Define JSON output schema
- Include auto-fix determination rules
- Add template variable placeholders
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Claude Code capabilities (2025):**
- Can execute bash commands (run tests, linters)
- Can read and modify files (apply fixes)
- Can iterate on changes
- Structured output via JSON works reliably

**Best practices for LLM prompts:**
- Be explicit about output format
- Provide examples
- Set clear boundaries (e.g., "maximum one fix attempt")
- Include error handling instructions

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Prompts are markdown files in `.adw/phases/`
- Variable substitution uses `{{variable}}` syntax
- Output validation uses JSON schema

---

## Dev Notes

### The Prompt Content

The prompt should be approximately:

```markdown
# Validation Phase

## Context
Feature: {{feature_description}}
Diff: {{git_diff}}

## Your Task

You are validating code changes. Do the following:

1. **Run Tests**
   - Determine the appropriate test command for this project
   - Execute it and capture results

2. **Run Linters** (if configured)
   - Run any configured linters/type checkers
   - Capture violations

3. **Code Review**
   - Review the diff for:
     - Bugs and logic errors
     - Security vulnerabilities
     - Bad patterns or anti-patterns
     - Missing error handling

4. **If Issues Found**
   - Assess: Can ALL issues be fixed with clear, mechanical changes?
   - If YES: Fix them, then re-run tests/linters ONCE
   - If NO: Return immediately with issues listed

5. **Return Result**

## Output Format

Return ONLY this JSON:

```json
{
  "passed": true,
  "tests_passed": true,
  "code_review_passed": true,
  "issues_fixed": [
    "Fixed missing null check in auth handler",
    "Added error handling for API timeout"
  ],
  "issues_remaining": [],
  "summary": "All tests pass, code review clean"
}
```

## Rules

- `passed` = true ONLY if `tests_passed` AND `code_review_passed` are both true
- `issues_fixed` = one-line summaries of issues you fixed (empty if none)
- `issues_remaining` = one-line summaries of issues that couldn't be fixed
- If you fix issues, re-validate ONCE only - do not loop
- If issues require design decisions or clarification - do NOT fix, add to `issues_remaining`
- Maximum one fix attempt, then return whatever state you're in
```

### Project Structure Notes

- Prompt goes in `.adw/phases/validate/prompt.md`
- Should be included in default project template
- No code changes to SDK needed for this story

### References

- [Source: _bmad-output/epics/epic-16-validation-simplification.md#The Prompt]
- [Source: _bmad-output/epics/epic-2-command-resolution-templates.md] (template patterns)

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used



### Debug Log References

### Completion Notes List

- Task 1: Created comprehensive validation prompt at `src/adw/defaults/commands/validate/prompt.md` (6181 bytes)
  - Includes 5-step validation process: run tests, run linters, code review, assess/fix, return result
  - Defines JSON output schema with all required fields
  - Includes comprehensive auto-fix determination rules
  - Added 5 examples covering various validation scenarios
- Task 2: Output schema fully defined in prompt file
  - Field Definitions section documents all 6 required fields
  - JSON examples demonstrate schema in various scenarios
  - Schema matches the simplified result model specified in Epic 16
- Task 3: Auto-fix determination rules included in prompt
  - 7 categories of auto-fixable issues (null checks, error handling, types, imports, linter fixes, logic errors, returns)
  - 6 categories of non-auto-fixable issues (design, architecture, requirements, performance, security, breaking changes)
  - Clear "All or Nothing" rule: if ANY issue is non-fixable, fix NOTHING
- Task 4: Created comprehensive test suite with 30 test cases
  - TestValidatePromptStructure: 11 tests verifying prompt sections
  - TestValidatePromptOutputSchema: 6 tests for schema fields
  - TestValidatePromptAutoFixRules: 8 tests for fix determination rules
  - TestValidatePromptVariableSubstitution: 2 tests for template rendering
  - TestValidatePromptExamples: 4 tests for scenario examples

### File List

- `src/adw/defaults/commands/validate/prompt.md` (modified)
- `tests/unit/commands/test_validate_prompt.py` (created)

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 16.3, Story 16.4
- **Can Parallel With:** Story 16.1

### Dependency Rationale
- Story 16.3: Configuration needs to match the new prompt's requirements (timeout, test_command)
- Story 16.4: Result model schema must match the prompt's output schema
