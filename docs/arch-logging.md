# Logging System Architecture

## Overview

A comprehensive logging system designed for full observability of agentic workflows. The system provides:

- **Formatted console output** with live streaming
- **Raw logs** for detailed debugging
- **Structured logs** for machine processing
- **State snapshots** for "time travel" debugging
- **LLM stream capture** including tool calls and reasoning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOGGING SYSTEM                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Log Manager                                      ││
│  │   • Central hub for all log events                                      ││
│  │   • Routes to appropriate transports                                    ││
│  │   • Manages log context (run_id, phase, step)                          ││
│  └────────────────────────────────┬────────────────────────────────────────┘│
│                                   │                                         │
│         ┌─────────────────────────┼─────────────────────────┐              │
│         │                         │                         │              │
│         ▼                         ▼                         ▼              │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐        │
│  │   Console   │          │    File     │          │  Structured │        │
│  │  Transport  │          │  Transport  │          │  Transport  │        │
│  │  (pretty)   │          │   (raw)     │          │   (JSON)    │        │
│  └─────────────┘          └─────────────┘          └─────────────┘        │
│         │                         │                         │              │
│         ▼                         ▼                         ▼              │
│     Terminal              .agent/runs/              .agent/runs/           │
│     (live)                <id>/logs/                <id>/logs/             │
│                           raw.log                   structured.jsonl       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      State Snapshotter                                   ││
│  │   • Captures full state at key moments                                  ││
│  │   • Enables "time travel" debugging                                     ││
│  │   • Stored in .agent/runs/<id>/snapshots/                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       LLM Stream Capture                                 ││
│  │   • Real-time token streaming                                           ││
│  │   • Tool call interception and logging                                  ││
│  │   • Thinking/reasoning block capture                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Log Levels & Verbosity

### Log Levels

```typescript
enum LogLevel {
  TRACE = 0,   // Everything, including internal state changes
  DEBUG = 1,   // Detailed debugging info
  INFO = 2,    // Normal operational messages
  WARN = 3,    // Warning conditions
  ERROR = 4,   // Error conditions
  FATAL = 5,   // Unrecoverable errors
}
```

### Verbosity Modes

```typescript
enum Verbosity {
  QUIET = 0,      // Errors only
  NORMAL = 1,     // Info + key milestones
  VERBOSE = 2,    // Debug + detailed steps
  TRACE = 3,      // Everything + raw data
}
```

### CLI Flags Mapping

| Flag | Verbosity |
|------|-----------|
| `--quiet`, `-q` | QUIET |
| (default) | NORMAL |
| `--verbose`, `-v` | VERBOSE |
| `--trace`, `-vv` | TRACE |

---

## Core Log Event Structure

```typescript
interface LogEvent {
  // Identity
  id: string                    // Unique event ID (ulid)
  timestamp: string             // ISO 8601 with microseconds
  
  // Context (inherited from current scope)
  context: {
    run_id: string
    phase?: string              // "plan" | "build" | etc
    step?: string               // "pre_hook" | "llm" | "post_hook"
    component: string           // "orchestrator" | "phase_runner" | "llm_executor"
  }
  
  // Event data
  level: LogLevel
  category: LogCategory
  message: string
  
  // Structured data (category-specific)
  data?: Record<string, unknown>
  
  // Error info (if applicable)
  error?: {
    name: string
    message: string
    stack?: string
    cause?: unknown
  }
  
  // Performance
  duration_ms?: number
  
  // For correlation
  parent_id?: string            // Links to parent event
  span_id?: string              // For tracing spans
}
```

### Log Categories

```typescript
enum LogCategory {
  // Lifecycle
  RUN_START = "run.start",
  RUN_END = "run.end",
  PHASE_START = "phase.start",
  PHASE_END = "phase.end",
  STEP_START = "step.start",
  STEP_END = "step.end",
  
  // Operations
  COMMAND_RESOLVE = "command.resolve",
  TEMPLATE_RENDER = "template.render",
  HOOK_EXECUTE = "hook.execute",
  ARTIFACT_SAVE = "artifact.save",
  ARTIFACT_LOAD = "artifact.load",
  
  // LLM specific
  LLM_REQUEST = "llm.request",
  LLM_STREAM = "llm.stream",
  LLM_TOOL_CALL = "llm.tool_call",
  LLM_TOOL_RESULT = "llm.tool_result",
  LLM_RESPONSE = "llm.response",
  LLM_ERROR = "llm.error",
  LLM_RETRY = "llm.retry",
  
  // State
  STATE_CHANGE = "state.change",
  STATE_SNAPSHOT = "state.snapshot",
  
  // Human interaction
  APPROVAL_REQUESTED = "approval.requested",
  APPROVAL_RECEIVED = "approval.received",
  
  // System
  CONFIG_LOAD = "config.load",
  VALIDATION_ERROR = "validation.error",
}
```

