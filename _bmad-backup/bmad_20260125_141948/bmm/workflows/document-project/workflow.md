---
name: document-project
description: Autonomously analyzes and documents brownfield projects by scanning codebase, architecture, and patterns to create comprehensive reference documentation for AI-assisted development
web_bundle: false
---

# Document Project Workflow

**Goal:** Autonomously analyze and document brownfield projects by scanning codebase structure, architecture patterns, and implementation details to create comprehensive reference documentation optimized for AI-assisted development.

**Your Role:** You are a technical documentarian that executes codebase analysis and documentation generation. Work autonomously to complete all steps, reporting results clearly at completion. User interaction is only needed if critical errors require manual intervention.

---

## CI/AUTOMATION DESIGN

This is an **action workflow** designed for autonomous execution in CI pipelines and automated environments.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_MODE` | `full` | Scan mode: `full` (complete scan) or `quick` (pattern-based only) |
| `SCAN_LEVEL` | `deep` | Depth: `quick`, `deep`, or `exhaustive` |
| `FAIL_ON_WARNING` | `false` | Exit with error on non-critical warnings |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - documentation generated |
| 1 | Critical failure - could not complete scan |
| 2 | Partial success - completed with warnings |

### Output

- **Documentation files**: Generated in `{output_folder}/`
- **State file**: `{output_folder}/project-scan-report.json`
- **Stdout**: Progress logging for CI visibility

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that executes autonomously:

### Core Principles

- **Config-Driven**: Scan mode and level from environment variables or config
- **Run All**: Execute all steps sequentially, collecting results throughout
- **Auto-Proceed**: Move between steps automatically without user confirmation
- **Clear Reporting**: Provide comprehensive status at workflow completion
- **Fail-Safe**: Log warnings and continue where possible, fail on critical errors only

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Move to next step immediately upon completion (no menu wait)
4. **TRACK STATE**: Update state file for progress tracking and debugging
5. **LOG PROGRESS**: Output step completion to stdout for CI visibility
6. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 🔄 **ALWAYS** continue on non-critical errors (log and proceed)
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📊 **ALWAYS** track results for final reporting
- ⏹️ **STOP** only on critical errors or workflow completion

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read full config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`, `communication_language`, `document_output_language`, `user_skill_level`

Load environment variable overrides:

- `SCAN_MODE` → `scan_mode` (default: `full`)
- `SCAN_LEVEL` → `scan_level` (default: `deep`)
- `FAIL_ON_WARNING` → `fail_on_warning` (default: `false`)

### 2. Path Definitions

- `workflow_path` = `{project-root}/_bmad/bmm/workflows/document-project`
- `output_folder` = from config (typically `{project-root}/_bmad-output`)
- `state_file` = `{output_folder}/project-scan-report.json`
- `documentation_requirements_csv` = `{workflow_path}/documentation-requirements.csv`

### 3. Stdout Initialization

Output to stdout:
```
[document-project] Starting autonomous documentation scan
[document-project] Mode: {scan_mode} | Level: {scan_level}
[document-project] Output: {output_folder}
```

### 4. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
