# Issue: Template variables not populated for pre-hook exports and build artifacts

**ID:** ISS-040
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-22
**Reporter:** Ivo

## Related

- **Epic:** 15 (Ship Phase)
- **Story:** N/A
- **Component:** Template Engine / Phase Runner

## Description

Two categories of template variables show warnings during full 5-phase pipeline runs:

### Problem 1: PR Variables in Ship Phase
The ship phase template (`src/adw/defaults/commands/ship/prompt.md:33-36`) references:
- `{{pr_number}}`
- `{{pr_url}}`
- `{{pr_state}}`
- `{{pr_mergeable}}`

However, the template variable system only provides `{{pre_hook_output}}` (raw stdout text). There is **no parsing code** to extract these individual values from the pre-hook output and make them available as template variables.

The pre.sh hook outputs these values to stdout and exports them as environment variables (`ADW_PR_NUMBER`, etc.), but:
1. Subprocess env vars don't persist to the parent Python process
2. The stdout text is passed as-is to `{{pre_hook_output}}`, not parsed into individual variables

### Problem 2: Build Artifacts in Document Phase
The document phase template (`src/adw/defaults/commands/document/prompt.md:16-19`) references:
- `{{artifacts.build.diff_stats}}`
- `{{artifacts.build.diff}}`

These should come from `BuildExtension.extra_artifacts()` which produces `diff.txt` and `diff_stats.json`. The artifacts may not be created if:
- No git changes were made during build phase
- No commits were created during build phase

The current behavior is to return empty list when no changes exist, but the template still references these variables expecting content.

## Reproduction Steps

1. Start a full ADW run: `adw run "implement feature X"`
2. Let it execute all 5 phases (plan → build → validate → document → ship)
3. Observe warnings at ~15:48:26 (document phase):
   ```
   [WARN] [phase] Unknown template variable left as-is: {{artifacts.build.diff_stats}}
   [WARN] [phase] Unknown template variable left as-is: {{artifacts.build.diff}}
   ```
4. Observe warnings at ~15:50:41 (ship phase):
   ```
   [WARN] [phase] Unknown template variable left as-is: {{pr_number}}
   [WARN] [phase] Unknown template variable left as-is: {{pr_url}}
   [WARN] [phase] Unknown template variable left as-is: {{pr_state}}
   [WARN] [phase] Unknown template variable left as-is: {{pr_mergeable}}
   ```

## Expected Behavior

1. **PR variables**: Should be populated by parsing the pre-hook stdout or by reading the RunContext (which has `pr_url` from DocumentExtension)
2. **Build artifacts**: Should either be populated or the template should gracefully handle missing artifacts

## Actual Behavior

1. **PR variables**: Template receives literal `{{pr_number}}` etc. in prompts sent to LLM, reducing prompt quality
2. **Build artifacts**: Template receives literal `{{artifacts.build.diff}}` etc., causing LLM to see placeholder text instead of actual diff content

## Impact

- **Ship phase**: LLM receives unresolved placeholders like `{{pr_number}}` instead of actual PR number, reducing context quality
- **Document phase**: LLM cannot see the actual diff content, affecting PR description quality
- Warnings clutter log output during normal operation

## User Impact Score

- **Users Affected:** All users running full pipeline
- **Frequency:** Every full run

## Workaround

**For PR variables**: The LLM can still work as the pre-hook stdout contains the PR information in text format via `{{pre_hook_output}}`.

**For build artifacts**: None. If diff artifacts aren't created, the document phase LLM doesn't see the changes.

## Environment

- **OS:** macOS
- **App Version:** 0.1.36
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

```
15:48:26 [WARN] [phase] Unknown template variable left as-is: {{artifacts.build.diff_stats}}
15:48:26 [WARN] [phase] Unknown template variable left as-is: {{artifacts.build.diff}}
15:50:41 [WARN] [phase] Unknown template variable left as-is: {{pr_number}}
15:50:41 [WARN] [phase] Unknown template variable left as-is: {{pr_url}}
15:50:41 [WARN] [phase] Unknown template variable left as-is: {{pr_state}}
15:50:41 [WARN] [phase] Unknown template variable left as-is: {{pr_mergeable}}
```

### Screen Recording

N/A

## Technical Analysis

### PR Variables Issue
**Location:** `src/adw/core/phase_runner.py:364-383`

The template variables dict provides:
```python
variables = {
    "pre_hook_output": pre_hook_output,  # Raw stdout text
    # ... other variables
}
```

But templates expect:
```markdown
- PR number: {{pr_number}}
- PR URL: {{pr_url}}
```

**Fix options:**
1. Parse pre-hook stdout for key-value pairs and add to variables dict
2. Change template to use `{{pre_hook_output}}` and let LLM extract values
3. Add PR fields to RunContext (DocumentExtension already sets `pr_url`) and expose via template

### Build Artifacts Issue
**Location:** `src/adw/core/extensions/build.py:118-124`

```python
if not diff_content.strip():
    logger.debug("No git changes to capture")
    return artifacts  # Empty list
```

**Fix options:**
1. Create placeholder artifacts even when no changes exist
2. Make document template resilient to missing artifacts (conditional rendering)
3. Log more clearly when artifacts aren't created so users understand why

## Resolution

- **Fix Story:** ux-fix-ISS-040-template-variables-not-populated.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This is a design gap between what templates expect and what the template variable system provides. The ship phase pre.sh was designed to export env vars, but env vars from subprocesses don't persist. The templates were written assuming individual variables would exist.
