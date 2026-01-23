---
name: gather-evidence
description: Gather evidence for implementation by invoking platform-specific skills
web_bundle: true
---

# Gather Evidence

**Goal:** Analyze a WIP branch against a story file and invoke platform-specific skills to gather implementation evidence, outputting structured JSON to stdout.

**Execution Mode:** Fully autonomous - no user interaction required.

---

## PLATFORM-SKILL MAPPING

```yaml
backend: review-backend-service
web: null      # Future
ios: null      # Future
android: null  # Future
cli: null      # Future
```

---

## WORKFLOW ARCHITECTURE

### Core Principles

- **Autonomous Execution**: Run without user interaction, output JSON to stdout
- **Platform-Driven**: Skill selection based on project-config.yaml platform value
- **Orchestrator Pattern**: This workflow delegates evidence gathering to platform-specific skills
- **Consistent Output**: All results (success, warnings, errors) use the same JSON structure

### Output Format

All output goes to stdout as JSON:

```json
{
  "issues": [
    {
      "id": "string (optional)",
      "severity": "error | warning | info",
      "description": "string (required)",
      "location": "string (optional)",
      "context": {}
    }
  ],
  "summary": {
    "total": 0,
    "passed": 0,
    "failed": 0
  },
  "status": "success | skipped | error",
  "reason": "string (when status != success)"
}
```

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read full config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `platform`

### 2. Execute

Load, read the full file and then execute `{workflow_path}/steps/step-01-execute.md` to run the evidence gathering.
