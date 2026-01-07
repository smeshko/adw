# Issue: Template Logic Scattered Between Modules

**ID:** ISS-017
**Severity:** Minor
**Type:** Tech Debt
**Status:** reported
**Reported:** 2026-01-06
**Reporter:** Ivo

## Related

- **Epic:** N/A
- **Story:** N/A
- **Component:** Template Engine / Phase Runner

## Description

Template handling responsibilities are split between `template.py` (generic template engine) and `phase_runner.py` (ADW orchestration) with some overlap and awkward patterns that create tech debt.

While the overall separation is defensible (template.py handles generic templating, phase_runner.py handles ADW-specific context building), there are three specific issues:

1. **Duplicated Pattern Matching** - `phase_runner.py:55` defines its own artifact regex that duplicates pattern-matching logic that could be delegated to the template engine
2. **Validation Logic in Wrong Place** - `_validate_artifact_references()` (lines 591-663) validates template syntax but lives in PhaseRunner instead of TemplateEngine
3. **Awkward State Mutation** - Lines 391-392 mutate template engine state before each render instead of passing parameters

## Reproduction Steps

1. Review `src/adw/commands/template.py` - generic template engine
2. Review `src/adw/core/phase_runner.py` - has ADW-specific templating concerns
3. Note the `ARTIFACT_REF_PATTERN` duplicates template pattern concepts
4. Note `_validate_artifact_references()` does template validation outside template.py
5. Note state mutation of `command_root`/`shared_root` before each render

## Expected Behavior

Template-related logic should be consolidated in the template module with clear extension points for domain-specific validation.

## Actual Behavior

Three areas of tech debt exist:
- `ARTIFACT_REF_PATTERN` in phase_runner.py duplicates template pattern logic
- `_validate_artifact_references()` method in PhaseRunner validates templates
- State mutation pattern for `command_root`/`shared_root` on TemplateEngine

## Impact

- **Maintainability:** Template logic changes require updates in multiple places
- **Testability:** Validation logic harder to test in isolation
- **Code smell:** State mutation before method calls is fragile pattern

This is minor tech debt - the current structure works and doesn't cause bugs.

## User Impact Score

- **Users Affected:** Developers only (internal)
- **Frequency:** During maintenance/refactoring

## Workaround

None needed - code works correctly, this is a maintainability concern.

## Environment

- **OS:** macOS
- **App Version:** Current
- **DPI Scaling:** N/A

## Evidence

### Code References

**Duplicated pattern (phase_runner.py:55):**
```python
ARTIFACT_REF_PATTERN = re.compile(r"\{\{artifacts\.([a-z_][a-z0-9_.]*(?:\.\*)?)}\}")
```

**State mutation before render (phase_runner.py:391-392):**
```python
self.template_engine.command_root = command.path
self.template_engine.shared_root = command.path.parent
```

**Validation in wrong module (phase_runner.py:591-663):**
```python
def _validate_artifact_references(
    self,
    template: str,
    artifacts_map: dict[str, dict[str, str]],
) -> None:
    """Validate that all artifact references in template exist..."""
```

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** N/A - Minor issue for backlog
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Recommended Refactoring

Priority order if addressing:

1. **Move ARTIFACT_REF_PATTERN usage into TemplateEngine** (or a subclass/extension point)
2. **Pass command_root/shared_root to render()** instead of mutating instance state
3. **Consider ArtifactTemplateValidator** class or pre-render validation hook in TemplateEngine

## Notes

Verdict from analysis: "Minor tech debt, not urgent. The current structure works and the separation is defensible."
