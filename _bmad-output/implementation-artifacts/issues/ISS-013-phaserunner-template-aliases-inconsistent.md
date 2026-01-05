# Issue: PhaseRunner Template Aliases Inconsistent and Hardcoded

**ID:** ISS-013
**Severity:** Minor
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** N/A
- **Story:** N/A
- **Component:** PhaseRunner

## Description

Template aliases are hardcoded with inconsistent naming, providing shortcuts like `{{plan}}` instead of explicit paths like `{{artifacts.plan.plan_output}}`. The naming is inconsistent across phases and creates ambiguity.

## Reproduction Steps

1. Open `src/adw/core/phase_runner.py`
2. Navigate to lines 331-339
3. Observe inconsistent alias mappings

## Expected Behavior

Either:
- Consistent alias naming across all phases, OR
- No aliases at all - use explicit paths for clarity

## Actual Behavior

Inconsistent alias mappings:

| Alias | Maps To | Issue |
|-------|---------|-------|
| `{{plan}}` | `artifacts.plan.plan_output` | Identity mapping - redundant |
| `{{implementation}}` | `artifacts.build.build_output` | Semantic rename - inconsistent |
| `{{output}}` | `artifacts.verify.verify_output` | Generic name - ambiguous |

Problems:
- `plan` stays `plan`, `build` becomes `implementation`, `verify` becomes `output`
- No aliases for `document` or `validate` phases
- Adding new aliases requires modifying PhaseRunner
- `{{output}}` could mean any phase's output

## Impact

- Inconsistent developer experience
- Confusing for prompt authors
- Maintenance burden when adding new phases
- Ambiguous template variables

## User Impact Score

- **Users Affected:** Developers writing custom prompts
- **Frequency:** Every prompt authoring session

## Workaround

Use explicit paths like `{{artifacts.plan.plan_output}}` instead of aliases.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** refactor-ISS-013-remove-template-aliases.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

**Proposed Fix:** Remove aliases entirely - use explicit paths for clarity.

**Changes Required:**

1. Delete alias block in `phase_runner.py:331-339`
2. Update default prompts:

| File | Change |
|------|--------|
| `commands/build/prompt.md` | `{{plan}}` -> `{{artifacts.plan.plan_output}}` |
| `commands/verify/prompt.md` | `{{implementation}}` -> `{{artifacts.build.build_output}}` |
| `commands/document/prompt.md` | `{{implementation}}` -> `{{artifacts.build.build_output}}` |
| `commands/validate/prompt.md` | `{{output}}` -> `{{artifacts.verify.verify_output}}` |

3. Update tests: Search for alias usage in template assertions

**Effort:** Low (~15 lines across 4 files)

**Source:** `docs/development/tech-debt/phase-runner-aliases.md`
