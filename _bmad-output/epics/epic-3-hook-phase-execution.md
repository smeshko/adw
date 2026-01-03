# Epic 3: Hook & Phase Execution

**Goal:** Execute shell hooks (pre/post) and LLM calls within phases with streaming output, retry logic, and timeout support. This epic enables the core execution capability.

## Story 3.1: Execute Shell Hooks with Capture

As a developer,
I want to execute shell scripts as pre-hooks and post-hooks,
So that I can run custom logic before and after LLM execution.

**Acceptance Criteria:**

**Given** a pre-hook script at `commands/plan/pre-hook.sh`
**When** the hook is executed
**Then** stdout is captured and returned for use in templates
**And** stderr is logged

**Given** a hook script that exits with code 0
**When** execution completes
**Then** the hook is considered successful

**Given** a hook script that exits with non-zero code
**When** execution completes
**Then** HookError is raised with exit code, stdout, and stderr

**Given** a hook script that takes longer than the configured timeout
**When** timeout is reached
**Then** the process is killed and HookError is raised with code "HOOK_TIMEOUT"

**Given** environment variables in the run context
**When** the hook executes
**Then** they are available to the script (ADW_RUN_ID, ADW_PHASE, ADW_FEATURE, etc.)

**Given** a command directory without hooks
**When** hook execution is requested
**Then** it's silently skipped (not an error)

---

## Story 3.2: Implement Claude Code Executor with Streaming

As a developer,
I want to invoke Claude Code CLI and stream its output in real-time,
So that users see LLM responses as they're generated.

**Acceptance Criteria:**

**Given** a rendered prompt
**When** I call the Claude Code executor
**Then** it spawns `claude` (or configured path) as subprocess

**Given** Claude Code is producing output
**When** streaming is enabled
**Then** output appears in the console in real-time via Rich
**And** artifact writes don't block the stream (NFR3)

**Given** the configured Claude Code path doesn't exist
**When** execution is attempted
**Then** LLMError is raised with code "CLAUDE_NOT_FOUND" and suggestion to configure path

**Given** Claude Code execution completes
**When** I inspect the result
**Then** it includes: full content, tool_calls list, tokens_used, duration_ms

**Given** Claude Code respects the `--print` flag
**When** streaming output
**Then** tool calls are captured separately from text content

---

## Story 3.3: Implement Retry Logic with Exponential Backoff

As a developer,
I want transient LLM failures to be retried automatically,
So that temporary issues don't fail the entire run.

**Acceptance Criteria:**

**Given** LLMTimeoutError occurs during execution
**When** retries are configured (default: 3)
**Then** the request is retried with exponential backoff (1s, 2s, 4s)

**Given** LLMRateLimitError occurs during execution
**When** retries are configured
**Then** the request is retried with backoff respecting rate limit headers if available

**Given** all retry attempts fail
**When** the final attempt fails
**Then** the original error is raised with attempt count in the message

**Given** a non-retryable error (e.g., invalid prompt)
**When** error occurs
**Then** no retries are attempted and error is raised immediately

**Given** MockExecutor with configured failures
**When** first two attempts fail and third succeeds
**Then** execution succeeds with attempt_count=3

---

## Story 3.4: Implement Timeout Configuration and Enforcement

As a developer,
I want timeouts enforced on LLM execution,
So that hung processes don't block the pipeline indefinitely.

**Acceptance Criteria:**

**Given** a timeout of 300 seconds in project config
**When** Claude Code execution exceeds 300 seconds
**Then** the process is killed and LLMTimeoutError is raised

**Given** no timeout configured
**When** execution proceeds
**Then** a default timeout of 600 seconds is used

**Given** timeout occurs
**When** error is raised
**Then** it includes elapsed time and configured timeout in the message

**Given** execution completes before timeout
**When** result is returned
**Then** duration_ms is included in the result

---

## Story 3.5: Track Token Usage and Tool Calls

As a developer,
I want token usage and tool calls captured from each LLM execution,
So that I can monitor costs and understand what actions the LLM took.

**Acceptance Criteria:**

**Given** Claude Code execution completes
**When** I inspect LLMResult
**Then** tokens_used contains the token count from the execution