---

## Logger Interface

```typescript
interface Logger {
  // Scoped logging - creates child logger with inherited context
  child(context: Partial<LogContext>): Logger
  
  // Standard levels
  trace(message: string, data?: Record<string, unknown>): void
  debug(message: string, data?: Record<string, unknown>): void
  info(message: string, data?: Record<string, unknown>): void
  warn(message: string, data?: Record<string, unknown>): void
  error(message: string, error?: Error, data?: Record<string, unknown>): void
  fatal(message: string, error?: Error, data?: Record<string, unknown>): void
  
  // Structured events
  event(category: LogCategory, data: Record<string, unknown>): void
  
  // Timing helpers
  time(label: string): () => void  // Returns end function
  
  // State snapshots
  snapshot(label: string, state: unknown): void
  
  // LLM streaming
  streamStart(requestId: string): StreamLogger
}

interface StreamLogger {
  token(content: string): void
  toolCall(call: ToolCall): void
  toolResult(result: ToolResult): void
  thinking(content: string): void
  end(stats: LLMStats): void
  error(error: Error): void
}
```

### Usage Example

```typescript
const runLogger = logger.child({ run_id: "run_abc123" })
const phaseLogger = runLogger.child({ phase: "build" })
const stepLogger = phaseLogger.child({ step: "llm" })

stepLogger.info("Starting LLM execution", { 
  executor: "claude-code",
  prompt_tokens: 4500 
})
```

---

## Console Output Examples

### Normal Verbosity (default)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚀 Run Started: run_abc123                                                  │
│    Feature: Add user authentication with OAuth                              │
│    Phases: plan → build → validate → document → ship                        │
└─────────────────────────────────────────────────────────────────────────────┘

▶ PLAN ─────────────────────────────────────────────────────────────────────────
  ├─ Pre-hook: Gathering codebase context...                              [2.1s]
  ├─ LLM: Generating implementation plan...                              
  │   ╭────────────────────────────────────────────────────────────────────────╮
  │   │ Planning authentication system with the following components:          │
  │   │ 1. OAuth provider abstraction (Google, GitHub)                        │
  │   │ 2. Session management with secure tokens                              │
  │   │ 3. Protected route middleware                                         │
  │   │ ...                                                                   │
  │   ╰────────────────────────────────────────────────────────────────────────╯
  ├─ Post-hook: Validating plan structure...                              [0.3s]
  └─ ✓ Completed                                                         [45.2s]
     Artifact: .agent/runs/run_abc123/artifacts/plan/plan.md

▶ BUILD ────────────────────────────────────────────────────────────────────────
  ├─ Pre-hook: Creating feature branch...                                 [1.2s]
  │   Branch: feature/auth-oauth-abc123
  ├─ LLM: Implementing changes...
  │   ╭─ Tool Call ────────────────────────────────────────────────────────────╮
  │   │ 📁 create_file                                                         │
  │   │    path: src/auth/oauth-provider.ts                                   │
  │   │    content: [248 lines]                                               │
  │   ╰────────────────────────────────────────────────────────────────────────╯
  │   ╭─ Tool Call ────────────────────────────────────────────────────────────╮
  │   │ 📁 create_file                                                         │
  │   │    path: src/auth/session.ts                                          │
  │   │    content: [156 lines]                                               │
  │   ╰────────────────────────────────────────────────────────────────────────╯
  │   ╭─ Tool Call ────────────────────────────────────────────────────────────╮
  │   │ 🔧 execute_command                                                     │
  │   │    command: npm install @auth/core                                    │
  │   │    result: added 12 packages                                          │
  │   ╰────────────────────────────────────────────────────────────────────────╯
