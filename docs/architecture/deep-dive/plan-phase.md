# Plan Phase Deep Dive

This document explains the complete execution flow of the Plan phase in ADW.

## Overview

The Plan phase is the first phase in the ADW pipeline (`plan → build → verify → validate → document`). It generates an implementation plan for a feature description.

**Command:** `adw run "Feature description" --phase plan`

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CLI Entry (src/adw/cli/app.py)                              │
│     - Validates feature description                             │
│     - Generates ULID run_id                                     │
│     - Calls create_orchestrator()                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Bootstrap (src/adw/cli/bootstrap.py)                        │
│     Wires up: ContextManager, ArtifactManager, CommandResolver, │
│     TemplateEngine, HookRunner, ClaudeCodeExecutor, PhaseRunner │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Orchestrator (src/adw/core/orchestrator.py)                 │
│     - Creates RunContext with run_id, feature, status           │
│     - Creates .adw/runs/<run_id>/ directory structure           │
│     - Saves context.json                                        │
│     - Calls PhaseRunner.run("plan", context)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. PhaseRunner (src/adw/core/phase_runner.py)                  │
│     Step 1: Resolve command from 3-tier hierarchy               │
│     Step 2: Run pre-hook (git branch creation)                  │
│     Step 3: Render prompt.md with template variables            │
│     Step 4: Execute LLM via ClaudeCodeExecutor                  │
│     Step 5: Run post-hook (if exists)                           │
│     Step 6: Auto-commit changes                                 │
│     Step 7: Capture artifacts (plan_output.md)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Command Resolution (3-Tier Hierarchy)

The `CommandResolver` searches for the plan command in order:

1. **Project:** `.adw/commands/plan/`
2. **User:** `~/.adw/commands/plan/`
3. **Bundled:** `src/adw/defaults/commands/plan/`

A valid command directory must contain `prompt.md`. Optional files: `pre.sh`, `post.sh`, `schema.json`.

## Template Variables

When rendering `prompt.md`, these variables are available:

| Variable | Description |
|----------|-------------|
| `{{context}}` | Full RunContext model |
| `{{feature_description}}` | The feature string from CLI |
| `{{feature}}` | Alias for feature_description |
| `{{run_id}}` | ULID run identifier |
| `{{phase}}` | Current phase name ("plan") |
| `{{pre_hook_output}}` | Stdout captured from pre-hook |
| `{{artifacts.*}}` | Artifacts from previous phases (empty for plan) |
| `{{worktree_path}}` | Path to worktree if enabled |

## LLM Execution

**File:** `src/adw/executors/claude_code.py`

The executor spawns Claude CLI as a subprocess:

```bash
claude --print --verbose --output-format stream-json \
       --dangerously-skip-permissions "<rendered_prompt>"
```

- Working directory: worktree path or current directory
- Timeout: 600s default (configurable via `llm.timeout_seconds` in adw.yaml)
- Output: Streaming JSON lines parsed for text content, tool calls, and token usage

## Artifact Creation

**Important:** The SDK creates artifact files, not the LLM.

```python
# src/adw/core/phase_runner.py:751-777
output_name = f"{phase}_output.md"  # "plan_output.md"
self.artifact_manager.store(
    context.run_id,
    phase,
    output_name,
    llm_result.content,  # Raw LLM stdout saved as-is
)
```

The LLM outputs plain text to stdout. The SDK captures it and saves it to the artifact file.

## Output Directory Structure

After plan phase completes:

```
.adw/runs/<run_id>/
├── context.json                    # Run state
├── artifacts/
│   └── plan/
│       ├── plan_output.md          # Generated plan (LLM output)
│       └── plan_tool_calls.json    # Tool calls made (if any)
├── logs/
│   ├── logs.jsonl                  # Structured logs
│   └── raw.log                     # Human-readable log
├── llm/
│   ├── 001_request.json            # LLM prompt captured
│   └── 001_response.json           # LLM response captured
└── snapshots/
    ├── pre_plan.json               # State before phase
    └── post_plan.json              # State after phase
```

## Creating a Custom Plan Command

To customize the plan phase, create `.adw/commands/plan/prompt.md`:

```markdown
# Plan Phase

Generate an implementation plan for this feature.

## Feature
{{feature_description}}

## Output Format

### Summary
<One paragraph overview>

### Tasks
1. Task name
   - Files to modify: ...
   - Acceptance criteria: ...

### Dependencies
- External dependencies needed

### Risks
- Potential issues and mitigations
```

The LLM's text response will be saved verbatim to `plan_output.md`. You control the output format through your prompt instructions.

## Key Source Files

| File | Role |
|------|------|
| `src/adw/cli/app.py` | CLI entry point |
| `src/adw/cli/bootstrap.py` | Dependency injection |
| `src/adw/core/orchestrator.py` | Pipeline coordination |
| `src/adw/core/phase_runner.py` | Phase execution logic |
| `src/adw/commands/resolver.py` | 3-tier command resolution |
| `src/adw/commands/template.py` | Jinja2 prompt rendering |
| `src/adw/executors/claude_code.py` | LLM subprocess management |
| `src/adw/core/artifact_manager.py` | Artifact storage |
| `src/adw/defaults/commands/plan/prompt.md` | Default plan prompt |
| `src/adw/defaults/commands/plan/pre.sh` | Git branch pre-hook |
