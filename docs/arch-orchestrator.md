# Orchestrator Core - Deep Dive

## Overview

The Orchestrator Core is the central hub that coordinates all execution. It consists of three main components:

1. **Context Manager** - Maintains state at multiple scopes
2. **Command Resolver** - Finds and assembles the right command for each phase
3. **Phase Runner** - Executes phases with their scripts and LLM calls

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR CORE                                 │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Entry Handler                                 │  │
│  │   • Normalizes input from CLI/Webhook/GitHub/Linear                  │  │
│  │   • Produces a standard RunRequest object                            │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Context Manager                                │  │
│  │                                                                       │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │   │   Session   │  │   Project   │  │    Run      │  │  Artifact  │  │  │
│  │   │   Context   │  │   Context   │  │   Context   │  │   Store    │  │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Command Resolver                               │  │
│  │                                                                       │  │
│  │   User Override ──▶ Project Override ──▶ Default ──▶ [Resolved Cmd]  │  │
│  │                                                                       │  │
│  │   • Loads prompt template                                            │  │
│  │   • Merges configurations                                            │  │
│  │   • Validates command structure                                      │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Phase Runner                                  │  │
│  │                                                                       │  │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐   │  │
│  │   │ pre.sh  │───▶│   LLM   │───▶│ post.sh │───▶│ Artifact Export │   │  │
│  │   └─────────┘    └─────────┘    └─────────┘    └─────────────────┘   │  │
│  │                                                                       │  │
│  │   • Handles retries & error recovery                                 │  │
│  │   • Enforces timeouts                                                │  │
│  │   • Captures structured output                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Context Manager

The Context Manager maintains state at multiple scopes and makes it available to commands.

### Context Layers

#### Session Context

Ephemeral - lives for one CLI invocation or webhook request.

```
┌─────────────────────────────────────────────────────────────────┐
│                      SESSION CONTEXT                             │
│                                                                  │
│  • run_id: unique identifier for this execution                 │
│  • trigger_source: "cli" | "webhook" | "github" | "linear"      │
│  • trigger_payload: raw input data                              │
│  • started_at: timestamp                                        │
│  • dry_run: boolean                                             │
│  • interactive: boolean (can prompt for human input?)           │
└─────────────────────────────────────────────────────────────────┘
```

#### Project Context

Loaded from `.agent/project.yaml` - committed to repo.

```
┌─────────────────────────────────────────────────────────────────┐
│                      PROJECT CONTEXT                             │
│                                                                  │
│  • project_name: string                                         │
│  • repo_root: path                                              │
│  • language: "typescript" | "python" | "swift" | etc            │
│  • framework: "nextjs" | "flutter" | "vapor" | etc              │
│  • test_command: "npm test" | "pytest" | etc                    │
│  • lint_command: "eslint ." | "ruff check" | etc                │
│  • build_command: "npm run build" | etc                         │
│  • conventions: path to CONVENTIONS.md or inline rules          │
│  • llm_executor: "claude-code" | "aider" | "custom"             │
│  • custom_phases: ["security-review", "perf-test"]              │
└─────────────────────────────────────────────────────────────────┘
```

#### Run Context

Built up during execution - persisted to `.agent/runs/<id>/`.

```
┌─────────────────────────────────────────────────────────────────┐
│                        RUN CONTEXT                               │
│                                                                  │
│  • feature_request: string (the original ask)                   │
│  • current_phase: "plan" | "build" | "validate" | etc           │
│  • completed_phases: ["plan", "build"]                          │
│  • phase_results: {                                             │
│      "plan": { status: "success", artifact: "plan.md" },        │
│      "build": { status: "success", files_modified: [...] }      │
│    }                                                            │
│  • accumulated_context: string (rolling summary for LLM)        │
│  • errors: []                                                   │
│  • human_decisions: []  (captured approvals/rejections)         │
└─────────────────────────────────────────────────────────────────┘
```

### Artifact Store

```typescript
interface ArtifactStore {
  // Base path: .agent/runs/<run_id>/artifacts/
  
  save(phase: string, name: string, content: string | Buffer): ArtifactRef
  load(ref: ArtifactRef): string | Buffer
  list(phase?: string): ArtifactRef[]
  
  // Special artifact types with schema validation
  savePlan(plan: PlanSchema): ArtifactRef
  saveTestResults(results: TestResultsSchema): ArtifactRef
}
```

#### Directory Structure After a Run

```
.agent/
  runs/
    run_abc123/
      context.json          # Serialized RunContext
      artifacts/
        plan/
          plan.md
          plan.json         # Structured version
        build/
          files_modified.json
        validate/
          test_results.json
          lint_results.json
```

