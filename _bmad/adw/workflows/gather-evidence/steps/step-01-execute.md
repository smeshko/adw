---
name: 'step-01-execute'
description: 'Execute the complete evidence gathering flow autonomously'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/gather-evidence'

# File References
thisStepFile: '{workflow_path}/steps/step-01-execute.md'
workflowFile: '{workflow_path}/workflow.md'
projectConfig: '{project-root}/project-config.yaml'

# Platform-Skill Mapping
platform_skills:
  backend: review-backend-service
  web: null
  ios: null
  android: null
  cli: null
---

# Step 1: Execute Evidence Gathering

## STEP GOAL:

Execute the complete evidence gathering workflow autonomously: validate inputs, detect story file, check branch state, invoke platform skill, and output structured JSON to stdout.

## EXECUTION MODE:

- **Fully autonomous** - no user interaction
- **No menus** - execute straight through
- **Output to stdout only** - JSON format for all results
- **Silent execution** - no progress messages, only final JSON output

---

## EXECUTION SEQUENCE

### 1. Parse Arguments

Check if a story file path was provided as an argument to the workflow.

- If provided: Use that path as the story file
- If not provided: Proceed to auto-detection in step 2

### 2. Auto-Detect Story File (if needed)

If no story file was provided:

1. Get the current branch name: `git branch --show-current`
2. Extract story identifier from branch name (e.g., `feature/story-123` → `story-123`)
3. Search for matching story file in the stories folder
4. If no story file found, output error JSON and exit:

```json
{
  "issues": [],
  "report": {
    "summary": "Error: Could not auto-detect story file from branch name",
    "markdown": "## Evidence Report\n\n### Status: Error\n\nCould not auto-detect story file from branch name. Please provide a story file path as an argument.",
    "artifacts": []
  },
  "status": "error",
  "reason": "Could not auto-detect story file from branch name"
}
```

### 3. Check Branch Commits

Compare current branch to staging:

```bash
git log staging..HEAD --oneline
```

If no commits found (empty output), output skip JSON and exit:

```json
{
  "issues": [],
  "report": {
    "summary": "Skipped: No commits found compared to staging",
    "markdown": "## Evidence Report\n\n### Status: Skipped\n\nNo commits found compared to staging branch. Nothing to gather evidence for.",
    "artifacts": []
  },
  "status": "skipped",
  "reason": "No commits found compared to staging"
}
```

### 4. Read Project Configuration

Read `{projectConfig}` and extract the `platform` value.

If platform is not found or project-config.yaml doesn't exist, output error JSON and exit:

```json
{
  "issues": [],
  "report": {
    "summary": "Error: Could not read platform from project-config.yaml",
    "markdown": "## Evidence Report\n\n### Status: Error\n\nCould not read platform from project-config.yaml. Ensure the file exists and contains a valid `platform` value.",
    "artifacts": []
  },
  "status": "error",
  "reason": "Could not read platform from project-config.yaml"
}
```

### 5. Map Platform to Skill

Look up the skill for the detected platform using the mapping in frontmatter:

- `backend` → `review-backend-service`
- `web` → null (not available)
- `ios` → null (not available)
- `android` → null (not available)
- `cli` → null (not available)

If no skill is available for the platform, output skip JSON and exit:

```json
{
  "issues": [],
  "report": {
    "summary": "Skipped: No skill available for platform: {platform}",
    "markdown": "## Evidence Report\n\n### Status: Skipped\n\nNo evidence gathering skill is available for platform: {platform}. Currently supported: backend.",
    "artifacts": []
  },
  "status": "skipped",
  "reason": "No skill available for platform: {platform}"
}
```

### 6. Invoke Platform Skill

Use the Skill tool to invoke the mapped skill with the story file path:

```
Skill: {skill_name}
Args: {story_file_path}
```

### 7. Capture and Format Result

Capture the skill's output and transform it into the standard output format.

#### 7.1 Expected Skill Output

The skill returns its raw results. Extract from the skill's output:
- Any issues/errors found
- Test results (passed, failed, total)
- Files/artifacts created during execution
- Raw output or logs

#### 7.2 Transform to Standard Format

Build the output JSON:

```json
{
  "issues": [
    // Map skill issues to standard format:
    {
      "id": "evidence-{index}",
      "severity": "error | warning | info",
      "description": "{issue description}",
      "location": "{endpoint or component}",
      "context": { /* relevant details */ }
    }
  ],
  "report": {
    "summary": "{passed}/{total} endpoints passed, {failed} failed",
    "markdown": "## Evidence Report\n\n### Summary\n- Endpoints tested: {total}\n- Passed: {passed}\n- Failed: {failed}\n\n### Results\n{detailed results per endpoint}\n\n### Artifacts\n{list of files created}",
    "artifacts": [
      {
        "filename": "{actual filename created}",
        "type": "text | json | log",
        "description": "{what this file contains}"
      }
    ]
  },
  "status": "success",
  "reason": null
}
```

#### 7.3 Handle Skill Errors

If the skill fails to execute or returns unusable output:

```json
{
  "issues": [
    {
      "id": "skill-error-001",
      "severity": "error",
      "description": "Skill execution failed: {error message}",
      "location": "{skill_name}",
      "context": {
        "skill": "{skill_name}",
        "raw_output": "..."
      }
    }
  ],
  "report": {
    "summary": "Error: Skill execution failed",
    "markdown": "## Evidence Report\n\n### Status: Error\n\nThe {skill_name} skill failed to execute.\n\n### Error Details\n{error message or raw output}",
    "artifacts": []
  },
  "status": "error",
  "reason": "Skill execution failed"
}
```

---

## SUCCESS CRITERIA

- Skill was invoked and returned valid JSON structure
- Output was written to stdout
- Exit cleanly after output

## FAILURE MODES (all output as JSON to stdout)

- No story file found → error JSON
- No commits vs staging → skip JSON
- No platform in config → error JSON
- No skill for platform → skip JSON
- Skill execution failed → error JSON

**All paths result in JSON output to stdout. No exceptions.**