**Given** Claude Code makes tool calls during execution
**When** I inspect LLMResult.tool_calls
**Then** each tool call includes: tool_name, arguments, result_summary

**Given** the LLM execution for a phase
**When** phase completes
**Then** token usage is logged in structured format for aggregation

**Given** an entire run completes
**When** I query total tokens
**Then** it's the sum of all phase executions

---

## Epic 3: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately (PARALLEL)                                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [3-1] Execute Shell Hooks     ║     [3-2] Claude Code Executor              ║
║        with Capture            ║           with Streaming                    ║
║                                ║                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                 │
                                 ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 3-2 (PARALLEL x3)                                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [3-3] Retry Logic     ║  [3-4] Timeout Config    ║  [3-5] Token & Tool      ║
║  w/ Exp. Backoff       ║  and Enforcement         ║  Call Tracking           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Wave Summary

| Wave | Stories | Dependencies | Notes |
|------|---------|--------------|-------|
| **Wave 1** | 3.1, 3.2 | None | Can start immediately, run in parallel |
| **Wave 2** | 3.3, 3.4, 3.5 | All depend on 3.2 | Can run in parallel after 3.2 completes |

### Critical Path

3.2 → (3.3, 3.4, 3.5)

Story 3.2 (Claude Code Executor) is the critical path blocker for Wave 2.
Story 3.1 (Shell Hooks) is independent and does not block other stories.

---

## Story 3.6: Security Hook Infrastructure (Course Correction 2026-01-03)

As a developer,
I want ADW to block dangerous LLM tool calls,
So that automated code generation cannot accidentally destroy my project.

**Acceptance Criteria:**

**Given** LLM attempts to execute `rm -rf` or similar destructive commands
**When** the tool call is intercepted
**Then** the call is blocked and a warning is logged

**Given** LLM attempts to read `.env` or `.adw.env` files
**When** the tool call is intercepted
**Then** the call is blocked (except for `.env.example` or `.env.sample`)

**Given** any tool call is executed
**When** execution completes
**Then** the tool name, arguments, and result are logged to `tools.log`

**Given** security patterns are configurable
**When** `project.yaml` includes `security.blocked_patterns`
**Then** custom patterns are also blocked

---

## Story 3.7: Dangerous Command Patterns (Course Correction 2026-01-03)

As a developer,
I want a default set of blocked command patterns,
So that common destructive operations are prevented out of the box.

**Acceptance Criteria:**

**Given** default security configuration
**When** ADW initializes
**Then** these patterns are blocked by default:
- `rm -rf /` and variants (`rm -rf ~`, `rm -rf .`)
- `chmod 777` on sensitive paths
- `git push --force` to main/master
- Direct writes to `.env` files

**Given** a blocked pattern is triggered
**When** the block occurs
**Then** error includes: pattern matched, suggested alternative, how to override

**Given** user needs to override a block
**When** `--allow-dangerous` flag is passed
**Then** blocks are logged as warnings but not enforced

---

## Story 3.8: Tool Execution Logging (Course Correction 2026-01-03)

As a developer,
I want all LLM tool calls logged,
So that I can audit what the AI did during a run.

**Acceptance Criteria:**

**Given** any tool call during a phase
**When** the tool executes
**Then** entry is written to `.adw/runs/<id>/tools.jsonl`

**Given** tool log entry
**When** written
**Then** includes: timestamp, tool_name, arguments, result_summary, duration_ms

**Given** `adw logs tools <run_id>`
**When** executed
**Then** displays formatted tool execution history

---

## Updated Dependency Flowchart (with Security Hooks)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately (PARALLEL)                                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [3.1] Execute Shell Hooks     ║     [3.2] Claude Code Executor              ║
║        with Capture            ║           with Streaming                    ║
║                                ║                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                 │
                                 ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 3.2 (PARALLEL x3)                                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [3.3] Retry Logic     ║  [3.4] Timeout Config    ║  [3.5] Token & Tool      ║
║  w/ Exp. Backoff       ║  and Enforcement         ║  Call Tracking           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                 │
                                 ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 3.5 (PARALLEL x3) - Security Hooks                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [3.6] Security Hook   ║  [3.7] Dangerous Command ║  [3.8] Tool Execution   ║
║  Infrastructure        ║  Patterns                ║  Logging                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---