> **Note on patch files:** `changes.patch` is only generated when running in `dry_run` mode, 
> for non-git projects, or when explicitly configured with `save_patches: true`. In normal 
> operation, git itself tracks changes, making patches redundant.

#### context.json Schema

The `context.json` file is written incrementally after each phase completes, enabling resume from failure. It contains summary information—detailed LLM interactions (tool calls, token streams) are stored separately in the `llm/` directory.

```typescript
interface ContextFile {
  version: string
  finalized_at?: string                // Set when run completes
  
  session: {
    run_id: string
    trigger_source: "cli" | "webhook" | "github" | "linear"
    trigger_payload: unknown
    started_at: string
    ended_at?: string
    duration_ms?: number
    dry_run: boolean
    interactive: boolean
  }
  
  project: {
    project_name: string
    repo_root: string
    language: string
    framework?: string
    test_command?: string
    lint_command?: string
    format_command?: string
    llm_executor: string
  }
  
  run: {
    feature_request: string
    status: "running" | "completed" | "failed" | "cancelled"
    current_phase: string | null
    phases_executed: string[]
    phases_skipped: string[]
    
    phase_results: {
      [phase: string]: {
        status: "success" | "failed" | "skipped" | "awaiting_approval"
        started_at: string
        ended_at: string
        duration_ms: number
        artifacts: string[]
        hooks: {
          pre: { exit_code: number, duration_ms: number } | null
          post: { exit_code: number, duration_ms: number } | null
        }
        llm: {
          executor: string
          input_tokens: number
          output_tokens: number
          duration_ms: number
          retries: number
          tool_call_count: number     // Summary only, details in llm/<phase>_tools.jsonl
        }
        files_created?: string[]
        files_modified?: string[]
        error?: {
          type: string
          message: string
          recoverable: boolean
        }
      }
    }
    
    accumulated_context: string       // Rolling summary for LLM continuity
    errors: Array<{ phase: string, error: string, timestamp: string }>
    human_decisions: Array<{ phase: string, decision: string, timestamp: string }>
    
    git?: {
      starting_ref: string
      starting_sha: string
      branch_created?: string
      commits: string[]
    }
  }
  
  artifacts_manifest: Array<{
    phase: string
    name: string
    size_bytes: number
    hash: string
  }>
  
  totals?: {                          // Computed at finalization
    duration_ms: number
    llm_input_tokens: number
    llm_output_tokens: number
    files_created: number
    files_modified: number
    tool_call_count: number
  }
}
```

> **Note on tool calls:** Individual tool calls (which can number in the hundreds) are 
> stored in `llm/<phase>_tools.jsonl`, not in context.json. Only the `tool_call_count` 
> summary is included here to keep the file lightweight and fast to parse.

### Context Injection into Prompts

The Context Manager provides a template variable system:

```markdown
<!-- commands/plan/prompt.md -->

# Feature Planning

## Project Context
- Project: {{project.name}}
- Language: {{project.language}}
- Framework: {{project.framework}}

## Conventions
{{file:.agent/CONVENTIONS.md}}

## Request
{{run.feature_request}}

## Previous Context
{{#if run.accumulated_context}}
Previous work on this feature:
{{run.accumulated_context}}
{{/if}}

---

Create a detailed implementation plan...
```

---

## 2. Command Resolver

The Command Resolver finds and assembles the right command configuration for a phase.

### Resolution Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                     RESOLUTION ORDER                             │
│                                                                  │
│  1. ~/.config/agent/commands/<phase>/     (User global)         │
│         │                                                        │
│         ▼ not found? try next                                   │
│  2. ./.agent/commands/<phase>/            (Project local)       │
│         │                                                        │
│         ▼ not found? try next                                   │
│  3. <install_dir>/defaults/commands/<phase>/  (Built-in)        │
│         │                                                        │
│         ▼ not found?                                            │
│  4. ERROR: Unknown phase "<phase>"                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Command Structure

```
commands/
  plan/
    prompt.md           # Required: the prompt template
    config.yaml         # Optional: phase-specific settings
    pre.sh              # Optional: runs before LLM
    post.sh             # Optional: runs after LLM  
    schema.json         # Optional: expected output schema
    
  build/
    prompt.md
    config.yaml
    pre.sh              # e.g., create feature branch
    post.sh             # e.g., run formatter
    
  validate/
    prompt.md
    config.yaml
    pre.sh              # e.g., run tests, capture output
    post.sh             # e.g., collect coverage report
```

### Default Hook Scripts

