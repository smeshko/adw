# Phase Runner

The `PhaseRunner` (`src/adw/core/phase_runner.py`) executes a single phase of the ADW pipeline. It coordinates the sequence: **Pre-hook → Prompt → LLM → Post-hook → Artifacts**.

## Core Responsibilities

| Responsibility | How |
|----------------|-----|
| Hook execution | Runs pre/post shell scripts via `HookRunner` |
| Prompt rendering | Loads template, injects artifacts from prior phases |
| LLM execution | Delegates to `LLMExecutor` (Claude Code or mock) |
| Artifact capture | Stores outputs for downstream phases |
| Progress display | Updates token count during streaming (Story 5.5) |

## Key Components

```
PhaseRunner
├── command_resolver    → Resolves phase config from commands/
├── template_engine     → Renders prompt templates with variables
├── hook_runner         → Executes pre/post shell scripts
├── executor            → LLM execution (streaming)
├── artifact_manager    → Stores phase outputs
└── progress_display    → Optional UI progress updates
```

## Phase Execution Flow

```
run(phase, context)
 ├── Resolve command config
 ├── Run pre-hook → capture stdout
 ├── Load prompt template
 │    ├── Build artifacts map from prior phases
 │    └── Render: expand includes, then fill ADW variables (see docs/templates.md)
 ├── Execute LLM → stream response
 ├── Run post-hook (ADW_LLM_OUTPUT in env)
 ├── Auto-commit changes
 └── Capture artifacts
      ├── {phase}_output.md (always)
      ├── {phase}_tool_calls.json (if any)
      └── diff.txt, diff_stats.json (build phase via extension)
```

## Template Variables

| Variable | Source |
|----------|--------|
| `{{context}}` | Full `RunContext` model |
| `{{pre_hook_output}}` | Pre-hook stdout |
| `{{artifacts.phase.name}}` | Prior phase artifacts |
| `{{inputs.name}}` | Files from the phase's `input_files` config |
| `{{task.*}}` | Task-manager fields (empty when the run has no task) |
| `{{run_id}}`, `{{phase}}` | Current run ID and phase name |
| `{{feature}}`, `{{feature_description}}` | User's feature request |
| `{{project_config}}` | `.adw/project.yaml` as a mapping |
| `{{ship_config}}` | Ship settings as YAML (ship phase, with a project ship config) |
| `{{doc_mappings}}` | Document phase `doc_mappings` from the project config |
| `{{build_command}}`, `{{test_command}}` | `.adw/project.yaml` |
| `{{lint_command}}` | Validate phase project config |
| `{{version_bump_command}}`, `{{publish_command}}` | Ship phase project config |
| Pre-hook variables | Keys from `pre_hook_vars.json`, e.g. `{{pr_number}}` |
| `{{schema}}` | Optional JSON schema from command dir |
| `{{worktree_path}}` | Git worktree path (if isolated) |

Includes are expanded before these are filled, and only these top-level names are filled; every other placeholder reaches the LLM verbatim. See [Templates](../../templates.md) for the syntax, the render order and the fill rule.

## Artifact Access in Templates

Templates reference prior phase outputs via nested map:

```
{{artifacts.plan.plan_output}}     → plan phase LLM output
{{artifacts.build.build_output}}   → build phase LLM output
{{artifacts.build.diff}}           → git diff from build (via extension)
{{artifacts.validate.validate_output}} → validate phase LLM output
```

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `HookError` | Fail phase, propagate to orchestrator |
| `LLMError` | Fail phase, propagate to orchestrator |
| `ConfigError` | Include directive fails: path traversal, missing file, or missing root |
| Missing artifact | Placeholder left verbatim, warning logged |

## Design Notes

**Extension-based artifacts**: Build phase captures git diff via `BuildExtension`. This pattern allows phase-specific artifact capture without hardcoding in the PhaseRunner core.

**Alias variables**: `{{feature}}` and `{{feature_description}}` are convenience shortcuts. The `{{artifacts.phase.name}}` pattern provides direct access to all phase outputs.

**Worktree support**: All git operations and LLM execution respect `context.worktree_path` for isolated runs (Story 10.5).
