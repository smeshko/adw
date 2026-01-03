# Epic 7: Observability & Logging

**Goal:** Provide multi-tier logging (console, raw file, structured JSONL), LLM interaction capture, and debugging commands for state inspection, log search, and export.

## Story 7.1: Implement Multi-Tier Logging System

As a developer,
I want logs written to console, raw file, and structured JSONL,
So that I have appropriate output for different use cases.

**Acceptance Criteria:**

**Given** any log message
**When** logged
**Then** it appears in console (via Rich), raw.log, and logs.jsonl

**Given** console output
**When** TTY is detected
**Then** Rich formatting with colors is used

**Given** console output
**When** non-TTY (piped/redirected)
**Then** plain text without colors/animations (UX-7)

**Given** structured log entry
**When** written to JSONL
**Then** it includes: timestamp, level, category, message, context fields

**Given** the LogCategory enum
**When** logging
**Then** categories include: PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE

---

## Story 7.2: Configure Verbosity Levels

As a user,
I want to control log verbosity,
So that I see the right amount of detail for my needs.

**Acceptance Criteria:**

**Given** command with `-q` or `--quiet`
**When** executing
**Then** only errors and final results are shown

**Given** command with no flags (default)
**When** executing
**Then** phase progress and key events are shown

**Given** command with `-v` or `--verbose`
**When** executing
**Then** detailed execution info including hook output is shown

**Given** command with `--trace`
**When** executing
**Then** all debug information including template rendering is shown

**Given** verbosity setting
**When** applied
**Then** it affects console output only, not file logs

---

## Story 7.3: Capture LLM Interactions

As a developer,
I want full LLM request/response captured,
So that I can debug and reproduce issues.

**Acceptance Criteria:**

**Given** LLM execution
**When** capturing
**Then** full request (prompt, params) is saved to `llm/<seq>_request.json`

**Given** LLM execution
**When** capturing
**Then** full response (content, tool_calls, tokens) is saved to `llm/<seq>_response.json`

**Given** streaming output
**When** capturing
**Then** raw stream is captured to `llm/<seq>_stream.txt`

**Given** captured LLM interactions
**When** replayed with same prompt
**Then** equivalent behavior can be reproduced (NFR12)

**Given** captured interactions
**When** reviewing
**Then** no API keys or secrets are included (NFR14)

---

## Story 7.4: Implement Log Viewing Commands

As a user,
I want to view and search logs from CLI,
So that I can debug issues without navigating files manually.

**Acceptance Criteria:**

**Given** command `adw logs show <run_id>`
**When** executed
**Then** displays recent log entries from the run

**Given** command `adw logs follow <run_id>`
**When** run is active
**Then** streams new log entries in real-time (FR47)

**Given** command `adw logs search <pattern>`
**When** executed
**Then** searches logs across runs for matching entries (FR48)

**Given** command `adw logs llm <run_id>`
**When** executed
**Then** shows LLM prompts and responses for the run (FR49)

**Given** command `adw logs export <run_id>`
**When** executed
**Then** creates a shareable bundle of logs and state (FR52)

---

## Story 7.5: Implement State Inspection Commands

As a user,
I want to inspect and diff state snapshots,
So that I can debug state-related issues.

**Acceptance Criteria:**

**Given** command `adw logs state <run_id>`
**When** executed
**Then** displays current or final state of the run (FR50)

**Given** command `adw logs state <run_id> --snapshot <seq>`
**When** executed
**Then** displays state at that specific snapshot

**Given** command `adw logs diff <run_id> <phase1> <phase2>`
**When** executed
**Then** shows differences between states at those phases (FR51)

**Given** command `adw logs snapshots <run_id>`
**When** executed
**Then** lists all available snapshots with labels (FR53)

**Given** snapshot inspection
**When** debugging
**Then** enables "time travel" to understand state evolution (NFR13)

---

## Story 7.6: Implement Secret Redaction

As a developer,
I want sensitive data redacted from logs,
So that secrets are never exposed.

**Acceptance Criteria:**

**Given** log message containing API key pattern
**When** logged
**Then** the key is replaced with [REDACTED] (NFR14)

**Given** environment variables with sensitive names
**When** logged
**Then** values are redacted (API_KEY, SECRET, TOKEN, PASSWORD)

**Given** configurable redaction patterns in project.yaml
**When** logging
**Then** custom patterns are also redacted (NFR17)

**Given** a log export
**When** generated
**Then** all redaction rules are applied

---

## Epic 7: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [7.1] Implement Multi-Tier Logging System                                    ║
║        Foundation for all logging infrastructure                              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 7.1 (PARALLEL x4)                                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [7.2] Configure          [7.3] Capture LLM       [7.5] State         [7.6]  ║
║        Verbosity                Interactions            Inspection     Secret ║
║        Levels                                           Commands       Redact ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                │                         │
                │                         ▼
                │   ╔═══════════════════════════════════════════════════════════╗
                │   ║  WAVE 3: After 7.3                                        ║
                │   ╠═══════════════════════════════════════════════════════════╣
                │   ║                                                           ║
                └──▶║  [7.4] Implement Log Viewing Commands                     ║
                    ║        (requires LLM captures for 'logs llm' command)     ║
                    ║                                                           ║
                    ╚═══════════════════════════════════════════════════════════╝
```

### Dependency Summary

| Story | Depends On | Blocks | Parallel With |
|-------|------------|--------|---------------|
| 7.1 | None | 7.2, 7.3, 7.4, 7.5, 7.6 | None |
| 7.2 | 7.1 | None | 7.3, 7.5, 7.6 |
| 7.3 | 7.1 | 7.4 | 7.2, 7.5, 7.6 |
| 7.4 | 7.1, 7.3 | None | 7.5 |
| 7.5 | 7.1 | None | 7.2, 7.3, 7.4, 7.6 |
| 7.6 | 7.1 | None | 7.2, 7.3, 7.5 |

---
