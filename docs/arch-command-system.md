# Command System Architecture

## Overview

The command system provides a pluggable architecture for customizing phase behavior. Each phase (plan, build, validate, document, ship) is defined by a set of files that can be overridden at the project or user level.

**Design Principles:**

- **File-level overrides** — No deep merging; each file comes from one location
- **Fixed phases** — The pipeline is always: plan → build → validate → document → ship
- **Deterministic hooks** — Shell scripts handle predictable operations; LLM handles reasoning
- **Fail-fast validation** — Schema mismatches fail the phase immediately

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMMAND RESOLUTION                                  │
│                                                                             │
│   For phase "build", file "prompt.md":                                      │
│                                                                             │
│   ┌─────────────────────────────────┐                                       │
│   │ .agent/commands/build/prompt.md │ ──found?──▶ USE THIS                  │
│   └─────────────────────────────────┘                                       │
│                 │ not found                                                 │
│                 ▼                                                           │
│   ┌──────────────────────────────────────────┐                              │
│   │ ~/.config/agent/commands/build/prompt.md │ ──found?──▶ USE THIS         │
│   └──────────────────────────────────────────┘                              │
│                 │ not found                                                 │
│                 ▼                                                           │
│   ┌──────────────────────────────────────────────┐                          │
│   │ <install>/defaults/commands/build/prompt.md  │ ──found?──▶ USE THIS     │
│   └──────────────────────────────────────────────┘                          │
│                 │ not found                                                 │
│                 ▼                                                           │
│              ERROR (for required files)                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Resolution

Each file in a command directory is resolved independently. First match wins.

### Resolution Order

```
1. .agent/commands/<phase>/<file>           → Project override
2. ~/.config/agent/commands/<phase>/<file>  → User override  
3. <install>/defaults/commands/<phase>/<file> → Built-in default
```

### Command Directory Structure

```
commands/<phase>/
  ├── prompt.md        # Required: LLM prompt template
  ├── config.yaml      # Required: Phase configuration
  ├── pre.sh           # Optional: Runs before LLM
  ├── post.sh          # Optional: Runs after LLM
  └── schema.json      # Optional: Output validation schema
```

### File Requirements

| File | Required | Behavior if Missing |
|------|----------|---------------------|
| `prompt.md` | Yes | Error: phase cannot run |
| `config.yaml` | Yes | Error: phase cannot run |
| `pre.sh` | No | Skipped; no `{{pre_hook_output}}` |
| `post.sh` | No | Skipped; phase ends after LLM |
| `schema.json` | No | No output validation |

### Resolution Example

```
# Project overrides only the prompt
.agent/commands/build/
  └── prompt.md              ← USED

# User has nothing for build phase

# Defaults provide everything else
<install>/defaults/commands/build/
  ├── prompt.md              ← ignored (project wins)
  ├── config.yaml            ← USED
  ├── pre.sh                 ← USED
  ├── post.sh                ← USED
  └── schema.json            ← USED
```

---

## Phase Artifacts

Each phase produces artifacts with fixed names. No configuration.

### Artifact Locations

All artifacts written to: `.agent/runs/<run_id>/artifacts/<phase>/`

### Fixed Artifact Names

| Phase | Artifact | Format | Description |
|-------|----------|--------|-------------|
| plan | `plan.md` | Markdown | Implementation plan |
| build | `changes.patch` | Unified diff | Git diff of all changes |
| build | `files_modified.json` | JSON array | List of files touched |
| validate | `test_results.json` | JSON | Test runner output |
| validate | `lint_results.json` | JSON | Linter output |
| document | `docs.md` | Markdown | Generated documentation |
| ship | `deploy_record.json` | JSON | Deployment metadata |

### Artifact Availability

Artifacts become available to subsequent phases:

```
plan ──────▶ build ──────▶ validate ──────▶ document ──────▶ ship
  │            │              │                │              │
  ▼            ▼              ▼                ▼              ▼
plan.md    changes.patch  test_results.json  docs.md    deploy_record.json
           files_modified lint_results.json
```

---

## Variable Namespace

Variables available in `prompt.md` templates using `{{variable}}` syntax.

### Project Variables

Sourced from `.agent/project.yaml`:

