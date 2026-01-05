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
 │    ├── Validate artifact references
 │    └── Render with variables
 ├── Execute LLM → stream response
 ├── Run post-hook (ADW_LLM_OUTPUT in env)
 └── Capture artifacts
      ├── {phase}_output.md (always)
      ├── {phase}_tool_calls.json (if any)
      ├── diff.txt, diff_stats.json (build phase)
      └── evidence_manifest.json (verify phase)
```

## Template Variables

| Variable | Source |
|----------|--------|
| `{{context}}` | Full `RunContext` model |
| `{{pre_hook_output}}` | Pre-hook stdout |
| `{{artifacts.phase.name}}` | Prior phase artifacts |
| `{{feature_description}}` | User's feature request |
| `{{schema}}` | Optional JSON schema from command dir |
| `{{worktree_path}}` | Git worktree path (if isolated) |

## Artifact Access in Templates

Templates reference prior phase outputs via nested map:

```
{{artifacts.plan.plan_output}}   → plan phase LLM output
{{artifacts.build.diff}}         → git diff from build
{{artifacts.verify.evidence_manifest}} → evidence JSON
```

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `HookError` | Fail phase, propagate to orchestrator |
| `LLMError` | Fail phase, propagate to orchestrator |
| `ConfigError` | Fail if `strict_artifacts=True` and artifact missing |

## Design Notes

**Special-case artifacts**: Build phase captures git diff, verify phase copies evidence manifest. These are hardcoded rather than config-driven (technical debt).

**Alias variables**: `{{plan}}`, `{{implementation}}`, `{{output}}` are convenience shortcuts to common artifacts. Inconsistently named (technical debt).

**Worktree support**: All git operations and LLM execution respect `context.worktree_path` for isolated runs (Story 10.5).
