---
name: run-tests
description: Autonomously run all configured test commands with auto-fix capability. Designed for CI/automation.
web_bundle: true
---

# Run Tests

**Goal:** Autonomously run all configured test, lint, and quality commands from project-config.yaml, automatically fix failures, and commit fixes.

**Your Role:** You are a test runner and code fixer that executes configured test commands autonomously. Work autonomously to complete all steps, reporting results clearly at completion. User interaction is only needed if unrecoverable errors require manual intervention.

---

## CI/AUTOMATION DESIGN

This is an **action workflow** designed for autonomous execution in CI pipelines.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed (including after fixes) |
| 1 | Tests failed after fix attempts |

### Output

Output is **always** structured JSON to stdout (for agent-to-agent communication):

```json
{
  "status": "passed|failed",
  "summary": { "total": N, "errors": N, "warnings": N, "fixed": N },
  "issues": [
    {
      "id": "type-NNN",
      "severity": "error|warning",
      "type": "test_failure|lint_error|type_error|build_error",
      "command": "unit|e2e|lint|typecheck|custom",
      "description": "Error message",
      "location": "file:line",
      "context": { "test_name": "...", "stack_trace": "...", "fixable": bool, "fix_hint": "..." }
    }
  ]
}
```

- Returns empty `issues` array on success
- Issue IDs are unique per run (e.g., `test-001`, `lint-002`)

---

## WORKFLOW ARCHITECTURE

This is an **action workflow** that executes commands and fixes code autonomously.

### Core Principles

- **Config-Driven**: All commands come from `_bmad/project-config.yaml`
- **Run All**: Execute all configured commands, don't fail fast
- **Auto-Fix**: Attempt to fix failures automatically (max 3 attempts)
- **Auto-Commit**: Commit successful fixes with descriptive messages
- **Auto-Proceed**: Move between steps automatically (no user confirmation)
- **JSON Output**: Output structured JSON with issues array to stdout
- **Fail-Safe**: Handle errors gracefully, continue where possible, report all issues

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Move to next step immediately upon completion (no menu wait)
4. **BUILD ISSUES**: Collect and structure issues for final JSON output
5. **TRACK STATE**: Maintain execution context between steps for final reporting
6. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Execution Rules

1. **READ CONFIG**: Load test configuration from project-config.yaml
2. **RUN ALL**: Execute every enabled command, collect all results
3. **FIX LOOP**: If failures, attempt fixes up to 3 times
4. **COMMIT FIXES**: Auto-commit any successful fixes
5. **REPORT**: Output final JSON to stdout with exit code

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 🔄 **ALWAYS** run all configured commands (don't fail fast)
- 🎯 **ALWAYS** follow the exact instructions in the step file
- 📊 **ALWAYS** track results for final reporting
- ⏹️ **STOP** only when workflow completes or unrecoverable error occurs

### Workflow-Specific Rules

- 📖 **ALWAYS** read project-config.yaml first
- 💾 **ALWAYS** commit fixes with descriptive messages
- 📊 **ALWAYS** build structured issues for JSON output
- 🎯 **ALWAYS** report final status clearly
- ⏹️ **STOP** fix attempts after 3 tries

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`

Load project config from {project-root}/_bmad/project-config.yaml and resolve:

- `test` section with all configured commands

### 2. First Step EXECUTION

Load, read the full file and then execute `{workflow_path}/steps/step-01-init.md` to begin the workflow.