| Variable | Type | Description |
|----------|------|-------------|
| `{{project.name}}` | string | Project name |
| `{{project.language}}` | string | Primary language (typescript, python, go, etc.) |
| `{{project.framework}}` | string \| null | Framework (nextjs, flask, rails, etc.) |
| `{{project.test_command}}` | string | Command to run tests |
| `{{project.lint_command}}` | string | Command to run linter |
| `{{project.build_command}}` | string | Command to build project |

### Run Variables

Current execution context:

| Variable | Type | Description |
|----------|------|-------------|
| `{{run.id}}` | string | Unique run identifier (e.g., `run_abc123`) |
| `{{run.feature_request}}` | string | Original user request |
| `{{run.current_phase}}` | string | Current phase name |
| `{{run.completed_phases}}` | JSON array | Phases already completed |

### Artifact Variables

Contents of previous phase artifacts (empty string if phase not yet complete):

| Variable | Type | Description |
|----------|------|-------------|
| `{{artifacts.plan}}` | string | Contents of `plan.md` |
| `{{artifacts.changes}}` | string | Contents of `changes.patch` |
| `{{artifacts.test_results}}` | string | Contents of `test_results.json` |
| `{{artifacts.lint_results}}` | string | Contents of `lint_results.json` |
| `{{artifacts.docs}}` | string | Contents of `docs.md` |

### Hook Output

| Variable | Type | Description |
|----------|------|-------------|
| `{{pre_hook_output}}` | string | stdout captured from `pre.sh` |

### File Inclusion

| Syntax | Description |
|--------|-------------|
| `{{file:path/to/file}}` | Inline file contents (path relative to repo root) |

Examples:
```
{{file:.agent/CONVENTIONS.md}}
{{file:src/schema.prisma}}
{{file:package.json}}
```

### Environment Variables

| Syntax | Description |
|--------|-------------|
| `{{env.VARIABLE_NAME}}` | Value of environment variable |

Examples:
```
{{env.NODE_ENV}}
{{env.DATABASE_URL}}
```

### Undefined Variables

- Render as empty string
- Warning logged: `"Variable '{{foo.bar}}' is undefined, rendering as empty string"`

---

## Hook Contracts

### Shared Environment Variables

Both `pre.sh` and `post.sh` receive these environment variables:

```bash
# Identity
AGENT_RUN_ID="run_abc123"
AGENT_PHASE="build"

# Paths (absolute)
AGENT_REPO_ROOT="/path/to/repo"
AGENT_RUN_DIR="/path/to/repo/.agent/runs/run_abc123"
AGENT_ARTIFACTS_DIR="/path/to/repo/.agent/runs/run_abc123/artifacts"

# Project metadata
AGENT_PROJECT_NAME="myproject"
AGENT_PROJECT_LANGUAGE="typescript"

# Request
AGENT_FEATURE_REQUEST="Add user authentication with OAuth"
```

---

### pre.sh Contract

**Purpose:** Gather context and prepare environment before LLM execution.

| Aspect | Specification |
|--------|---------------|
| Working directory | Repository root (`$AGENT_REPO_ROOT`) |
| stdin | Empty |
| stdout | Captured → available as `{{pre_hook_output}}` in prompt |
| stderr | Logged (not captured for prompt) |
| Exit code 0 | Continue to LLM execution |
| Exit code non-zero | Phase fails immediately |

**Example:**

```bash
#!/bin/bash
set -e

# Create feature branch
git checkout -b "feature/${AGENT_RUN_ID}" 2>/dev/null || true

# Output goes to {{pre_hook_output}} for the LLM prompt
echo "## Current Branch"
git branch --show-current

echo ""
echo "## Recent Commits"
git log --oneline -5

echo ""
echo "## Uncommitted Changes"
git status --short
```

---

### post.sh Contract

**Purpose:** Validate, format, or post-process after LLM execution.

| Aspect | Specification |
|--------|---------------|
| Working directory | Repository root (`$AGENT_REPO_ROOT`) |
| stdin | Empty |
| stdout | Logged (informational) |
| stderr | Logged |
| Exit code 0 | Phase succeeds |
| Exit code non-zero | Phase fails |

**Additional Environment:**

| Variable | Description |
|----------|-------------|
| `AGENT_LLM_OUTPUT_FILE` | Absolute path to file containing raw LLM output |

**Example:**

