# Issue: PR Title Missing Description When Feature Description Equals Task ID

**ID:** ISS-037
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** Epic 9 (Git Integration & Documentation)
- **Story:** 9-4-generate-pr-description
- **Component:** PR Creation (pr.py)

## Description

When a user runs ADW with just a task ID (e.g., `adw run "RULE-151"`), the PR title is created as just "RULE-151" without any meaningful description. This happens because `feature_description` is set to the task ID, and the PR title format `{task_id}: {feature_description}` becomes "RULE-151: RULE-151" which gets truncated to just "RULE-151".

**Location:** `src/adw/cli/pr.py:413-419`

## Reproduction Steps

1. Run ADW with just a task ID:
   ```bash
   adw run "RULE-151"
   ```
2. Complete through document phase
3. Observe PR is created with title "RULE-151" only
4. No meaningful description of what the PR does

**Evidence from project-rulebook-be run:**
- context.json shows: `"feature_description": "RULE-151"`
- PR #35 title: "RULE-151" (no description)
- Linear task RULE-151 has title "Add remote configuration module"

## Expected Behavior

When `feature_description` equals `task_id`:
1. Fetch the task title from Linear (`task_info.title`)
2. Use that as the PR title: "RULE-151: Add remote configuration module"
3. Fallback gracefully if task_info is unavailable

## Actual Behavior

1. PR title is just the task ID
2. No attempt to use the Linear task title
3. Users must manually edit PR title

## Impact

- **Poor PR quality**: PRs have meaningless titles
- **Extra work**: Users must manually fix PR titles
- **Lost context**: Linear task has the description but it's not used

## Workaround

Provide a full feature description when running:
```bash
adw run "RULE-151: Add remote configuration module"
```

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### Code Analysis

**pr.py:411-419** - Current title generation:
```python
# Generate PR title from feature description (Story 12.6: PR-Task Linking)
# If task_id is present, prefix with task ID
pr_title = context.feature_description  # ← Just "RULE-151"
if context.task_id:
    # Format: "TASK-123: description"
    pr_title = f"{context.task_id}: {context.feature_description}"  # ← "RULE-151: RULE-151"

if len(pr_title) > 72:
    pr_title = pr_title[:69] + "..."  # ← Truncated to just "RULE-151"
```

### context.json from run
```json
{
  "feature_description": "RULE-151",
  "task_id": "RULE-151",
  "task_info": {
    "title": "Add remote configuration module",
    ...
  }
}
```

## Proposed Fix

### 1. Check if feature_description equals task_id and use task_info.title
**File:** `src/adw/cli/pr.py`
```python
# Generate PR title
pr_title = context.feature_description

# If feature_description is just the task ID, try to use the task title instead
if context.task_id and context.feature_description == context.task_id:
    if context.task_info and context.task_info.title:
        pr_title = f"{context.task_id}: {context.task_info.title}"
    else:
        pr_title = context.task_id  # Fallback to just the ID
elif context.task_id:
    # Normal case: prefix with task ID
    pr_title = f"{context.task_id}: {context.feature_description}"

if len(pr_title) > 72:
    pr_title = pr_title[:69] + "..."
```

### 2. Optional: Warn user at run start
**File:** `src/adw/cli/app.py` or `bootstrap.py`
```python
# When starting a run
if feature_description == task_id:
    logger.info(
        "Using task title from Linear as PR description",
        extra={"task_id": task_id, "title": task_info.title if task_info else "N/A"}
    )
```

## Files Affected

| File | Change |
|------|--------|
| `src/adw/cli/pr.py` | Add logic to use task_info.title when needed |
| `src/adw/cli/app.py` | Optional: Add warning when no description provided |

## Resolution

- **Fix Story:** [ux-fix-ISS-037-pr-title-missing-description.md](../ux-fix-ISS-037-pr-title-missing-description.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

The task_info is already fetched and available in context. This is purely a matter of using existing data when the feature_description is insufficient.
