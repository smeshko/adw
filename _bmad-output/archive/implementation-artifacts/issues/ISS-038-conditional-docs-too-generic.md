# Issue: Document Phase Generates Overly Generic Conditional Docs Conditions

**ID:** ISS-038
**Severity:** Minor
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** N/A (LLM prompt instructions)
- **Story:** N/A
- **Component:** Document Phase Instructions (document-feature/instructions.xml)

## Description

The document phase LLM generates conditions for the CONDITIONAL_DOCS.md that are too generic and not specific to the actual feature implemented. For example, a remote config feature got these conditions:

```markdown
- docs/features/remote-config.md
  - Conditions:
    - When adding feature flags to control mobile app behavior     ✓ Specific
    - When implementing server-driven configuration                ✓ Specific
    - When working with the AnyCodable type for heterogeneous JSON ✓ Specific
    - When adding new admin endpoints with authentication          ✗ Too generic
    - When implementing caching strategies for API responses       ✗ Too generic
    - When creating public (unauthenticated) API endpoints         ✗ Too generic
```

The last 3 conditions are not specific to remote config - they're general patterns that could apply to many features.

**Location:** `src/adw/defaults/commands/document/document-feature/instructions.xml:268-271`

## Reproduction Steps

1. Run ADW with a new feature that introduces common patterns
2. Complete through document phase
3. Check `docs/CONDITIONAL_DOCS.md`
4. Observe some conditions are overly broad

**Evidence from project-rulebook-be run:**
- Feature: Remote Config Module
- Generated conditions include generic patterns like "When adding new admin endpoints"
- These conditions would trigger the doc for unrelated admin endpoint work

## Expected Behavior

Conditions should be specific to the feature:
- "When adding feature flags to the remote config system"
- "When implementing server-driven mobile app configuration"
- "When adding admin endpoints **for remote config**"

## Actual Behavior

Conditions are generic patterns that could apply to many features:
- "When adding new admin endpoints with authentication"
- "When implementing caching strategies for API responses"

## Impact

- **Doc pollution**: CONDITIONAL_DOCS becomes less useful
- **False positives**: Unrelated work triggers irrelevant doc suggestions
- **Maintenance burden**: Generic conditions accumulate over time

## Workaround

Manually edit CONDITIONAL_DOCS.md to make conditions more specific.

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### Generated output from document phase
```markdown
**Suggested Conditions:**
- When adding feature flags to control mobile app behavior
- When implementing server-driven configuration
- When working with the AnyCodable type for heterogeneous JSON
- When adding new admin endpoints with authentication          ← Generic!
- When implementing caching strategies for API responses       ← Generic!
- When creating public (unauthenticated) API endpoints         ← Generic!
```

### Current instructions (instructions.xml:268-271)
```xml
<action>Generate suggested conditions for conditional docs guide:
  {{analysis.suggested_conditions}} = [...]
  Generate 3-5 specific, actionable conditions based on the actual changes.
</action>
```

## Proposed Fix

### Add explicit guidance against generic conditions
**File:** `src/adw/defaults/commands/document/document-feature/instructions.xml`
```xml
<action>Generate suggested conditions for conditional docs guide:
  {{analysis.suggested_conditions}} = [...]
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

## Files Affected

| File | Change |
|------|--------|
| `src/adw/defaults/commands/document/document-feature/instructions.xml` | Add explicit guidance against generic conditions |

## Resolution

- **Fix Story:** N/A - Minor issue for backlog
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This is an LLM behavior issue that can be improved through better prompting. The fix is straightforward - add explicit examples of good vs bad conditions to the instructions.
