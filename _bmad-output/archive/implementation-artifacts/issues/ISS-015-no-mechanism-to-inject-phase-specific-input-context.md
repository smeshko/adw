# Issue: No mechanism to inject phase-specific input context

**ID:** ISS-015
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-06
**Reporter:** Ivo

## Related

- **Epic:** Epic 12 (Task Manager Integration / Tech Debt)
- **Story:** N/A
- **Component:** Phase Configuration / PhaseRunner

## Description

Phases cannot receive optional input context (e.g., paths to PRD, architecture files). Users wanting to inject external documentation into specific phases (like the plan phase) have no declarative way to do so. The only workaround is using `pre_hook` to cat files into output.

Currently, `PhaseConfig` only supports:
- `enabled: bool`
- `timeout_seconds: int | None`
- `pre_hook: str | None`
- `post_hook: str | None`

There is no `input_files` or similar field to declaratively specify phase-specific input documents.

## Reproduction Steps

1. Open `adw.yaml` configuration file
2. Attempt to configure the `plan` phase with input files (PRD, architecture docs)
3. Observe that no such configuration option exists
4. Check `PhaseConfig` model in `src/adw/models/config.py:102-122`
5. Confirm only `enabled`, `timeout_seconds`, `pre_hook`, `post_hook` are available

## Expected Behavior

PhaseConfig should support an optional `input_files` field that maps names to file paths, making them available in phase templates:

```yaml
phases:
  plan:
    input_files:
      prd: "docs/product/prd.md"
      architecture: "docs/architecture/architecture.md"
```

These files would then be loaded by PhaseRunner and made available as template variables.

## Actual Behavior

PhaseConfig only supports `enabled`, `timeout_seconds`, `pre_hook`, and `post_hook` - no input file injection capability exists.

## Impact

Users cannot easily provide phase-specific context documents, reducing flexibility for customizing phase behavior based on project documentation. This is particularly limiting for the `plan` phase where PRD and architecture context would significantly improve planning quality.

## User Impact Score

- **Users Affected:** All users wanting phase-specific context
- **Frequency:** Every run where external documentation is relevant

## Workaround

Use `pre_hook` to output file contents:
```yaml
phases:
  plan:
    pre_hook: "cat docs/product/prd.md docs/architecture/architecture.md"
```

Then reference `pre_hook_output` in templates. This is not ideal because:
- Mixes file content together without structure
- No named access to individual files
- Pre-hook output is a single string, not a map

## Environment

- **OS:** macOS
- **App Version:** adw-sdk (development)
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-015-phase-specific-input-context.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Proposed implementation approach:

1. Extend `PhaseConfig` in `src/adw/models/config.py`:
   ```python
   class PhaseConfig(BaseModel):
       enabled: bool = True
       timeout_seconds: int | None = None
       pre_hook: str | None = None
       post_hook: str | None = None
       input_files: dict[str, str] | None = None  # NEW: {name: path}
   ```

2. Update `PhaseRunner._build_artifacts_map()` in `src/adw/core/phase_runner.py` to:
   - Load files specified in `input_files`
   - Add them to template variables under a dedicated key (e.g., `inputs`)

3. Update prompt templates to reference `{{ inputs.prd }}`, `{{ inputs.architecture }}`, etc.
