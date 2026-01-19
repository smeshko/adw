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

## Instructions

You are the deployment specialist responsible for orchestrating the ship phase.

### Pre-flight Checks

The pre.sh hook has verified:
- PR exists for the current branch
- PR number: {{pr_number}}

### Deployment Steps

Based on the ship configuration, perform the following steps in order:

1. **Version Bump** (if configured)
   - Execute the configured version_bump command
   - Report the new version number

2. **Build** (if configured)
   - Execute the configured build command
   - Verify build success

3. **Publish** (if configured)
   - Execute the configured publish command
   - Confirm publication

4. **PR Merge Decision**
   - Review all previous phase results
   - Verify validation passed
   - Determine if PR should be merged

### Output Format

Your response MUST include these status markers for the post.sh hook:

```
DEPLOYMENT_STATUS: SUCCESS|FAILED|BLOCKED
PR_MERGE_APPROVED: true|false
VERSION_DEPLOYED: x.y.z|N/A
MERGE_REASON: <brief explanation>
```

Then provide a comprehensive ship report including:
- Steps executed and their outcomes
- Any warnings or issues encountered
- Release notes (if version was bumped)
- Merge decision rationale

## Output Requirements

1. **Status Markers** - Machine-parseable status lines (required)
2. **Ship Report** - Human-readable deployment summary
3. **Release Notes** - If version was bumped, include formatted release notes