The SDK provides default pre/post hooks following the principle: **safe defaults, opt-in mutations**.

#### Default Hook Matrix

| Phase | Pre-Hook (Default) | Post-Hook (Default) | Notes |
|-------|-------------------|---------------------|-------|
| `plan` | ✓ Gather codebase context | ✓ Validate plan structure | Read-only |
| `build` | ✗ None | ✓ Run formatter (if configured) | Branch creation opt-in |
| `validate` | ✓ Run tests, capture output | ✓ Summarize results | Uses project.test_command |
| `document` | ✗ None | ✓ Validate doc format | Read-only |
| `ship` | ✗ None | ✗ None | Too dangerous for defaults |

#### Example Default Hooks

**`defaults/commands/plan/pre.sh`** — Read-only context gathering:
```bash
#!/bin/bash
echo "=== Project Structure ==="
find src -type f -name "*.${PROJECT_LANGUAGE_EXT}" | head -50

echo "=== Recent Changes ==="
git log --oneline -10

echo "=== Open TODOs ==="
grep -r "TODO\|FIXME" src --include="*.${PROJECT_LANGUAGE_EXT}" | head -20
```

**`defaults/commands/validate/pre.sh`** — Uses project config:
```bash
#!/bin/bash
if [ -n "$PROJECT_TEST_COMMAND" ]; then
  echo "Running: $PROJECT_TEST_COMMAND"
  $PROJECT_TEST_COMMAND > "$ARTIFACT_DIR/test_output.txt" 2>&1
  echo $? > "$ARTIFACT_DIR/test_exit_code"
else
  echo "No test_command configured"
fi
```

**`defaults/commands/build/post.sh`** — Conditional formatting:
```bash
#!/bin/bash
if [ -n "$PROJECT_FORMAT_COMMAND" ]; then
  echo "Running formatter: $PROJECT_FORMAT_COMMAND"
  $PROJECT_FORMAT_COMMAND
fi
git diff --stat
```

#### What Defaults Should NOT Do

```bash
# ❌ Never in default hooks - these require explicit opt-in:
git checkout -b ...     # Branch strategy varies by team
git commit ...          # Commit granularity is project-specific
git push               # Never auto-push
npm install            # Could break things unexpectedly
rm / delete            # Dangerous
```

#### Opting Into Mutating Behaviors

Projects can enable mutations via config:

```yaml
# .agent/project.yaml
hooks:
  build:
    create_branch: true
    branch_pattern: "feature/{{run.id}}"
    auto_commit: false
  ship:
    strategy: "pr"           # Opens PR instead of direct merge
    require_approval: true   # Human gate before any action
```

### Config Merging

Configurations merge with specificity (more specific wins):

```yaml
# defaults/commands/build/config.yaml (built-in)
timeout: 300
max_retries: 2
require_approval: false
llm:
  temperature: 0
  max_tokens: 16000

# .agent/commands/build/config.yaml (project override)
timeout: 600  # Override: longer timeout for this project
require_approval: true  # Override: require human approval
# llm settings inherited from default

# Final merged config:
# timeout: 600
# max_retries: 2
# require_approval: true
# llm:
#   temperature: 0
#   max_tokens: 16000
```

### Resolver Interface

```typescript
interface ResolvedCommand {
  phase: string
  promptTemplate: string
  config: PhaseConfig
  hooks: {
    pre?: ScriptPath
    post?: ScriptPath
  }
  outputSchema?: JSONSchema
  source: "user" | "project" | "default"
}

interface CommandResolver {
  resolve(phase: string): ResolvedCommand
  listAvailable(): PhaseInfo[]
  validate(phase: string): ValidationResult
  
  // For debugging/transparency
  explainResolution(phase: string): ResolutionTrace
}
```

#### Example Resolution Trace

```json
{
  "phase": "build",
  "checked": [
    { "path": "~/.config/agent/commands/build", "found": false },
    { "path": "./.agent/commands/build", "found": true, "partial": true },
    { "path": "/defaults/commands/build", "found": true }
  ],
  "merged": {
    "prompt": "./.agent/commands/build/prompt.md",
    "config": "merged from project + default",
    "pre": "/defaults/commands/build/pre.sh",
    "post": "./.agent/commands/build/post.sh"
  }
}
```

---

## 3. Phase Runner