```bash
#!/bin/bash
set -e

echo "Running post-build validations..."

# Format any modified files
npm run format

# Type check
echo "Running type check..."
npm run typecheck

# Lint
echo "Running linter..."
npm run lint

# Record modified files for artifact
git diff --name-only > "$AGENT_ARTIFACTS_DIR/build/files_modified.json"

echo "Post-build validations passed"
```

---

## Schema Validation

When `schema.json` exists for a phase, LLM output is validated against it.

### Behavior

1. LLM output is parsed as JSON
2. Validated against JSON Schema (draft-07)
3. **Validation failure → phase fails immediately**
4. Validation errors included in logs and error output

### Schema Example

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["summary", "steps", "files_to_modify"],
  "additionalProperties": false,
  "properties": {
    "summary": {
      "type": "string",
      "minLength": 10,
      "description": "Brief description of the implementation plan"
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["description", "file"],
        "properties": {
          "description": { "type": "string" },
          "file": { "type": "string" }
        }
      }
    },
    "files_to_modify": {
      "type": "array",
      "items": { "type": "string" }
    },
    "estimated_complexity": {
      "type": "string",
      "enum": ["low", "medium", "high"]
    }
  }
}
```

### Validation Error Output

```
Phase 'plan' failed: Schema validation error

Errors:
  - /steps/0: Missing required property 'file'
  - /estimated_complexity: Value "extreme" is not one of: low, medium, high

Schema: .agent/commands/plan/schema.json
Output: .agent/runs/run_abc123/artifacts/plan/raw_output.json
```

---

## Config Schema

Phase configuration in `config.yaml`:

```yaml
# Execution limits
timeout_seconds: 300        # Max time for LLM execution (default: 300)
max_retries: 2              # Retry count on transient failures (default: 2)

# Human gates
require_approval: false     # Pause for approval before next phase (default: false)

# LLM settings
llm:
  temperature: 0            # 0 for deterministic output (default: 0)
  max_tokens: 16000         # Max output tokens (default: 16000)
```

### Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout_seconds` | integer | 300 | Maximum seconds for LLM call |
| `max_retries` | integer | 2 | Retries on transient LLM failures |
| `require_approval` | boolean | false | Require human approval after phase |
| `llm.temperature` | number | 0 | LLM temperature (0 = deterministic) |
| `llm.max_tokens` | integer | 16000 | Maximum output tokens |

### No Config Merging

The entire `config.yaml` is taken from one location. To override a single value, copy the entire file.

---

## Prompt Template Example

Complete example of a `prompt.md` file:

```markdown
# Build Phase

## Project Context

- **Project:** {{project.name}}
- **Language:** {{project.language}}
- **Framework:** {{project.framework}}

## Conventions

{{file:.agent/CONVENTIONS.md}}

## Implementation Plan

{{artifacts.plan}}

## Current State

{{pre_hook_output}}

## Feature Request

{{run.feature_request}}

---

## Instructions

Implement the changes described in the plan above. For each file:

1. Create or modify the file as specified
2. Follow the project conventions
3. Include appropriate error handling
4. Add comments for complex logic

Output your changes as a series of file operations.
```

---

## Resolution Debugging

The CLI provides commands to debug resolution:

```bash
# Show where each file comes from for a phase
$ agent command explain build

Phase: build
Resolution:
  prompt.md   → .agent/commands/build/prompt.md (project)
  config.yaml → ~/.config/agent/commands/build/config.yaml (user)
  pre.sh      → <install>/defaults/commands/build/pre.sh (default)
  post.sh     → .agent/commands/build/post.sh (project)
  schema.json → not found (validation disabled)

# Validate a command is properly configured
$ agent command validate build

✓ prompt.md found
✓ config.yaml found and valid
✓ pre.sh found and executable
✓ post.sh found and executable
⚠ schema.json not found (output validation disabled)

# Render a prompt with current context (dry run)
$ agent command render build --feature "Add auth"

[Rendered prompt output...]
```

---

## Summary

| Aspect | Behavior |
|--------|----------|
| Override granularity | Per-file (no merging) |
| Resolution order | Project → User → Default |
| Required files | `prompt.md`, `config.yaml` |
| Optional files | `pre.sh`, `post.sh`, `schema.json` |
| Artifact names | Fixed per phase |
| Variables | Project, run, artifacts, hooks, files, env |
| Undefined variables | Empty string + warning |
| Schema validation | Fail phase on mismatch |
| Config merging | None (whole file) |