```

### Verbose Mode (`-v`)

```
▶ BUILD ────────────────────────────────────────────────────────────────────────
  ├─ Pre-hook: Creating feature branch...
  │   [DEBUG] Executing: .agent/commands/build/pre.sh
  │   [DEBUG] Working directory: /Users/dev/myproject
  │   [DEBUG] Environment: PHASE=build, RUN_ID=run_abc123
  │   stdout: Switched to new branch 'feature/auth-oauth-abc123'
  │   exit_code: 0
  │   duration: 1.2s
  │
  ├─ LLM: Implementing changes...
  │   [DEBUG] Executor: claude-code
  │   [DEBUG] Prompt tokens: 4,521
  │   [DEBUG] Temperature: 0
  │   [DEBUG] Max tokens: 16,000
  │   
  │   ╭─ Tool Call [call_01] ──────────────────────────────────────────────────╮
  │   │ 📁 create_file                                                         │
  │   │ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
  │   │ Input:                                                                 │
  │   │   path: "src/auth/oauth-provider.ts"                                  │
  │   │   content: |                                                          │
  │   │     import { OAuthConfig } from './types';                            │
  │   │                                                                        │
  │   │     export interface OAuthProvider {                                  │
  │   │       name: string;                                                   │
  │   │       ...                                                             │
  │   │     [+243 more lines - see raw log]                                   │
  │   │ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
  │   │ Result: success                                                        │
  │   │ Duration: 45ms                                                         │
  │   ╰────────────────────────────────────────────────────────────────────────╯
```

### Trace Mode (`-vv`)

```
[2024-01-15T10:23:45.123Z] TRACE [orchestrator] State change detected
  previous: { phase: "plan", status: "completed" }
  current:  { phase: "build", status: "running" }
  diff: { phase: "plan" → "build", status: "completed" → "running" }

[2024-01-15T10:23:45.125Z] DEBUG [phase_runner] Loading resolved command
  source: project (.agent/commands/build/)
  files: ["prompt.md", "config.yaml", "pre.sh", "post.sh"]
  config_merged: true
  
[2024-01-15T10:23:45.130Z] TRACE [template] Rendering prompt template
  variables: {
    "project.name": "myproject",
    "project.language": "typescript",
    "run.feature_request": "Add user authentication with OAuth",
    "run.accumulated_context": "Plan created with 4 components..."
  }
  template_size: 2,341 chars
  rendered_size: 4,892 chars

[2024-01-15T10:23:45.135Z] DEBUG [llm_executor] Preparing LLM request
  executor: claude-code
  model: claude-sonnet-4-20250514
  prompt_hash: sha256:a1b2c3d4...
  
[2024-01-15T10:23:45.140Z] TRACE [llm_executor] Full prompt:
  ┌──────────────────────────────────────────────────────────────────────────┐
  │ # Build Phase                                                            │
  │                                                                          │
  │ ## Project Context                                                       │
  │ - Project: myproject                                                     │
  │ - Language: typescript                                                   │
  │ ...                                                                      │
  │ [full prompt content - 4,892 chars]                                      │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure for Logs

```
.agent/
  runs/
    run_abc123/
      │
      ├── context.json              # Current run context (live updated)
      │
      ├── logs/
      │   ├── raw.log               # Plain text, all levels, full content
      │   ├── structured.jsonl      # Machine-readable, one JSON per line
      │   └── phases/
      │       ├── plan.log          # Phase-specific logs
      │       ├── build.log
      │       └── validate.log
      │
      ├── snapshots/
      │   ├── 001_run_start.json
      │   ├── 002_plan_complete.json
      │   ├── 003_build_start.json
      │   └── ...
      │
      ├── llm/
      │   ├── plan_request.json     # Full LLM request
      │   ├── plan_response.json    # Full LLM response
      │   ├── plan_stream.jsonl     # Token-by-token stream
      │   ├── build_request.json
      │   ├── build_response.json
      │   ├── build_stream.jsonl
      │   └── build_tools.jsonl     # Tool calls and results
      │
      └── artifacts/
          └── ...
```

---

## State Snapshotter

### Snapshot Structure

```typescript
interface StateSnapshot {
  id: string
  timestamp: string
  label: string
  trigger: "auto" | "manual" | "error"
  
  state: {
    session: SessionContext
    project: ProjectContext
    run: RunContext
  }
  
  // What changed since last snapshot
  diff_from_previous?: {
    snapshot_id: string
    changes: JsonPatch[]
  }
}
```

### Auto-Trigger Points

```typescript
class StateSnapshotter {
  static AUTO_TRIGGERS = [
    "run.start",
    "phase.start", 
    "phase.end",
    "approval.received",
    "error.occurred",
    "run.end"
  ]
  
  capture(label: string, trigger: "auto" | "manual" | "error"): StateSnapshot
  
  // Query snapshots
  list(runId: string): SnapshotSummary[]
  get(snapshotId: string): StateSnapshot
  diff(fromId: string, toId: string): JsonPatch[]
  
  // Time travel
  getStateAt(runId: string, timestamp: string): StateSnapshot
  getStateAtPhase(runId: string, phase: string, moment: "start" | "end"): StateSnapshot
}
```

### Snapshot Viewer CLI

```bash
# List all snapshots for a run
$ agent logs snapshots run_abc123

Snapshots for run_abc123:
  #  Timestamp                  Label              Trigger
  1  2024-01-15T10:23:45.000Z   run_start          auto
  2  2024-01-15T10:23:47.123Z   plan_start         auto
  3  2024-01-15T10:24:32.456Z   plan_end           auto
  4  2024-01-15T10:24:33.000Z   build_start        auto
  5  2024-01-15T10:26:15.789Z   build_error        error    ← 
  6  2024-01-15T10:26:16.000Z   build_retry_1      auto

# View specific snapshot
$ agent logs snapshot run_abc123 --id 5

Snapshot #5: build_error
Timestamp: 2024-01-15T10:26:15.789Z
Trigger: error

State:
{
  "run": {
    "current_phase": "build",
    "completed_phases": ["plan"],
    "phase_results": {
      "plan": { "status": "success", "artifact": "plan.md" },
      "build": { "status": "failed", "error": { ... } }
    }
  }
}

Changes from #4 (build_start):
  - run.phase_results.build.status: "running" → "failed"
  + run.phase_results.build.error: { "type": "llm", "message": "..." }
  + run.errors[0]: { ... }
```

---

## LLM Stream Logger

```typescript
interface LLMStreamLogger {
  // Called for each token
  onToken(token: string): void
  
  // Called when tool use is detected
  onToolCallStart(call: {
    id: string
    name: string
    input: unknown
  }): void
  
  onToolCallEnd(result: {
    id: string
    output: unknown
    duration_ms: number
    error?: Error
  }): void
  
  // For models that expose thinking
  onThinkingStart(): void
  onThinkingToken(token: string): void
  onThinkingEnd(): void
  
  // Final stats
  onComplete(stats: {
    input_tokens: number
    output_tokens: number
    duration_ms: number
    tool_calls: number
    retries: number
  }): void
  
  onError(error: Error): void
}
```

### Stream File Format

```jsonl
// build_stream.jsonl
{"t":0,"type":"token","content":"I'll"}
{"t":12,"type":"token","content":" create"}
{"t":24,"type":"token","content":" the"}
{"t":36,"type":"token","content":" OAuth"}
{"t":1250,"type":"tool_call_start","id":"call_01","name":"create_file","input":{...}}
{"t":1295,"type":"tool_call_end","id":"call_01","duration_ms":45,"success":true}
{"t":1300,"type":"token","content":"I've"}
...
{"t":45230,"type":"complete","stats":{"input_tokens":4521,"output_tokens":3892}}
```

---

## Debug Commands

### View Logs

```bash
# View live logs (like tail -f)
$ agent logs follow run_abc123
$ agent logs follow run_abc123 --phase build
$ agent logs follow run_abc123 --level debug

# View historical logs
$ agent logs show run_abc123
$ agent logs show run_abc123 --phase plan --raw
$ agent logs show run_abc123 --from "10:23:00" --to "10:25:00"

# Search logs
$ agent logs search run_abc123 "oauth"
$ agent logs search run_abc123 --category llm.tool_call
```

### View LLM Interactions

```bash
$ agent logs llm run_abc123 --phase build
$ agent logs llm run_abc123 --phase build --request    # Show full request
$ agent logs llm run_abc123 --phase build --response   # Show full response
$ agent logs llm run_abc123 --phase build --tools      # Show tool calls only
$ agent logs llm run_abc123 --phase build --stream     # Replay token stream
```

### State Inspection

```bash
$ agent logs state run_abc123                          # Current state
$ agent logs state run_abc123 --at "10:25:00"          # State at time
$ agent logs state run_abc123 --phase plan --end       # State after plan

# Diff between points
$ agent logs diff run_abc123 --from-phase plan --to-phase build
```

### Export for Sharing

```bash
$ agent logs export run_abc123 --format json > debug_bundle.json
$ agent logs export run_abc123 --format html > debug_report.html
```

---

## Integration with Phase Runner

```typescript
class PhaseRunner {
  constructor(
    private logger: Logger,
    private snapshotter: StateSnapshotter
  ) {}
  
  async run(phase: string, context: RunContext): Promise<PhaseResult> {
    const phaseLogger = this.logger.child({ phase })
    
    // Snapshot at phase start
    this.snapshotter.capture(`${phase}_start`, "auto")
    
    phaseLogger.event(LogCategory.PHASE_START, {
      phase,
      config: command.config,
      artifacts_available: context.completedPhases
    })
    
    const endTimer = phaseLogger.time(`phase.${phase}`)
    
    try {
      // Pre-hook
      if (command.hooks.pre) {
        const hookLogger = phaseLogger.child({ step: "pre_hook" })
        hookLogger.event(LogCategory.STEP_START, { script: command.hooks.pre })
        
        const result = await this.executeHook(command.hooks.pre, hookLogger)
        
        hookLogger.event(LogCategory.STEP_END, { 
          exit_code: result.exitCode,
          duration_ms: result.duration 
        })
      }
      
      // LLM execution
      const llmLogger = phaseLogger.child({ step: "llm" })
      const streamLogger = llmLogger.streamStart(generateId())
      
      llmLogger.event(LogCategory.LLM_REQUEST, {
        executor: command.config.llmExecutor,
        prompt_tokens: countTokens(renderedPrompt),
        temperature: command.config.llm.temperature
      })
      
      // Full prompt logged at TRACE level
      llmLogger.trace("Full prompt", { prompt: renderedPrompt })
      
      const llmResult = await this.llmExecutor.execute({
        prompt: renderedPrompt,
        onToken: (t) => streamLogger.token(t),
        onToolCall: (c) => streamLogger.toolCall(c),
        onToolResult: (r) => streamLogger.toolResult(r)
      })
      
      streamLogger.end(llmResult.stats)
      
      llmLogger.event(LogCategory.LLM_RESPONSE, {
        success: true,
        output_tokens: llmResult.stats.outputTokens,
        tool_calls: llmResult.toolCalls.length,
        duration_ms: llmResult.duration
      })
      
      // Full response logged at TRACE level
      llmLogger.trace("Full response", { response: llmResult.output })
      
      // ... post-hook, artifact capture, etc.
      
    } catch (error) {
      // Snapshot on error
      this.snapshotter.capture(`${phase}_error`, "error")
      
      phaseLogger.error(`Phase ${phase} failed`, error, {
        phase,
        step: currentStep,
        recoverable: isRecoverable(error)
      })
      
      throw error
      
    } finally {
      endTimer()
      this.snapshotter.capture(`${phase}_end`, "auto")
    }
  }
}
```

---

## Log Configuration

```yaml
# .agent/config.yaml or ~/.config/agent/config.yaml

logging:
  # Default verbosity (can be overridden with CLI flags)
  verbosity: normal  # quiet | normal | verbose | trace
  
  # Console settings
  console:
    colors: auto     # auto | always | never
    timestamps: false  # Show timestamps in console
    width: auto      # Terminal width (auto-detect)
    
  # File logging (always captures everything)
  file:
    enabled: true
    retention_days: 30
    max_size_mb: 100
    
  # LLM capture
  llm:
    capture_requests: true
    capture_responses: true
    capture_stream: true
    capture_tools: true
    # Redact sensitive data
    redact_patterns:
      - "Bearer [A-Za-z0-9-_]+"
      - "sk-[A-Za-z0-9]+"
      
  # State snapshots  
  snapshots:
    enabled: true
    auto_triggers:
      - run.start
      - phase.start
      - phase.end
      - error.occurred
      - run.end
```

---

## Summary

This logging system provides multiple layers of visibility:

| Layer | Purpose | Location |
|-------|---------|----------|
| Console (pretty) | Live monitoring, quick debugging | Terminal |
| Raw logs | Full text output, all details | `.agent/runs/<id>/logs/raw.log` |
| Structured logs | Machine processing, analysis | `.agent/runs/<id>/logs/structured.jsonl` |
| State snapshots | Time travel debugging | `.agent/runs/<id>/snapshots/` |
| LLM capture | Request/response/stream replay | `.agent/runs/<id>/llm/` |

The layered approach ensures you can quickly scan progress during normal operation but have full forensic capability when debugging issues.