The Phase Runner executes a single phase with its scripts and LLM call.

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      PHASE RUNNER FLOW                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. PREPARATION                                              ││
│  │    • Load ResolvedCommand from Command Resolver             ││
│  │    • Render prompt template with Context Manager vars       ││
│  │    • Validate preconditions (required artifacts exist?)     ││
│  └─────────────────────────────────┬───────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 2. PRE-HOOK (deterministic)                                 ││
│  │    • Run pre.sh if exists                                   ││
│  │    • Script can: gather info, create files, set env vars    ││
│  │    • Output captured and available as {{pre_hook_output}}   ││
│  │    • Non-zero exit = phase fails                            ││
│  └─────────────────────────────────┬───────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 3. LLM EXECUTION                                            ││
│  │    • Invoke configured LLM executor with rendered prompt    ││
│  │    • Stream output to console (if interactive)              ││
│  │    • Apply timeout from config                              ││
│  │    • Retry on transient failures (up to max_retries)        ││
│  │    • Validate output against schema.json if provided        ││
│  └─────────────────────────────────┬───────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 4. POST-HOOK (deterministic)                                ││
│  │    • Run post.sh if exists                                  ││
│  │    • Script can: format code, run tests, validate output    ││
│  │    • Has access to LLM output via env/file                  ││
│  │    • Can transform/enrich the output                        ││
│  └─────────────────────────────────┬───────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 5. ARTIFACT CAPTURE                                         ││
│  │    • Save phase output to Artifact Store                    ││
│  │    • Update Run Context (completed_phases, etc.)            ││
│  │    • Generate accumulated_context summary for next phase    ││
│  └─────────────────────────────────┬───────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 6. APPROVAL GATE (if require_approval: true)                ││
│  │    • If interactive: prompt human for approval              ││
│  │    • If non-interactive: pause and wait for external signal ││
│  │    • Record decision in human_decisions[]                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### LLM Executor Abstraction

```typescript
interface LLMExecutor {
  name: string
  
  execute(request: ExecutionRequest): Promise<ExecutionResult>
  
  // Capability detection
  supportsStreaming(): boolean
  supportsStructuredOutput(): boolean
  supportsTools(): boolean
}

interface ExecutionRequest {
  prompt: string
  workingDirectory: string
  config: LLMConfig
  outputSchema?: JSONSchema
  
  // For executors that support it
  tools?: ToolDefinition[]
  systemPrompt?: string
}

interface ExecutionResult {
  success: boolean
  output: string
  structuredOutput?: unknown  // If schema was provided
  tokensUsed?: { input: number, output: number }
  duration: number
  
  // For agentic executors that modify files
  filesModified?: string[]
  filesCreated?: string[]
}

// Built-in executors
class ClaudeCodeExecutor implements LLMExecutor { ... }
class AiderExecutor implements LLMExecutor { ... }
class RawAPIExecutor implements LLMExecutor { ... }  // Direct API calls
```

### Error Handling & Recovery

```typescript
interface PhaseRunner {
  run(phase: string, context: RunContext): Promise<PhaseResult>
  
  // Recovery options
  retry(runId: string, phase: string): Promise<PhaseResult>
  resume(runId: string): Promise<PipelineResult>  // From last successful
  rollback(runId: string, toPhase: string): Promise<void>
}

interface PhaseResult {
  phase: string
  status: "success" | "failed" | "skipped" | "awaiting_approval"
  artifact?: ArtifactRef
  error?: {
    type: "pre_hook" | "llm" | "post_hook" | "validation" | "timeout"
    message: string
    recoverable: boolean
  }
  duration: number
  llmStats?: { tokens: number, retries: number }
}
```

---

## How They Work Together

```typescript
// Simplified orchestration flow
async function runPipeline(request: RunRequest): Promise<PipelineResult> {
  // 1. Context Manager initializes contexts
  const session = contextManager.createSession(request)
  const project = contextManager.loadProject()
  const run = contextManager.createRun(session, project, request.featureRequest)
  
  // 2. Determine phases to run
  const phases = request.phases ?? ["plan", "build", "validate", "document", "ship"]
  
  for (const phase of phases) {
    // 3. Command Resolver finds the right command
    const command = commandResolver.resolve(phase)
    
    // 4. Context Manager renders the prompt
    const renderedPrompt = contextManager.renderTemplate(
      command.promptTemplate,
      { session, project, run }
    )
    
    // 5. Phase Runner executes
    const result = await phaseRunner.run(phase, {
      command,
      prompt: renderedPrompt,
      context: run
    })
    
    // 6. Context Manager updates state
    contextManager.recordPhaseResult(run, phase, result)
    
    if (result.status === "failed" && !result.error?.recoverable) {
      break
    }
    
    if (result.status === "awaiting_approval") {
      // Non-interactive: save state and exit
      // Interactive: wait for input
    }
  }
  
  return contextManager.finalize(run)
}
```
