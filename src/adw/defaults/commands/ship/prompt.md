# Ship Phase

Execute deployment steps including optional version bump, build, publish, and PR merge automation.

## Context

Run Context: {{context}}
Feature: {{feature_description}}

## Previous Phase Artifacts

**PR Description:**
{{artifacts.document.pr_description}}

**Build Output:**
{{artifacts.build.build_output}}

**Validation Evidence:**
{{artifacts.validate.*}}

## Ship Configuration

{{ship_config}}

## Additional Inputs

{{inputs.*}}

## Pre-Hook Context

The pre.sh hook has verified:
- PR exists for the current branch
- PR number: {{pr_number}}
- PR URL: {{pr_url}}
- PR State: {{pr_state}}
- PR Mergeable: {{pr_mergeable}}

## Instructions

{{include:instructions.xml}}

## Output Requirements

Your response MUST include these status markers for the post.sh hook:

```
DEPLOYMENT_STATUS: SUCCESS|FAILED|BLOCKED
PR_MERGE_APPROVED: true|false
VERSION_DEPLOYED: x.y.z|N/A
MERGE_REASON: <brief explanation>
```

Then provide a comprehensive ship report including:
1. **Status Markers** - Machine-parseable status lines (required)
2. **Ship Report** - Human-readable deployment summary
3. **Release Notes** - If version was bumped, include formatted release notes
