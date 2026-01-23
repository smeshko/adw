---
name: 'step-02-execute'
description: 'Execute deployment commands in sequence with fail-fast behavior'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/ship'

# File References
thisStepFile: '{workflow_path}/steps/step-02-execute.md'
nextStepFile: '{workflow_path}/steps/step-03-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 2: Execute Deployment

## STEP GOAL:

To execute all configured deployment commands in sequence (version bump, build, publish, post-publish), capturing results and stopping immediately on any failure.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step upon completion
- ⛔ FAIL FAST: Stop immediately on any command failure
- 📊 TRACK STATE: Capture all results for final reporting

### Role Reinforcement:

- ✅ You are a release manager executing deployment autonomously
- ✅ Work autonomously without waiting for user input
- ✅ Log progress to stdout for CI visibility
- ✅ Only stop on command failures

### Step-Specific Rules:

- 🎯 Execute commands in exact configured order
- 🚫 FAIL FAST - stop immediately on first failure
- 📊 Log progress to stdout
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Execute each command and capture output
- 💾 Track deployment state (version, success/failure, timing)
- 📖 Display progress for each command
- 🚫 FORBIDDEN to continue after any command fails

## CONTEXT BOUNDARIES:

- Available context: Ship configuration and commands from Step 1
- Focus: Sequential command execution with output capture
- Limits: Only execute configured commands, no improvisation
- Dependencies: Successful Step 1 completion with validated config

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Initialize Deployment Tracking

Store in memory:
```
deployment = {
  startTime: now(),
  steps: [],
  version: null,
  success: false,
  failedAt: null,
  outputs: {}
}
```

### 2. Execute Version Bump (if configured)

If `version_bump` command is configured:

Output to stdout:
```
[step-02] Executing version bump...
[step-02]   Running: [version_bump command]
```

Execute command and capture output.

If success:
- Parse new version from output (e.g., "v1.2.3")
- Store version: `deployment.version = newVersion`
- Output: `[step-02]   ✓ Version bumped to [version]`

If failure:
- Output: `[step-02]   ✗ Version bump failed`
- Store: `deployment.failedAt = 'version_bump'`
- Jump to Section 7 (Handle Failure)

### 3. Execute Build (if configured)

If `build` command is configured:

Output to stdout:
```
[step-02] Executing build...
[step-02]   Running: [build command]
```

Execute command and capture output.

If success:
- Output: `[step-02]   ✓ Build completed`

If failure:
- Output: `[step-02]   ✗ Build failed`
- Store: `deployment.failedAt = 'build'`
- Jump to Section 7 (Handle Failure)

### 4. Execute Publish

Output to stdout:
```
[step-02] Executing publish...
[step-02]   Running: [publish command]
```

Execute command and capture output.

If success:
- Output: `[step-02]   ✓ Published successfully`
- Parse any relevant output (registry URL, release URL, etc.)

If failure:
- Output: `[step-02]   ✗ Publish failed`
- Store: `deployment.failedAt = 'publish'`
- Jump to Section 7 (Handle Failure)

### 5. Execute Post-Publish (if configured)

If `post_publish` commands are configured:

Output to stdout:
```
[step-02] Executing post-publish commands...
```

For each post_publish command:
- Output: `[step-02]   Running: [command]`
- Execute and capture output

If any fails:
- Output: `[step-02]   ✗ Post-publish command failed`
- Store: `deployment.failedAt = 'post_publish'`
- Note: Publish already succeeded - flag as partial success (exit code 2)

If all succeed:
- Output: `[step-02]   ✓ Post-publish completed`

### 6. Handle Success

If all steps succeeded:

Output to stdout:
```
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-02] ✓ All deployment steps completed
[step-02]   Version Bump: ✓ [version or 'skipped']
[step-02]   Build: ✓ [or 'skipped']
[step-02]   Publish: ✓
[step-02]   Post-Publish: ✓ [or 'skipped']
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-02] ✓ Step 2 complete - proceeding to report
```

Store `deployment.success = true`, then proceed to Section 8.

### 7. Handle Failure

If any step failed:

Output to stdout:
```
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[step-02] ✗ Deployment failed
[step-02]   Failed at: [step name]
[step-02]   Error: [error summary]
[step-02]
[step-02]   Completed: [list of completed steps]
[step-02]   Not executed: [list of remaining steps]
[step-02] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Store failure context for report.

### 8. Auto-Proceed to Report

Store deployment context, then load, read entire file, then execute {nextStepFile}.

---

## DEPLOYMENT TYPE REFERENCE:

### npm
- version_bump: `npm version patch|minor|major`
- build: `npm run build`
- publish: `npm publish`

### docker
- build: `docker build -t [image] .`
- publish: `docker push [registry/image]`

### github-release
- build: custom build command
- publish: `gh release create [tag] --generate-notes`

### custom
- All commands as configured by user

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All configured commands executed in correct order
- Version tracked if bumped
- Output captured for each step
- Success/failure status clearly tracked
- Progress logged to stdout
- Auto-proceeded to report

### ❌ CRITICAL FAILURE (Exit 1):

- Deployment command failed (version bump, build, or publish)

### ⚠️ PARTIAL SUCCESS (Exit 2):

- Publish succeeded but post-publish failed

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
