# Validation Phase Redesign Analysis

> **Date**: 2026-01-08
> **Status**: Discussion / Proposal
> **Context**: Conversation about improving the validation phase architecture

---

## Table of Contents

1. [Current State](#1-current-state)
2. [The Three Validators](#2-the-three-validators)
3. [Evidence Gathering - Current Approach](#3-evidence-gathering---current-approach)
4. [Problem: Static Evidence Configuration](#4-problem-static-evidence-configuration)
5. [Proposal: LLM-Driven Evidence Gathering](#5-proposal-llm-driven-evidence-gathering)
6. [Proposal: LLM-Driven Validation Prompts](#6-proposal-llm-driven-validation-prompts)
7. [Tool-Based Execution Model](#7-tool-based-execution-model)
8. [Decisions Made](#8-decisions-made)
9. [Open Questions](#9-open-questions)
10. [Next Steps](#10-next-steps)

---

## 1. Current State

### Phase Sequence

```
Plan → Build → Validate → Document
```

The validation phase is the 3rd of 4 phases in the ADW pipeline.

### What Happens in Validate Phase

```
1. Platform Detection          [DETERMINISTIC]
   └── Detects: web, mobile, cli, backend

2. Load & Render Prompt        [DETERMINISTIC]
   └── Merges artifacts, context, schema into prompt.md

3. Execute LLM                 [LLM-DRIVEN]
   └── Analyzes build output against schema/requirements
   └── Generates validation report

4. Auto-Commit                 [DETERMINISTIC]
   └── Stages and commits changes

5. Evidence Gathering          [DETERMINISTIC]
   └── Platform-specific capture (screenshots, CLI output, API calls)

6. Evidence Optimization       [DETERMINISTIC]
   └── Image compression, text truncation
```

### Key Finding: Sophisticated Validation System Not Integrated

There is a sophisticated validation system built in `src/adw/validation/` that includes:

- `ValidationPhase` class
- `TestValidator` (runs pytest/npm test)
- `ReviewValidator` (LLM code review)
- `EvidenceValidator` (checks evidence manifest)
- `TriageSystem` (FIX/DISMISS/DEFER decisions)
- `FixEngine` (automated issue resolution)
- `ValidationLoopController` (retry logic)

**However**: This system is **NOT integrated** into the orchestrator. The `ValidationPhase` class is never instantiated. The config exists in `ADWConfig.validation` but is never read.

Currently, the validate phase just runs a simple LLM prompt through the generic `PhaseRunner`.

---

## 2. The Three Validators

### 2.1 TestValidator

**File**: `src/adw/validation/validators/test_validator.py`

**What it does**:
- Runs test suite via subprocess
- Parses output for failures
- Returns `ValidationIssue` list

**Supported frameworks**:
| Framework | Detection | Parsing |
|-----------|-----------|---------|
| pytest | `"pytest" in command` | `FAILED tests/file.py::test_name` |
| npm/jest | `"npm" or "jest" in command` | `FAIL file.test.js` |
| Generic | Fallback | Regex for `ERROR\|FAIL` |

**Execution**:
```python
result = subprocess.run(command, shell=True, timeout=300)
if result.returncode == 0:
    return []  # All passed
issues = self._parse_test_output(output, command)
return issues
```

### 2.2 ReviewValidator

**File**: `src/adw/validation/validators/review_validator.py`

**What it does**:
- Sends code changes to LLM with review prompt
- Parses response for severity-tagged issues
- Returns `ValidationIssue` list

**LLM prompt includes**:
- Feature description
- Focus areas (security, error_handling, edge_cases)
- Output format specification

**Response parsing**:
```python
# Pattern for issues
r"\[?(HIGH|MEDIUM|LOW|CRITICAL|INFO)\]?\s*[:\-]?\s*(.+?)\s+in\s+([^\s:]+\.py):?(\d+)?"
```

### 2.3 EvidenceValidator

**File**: `src/adw/validation/validators/evidence_validator.py`

**What it does**:
- Reads `evidence_manifest.json`
- Checks status of each evidence item
- Reports FAIL/ERROR items as `ValidationIssue`

---

## 3. Evidence Gathering - Current Approach

### Platform Detection → Strategy Selection

```python
strategy_map = {
    PlatformType.CLI:     EvidenceStrategy.TERMINAL_OUTPUT,
    PlatformType.WEB:     EvidenceStrategy.SCREENSHOT,
    PlatformType.MOBILE:  EvidenceStrategy.SCREENSHOT,
    PlatformType.BACKEND: EvidenceStrategy.API_CAPTURE,
}
```

### By Platform

#### CLI Projects
- Loads commands from `.adw/project.yaml`
- Executes via `subprocess.run()`
- Captures stdout, stderr, exit code
- Output: `evidence/cli/*.txt`

```yaml
# .adw/project.yaml
evidence:
  commands:
    - name: version
      cmd: "adw --version"
```

#### WEB Projects
- Loads routes from `.adw/project.yaml`
- Uses **Playwright** for browser screenshots
- Captures at multiple viewports
- Output: `evidence/screenshots/*.png`

```yaml
evidence:
  base_url: "http://localhost:3000"
  routes:
    - name: home
      path: /
      wait_for: networkidle
```

#### MOBILE Projects
- Detects iOS Simulator or Android Emulator
- Loads screen configs from `.adw/project.yaml`
- Navigates via deeplinks
- Output: `evidence/mobile/*.png`

```yaml
evidence:
  mobile:
    screens:
      - name: home
        deeplink: "myapp://home"
```

#### BACKEND Projects
- Loads endpoint configs from `.adw/project.yaml`
- Uses **httpx** for HTTP requests
- Captures request/response pairs
- Output: `evidence/api/*.json`

```yaml
evidence:
  base_url: "http://localhost:8000"
  endpoints:
    - name: health
      method: GET
      path: /health
      expected_status: 200
```

---

## 4. Problem: Static Evidence Configuration

### The Fundamental Flaw

Evidence configuration is **static** in `project.yaml`, but each run implements a **different feature**.

```
Current Flow:
┌──────────────────────────────────────────────────────────────┐
│  project.yaml (static)          │  Run #1: "Add login"      │
│  ─────────────────────          │  Run #2: "Add dashboard"  │
│  routes:                        │  Run #3: "Add user API"   │
│    - /                          │                           │
│    - /about                     │  ← Same evidence gathered │
│  endpoints:                     │     for every feature!    │
│    - GET /health                │                           │
└──────────────────────────────────────────────────────────────┘
```

You implement a login feature, but the system captures screenshots of `/` and `/about` because that's what's in the static config.

**The evidence doesn't match what was built.**

---

## 5. Proposal: LLM-Driven Evidence Gathering

### Core Principle

**Scripts for execution, LLM for decision-making.**

```
┌─────────────────────────────────────────────────────────────┐
│                    EVIDENCE GATHERING                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   LLM Layer (Intelligence)                                   │
│   ├── Decides WHAT to capture                               │
│   ├── Decides HOW to navigate/prepare                       │
│   ├── Provides inputs (API bodies, test data)               │
│   └── Orchestrates the sequence                             │
│                                                              │
│   ─────────────────────────────────────────────────────     │
│                                                              │
│   Script Layer (Execution)                                   │
│   ├── start_simulator(scheme, device)                       │
│   ├── capture_screenshot(output_path)                       │
│   ├── call_endpoint(method, url, body)                      │
│   └── run_tests(pattern)                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. LLM analyzes build output + diff
2. LLM generates evidence plan for THIS specific feature
3. LLM invokes deterministic tools to gather evidence
4. Evidence is captured

### Example

```
LLM analyzes: "I implemented user registration API and signup page"

LLM decides and executes:
  → call_endpoint("POST", "/users", {"email": "test@test.com", ...})
  → call_endpoint("POST", "/users", {"email": "existing@test.com", ...})  # error case
  → capture_screenshot("/signup", "desktop")
  → capture_screenshot("/signup", "mobile")
  → run_command("pytest tests/test_users.py -v")
```

### What Stays in project.yaml

Infrastructure config only:

```yaml
evidence:
  web:
    base_url: "http://localhost:3000"
  api:
    base_url: "http://localhost:8000"
    auth:
      type: bearer
      token_env: API_TOKEN
```

### Mobile: Deferred

Mobile evidence gathering is significantly more complex because it requires **multi-turn agentic navigation with vision**:

1. LLM sees current screen state
2. LLM decides what to tap/interact with
3. System executes the tap
4. LLM sees new screen state
5. Repeat until target screen reached
6. Capture screenshot

This is essentially computer-use agent territory.

**Decision**: Skip mobile evidence gathering for now, revisit later.

### Simpler Cases (CLI, API, Web)

For these, the LLM can generate a complete plan in **one shot**:

| Type | LLM Decides | Script Executes | Complexity |
|------|-------------|-----------------|------------|
| CLI | What commands to run | `run_command(cmd)` | Simple |
| API | What endpoints, methods, bodies | `call_endpoint(...)` | Simple |
| Web | What URLs to capture | `capture_page(url, viewport)` | Simple-Medium |

No multi-turn navigation loop needed.

---

## 6. Proposal: LLM-Driven Validation Prompts

### Current Approach

```
TestValidator     → subprocess.run("pytest") → hardcoded parsing
ReviewValidator   → LLM prompt (hardcoded in code)
EvidenceValidator → read manifest.json → check status
```

### Proposed Approach

Replace deterministic validators with customizable prompt templates:

```
run-tests.md      → LLM decides how to run tests, interprets results
code-review.md    → LLM reviews code (customizable prompt)
gather-evidence.md→ LLM gathers evidence (customizable prompt)
```

### Benefits

1. **Customizable per project**: User defines how tests run
2. **Framework agnostic**: Works with any test framework
3. **Consistent architecture**: Everything is prompt-driven
4. **Contextual intelligence**: LLM understands nuanced failures

### Concerns Raised

| Concern | Severity | Mitigation |
|---------|----------|------------|
| Tests might not run | High | Require tool invocation, fail if not called |
| Non-deterministic | Medium | Log all decisions, acceptable tradeoff |
| Parsing errors | Medium | Structured output format |
| Security | Medium | Sandboxed tool execution |
| Cost/latency | Low | Acceptable for better results |
| Debugging | Medium | Comprehensive logging |

### The "Skip Tests" Problem

LLM might rationalize:
```
"These tests are testing old code, I'll skip them"
"The build succeeded so tests probably pass"
```

**Mitigation**: The system should verify that test-related tools were actually invoked.

---

## 7. Tool-Based Execution Model

### How LLM Uses Tools

Same pattern as Claude Code - LLM has tools available and invokes them:

```
┌─────────────────────────────────────────────────────────────┐
│  1. System sends to LLM:                                     │
│     - Prompt (run-tests.md)                                  │
│     - Context (build output, diff)                          │
│     - Available tools                                        │
│                                                              │
│  2. LLM responds with tool call:                             │
│     → run_command("pytest tests/ -v")                        │
│                                                              │
│  3. System executes tool, returns result:                    │
│     ← stdout, stderr, exit_code                              │
│                                                              │
│  4. LLM analyzes, maybe calls more tools                     │
│                                                              │
│  5. LLM produces structured output:                          │
│     ← ValidationIssues as JSON                               │
└─────────────────────────────────────────────────────────────┘
```

### Available Tools

```python
tools = [
    # Test execution
    {
        "name": "run_command",
        "description": "Execute a shell command",
        "parameters": {"cmd": str, "timeout": int}
    },

    # Evidence capture
    {
        "name": "capture_screenshot",
        "description": "Capture browser screenshot",
        "parameters": {"url": str, "viewport": str}
    },
    {
        "name": "call_endpoint",
        "description": "Make HTTP request",
        "parameters": {"method": str, "path": str, "body": dict}
    },
]
```

### Execution Model

```python
def execute_tool(name: str, params: dict) -> str:
    """Deterministic tool execution."""
    if name == "run_command":
        result = subprocess.run(params["cmd"], shell=True, ...)
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        })

    elif name == "capture_screenshot":
        path = playwright_capture(params["url"], params["viewport"])
        return json.dumps({"path": str(path), "success": True})

    elif name == "call_endpoint":
        response = httpx.request(params["method"], params["path"], ...)
        return json.dumps({...})
```

### Key Point

**Tool execution is deterministic** - subprocess always runs the same way, Playwright always captures the same way.

**LLM decides**:
- Which tools to call
- With what parameters
- How to interpret results
- What to report

---

## 8. Decisions Made

### Confirmed Decisions

1. **Skip mobile evidence gathering for now** - Too complex, requires multi-turn agentic vision

2. **Evidence gathering should be LLM-driven** - Static config doesn't match dynamic features

3. **Use tools + prompts model** - Scripts for execution, LLM for orchestration

4. **Keep infrastructure config in project.yaml** - Base URLs, auth, viewports

### Architecture Direction

```
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION PHASE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Prompts (customizable):                                     │
│    ├── run-tests.md                                          │
│    ├── code-review.md                                        │
│    └── gather-evidence.md                                    │
│                                                              │
│  Tools (deterministic scripts):                              │
│    ├── run_command(cmd)                                      │
│    ├── capture_screenshot(url, viewport)                     │
│    ├── call_endpoint(method, path, body)                     │
│    └── run_tests(pattern)                                    │
│                                                              │
│  LLM orchestrates tools based on prompts and context         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Open Questions

### High Priority

1. **How to ensure tests actually run?**
   - Should system verify `run_command` was called with test command?
   - What if LLM decides tests aren't needed?

2. **Structured output format for ValidationIssues**
   - JSON schema?
   - How to ensure LLM follows format?

3. **Integration with existing TriageSystem and FixEngine**
   - These expect `ValidationIssue` objects
   - How do LLM-generated issues feed into fix loop?

### Medium Priority

4. **Cost management**
   - Multiple tool calls = more tokens
   - How to optimize?

5. **Logging and debugging**
   - How to capture full decision trace?
   - How to reproduce issues?

6. **User customization of prompts**
   - Where are prompts stored?
   - How to override per-project?

### Lower Priority

7. **Mobile evidence gathering**
   - Deferred, but need eventual solution
   - Deeplinks vs navigation vs hybrid?

8. **Validation loop with LLM-driven issues**
   - How does fix engine work with this model?
   - Is FixEngine also LLM-driven?

---

## 10. Next Steps

### Immediate

1. [ ] Design prompt templates for each validation stage
   - `run-tests.md`
   - `code-review.md`
   - `gather-evidence.md`

2. [ ] Define tool schemas
   - Parameters, return types
   - Error handling

3. [ ] Decide on structured output format
   - JSON schema for ValidationIssues

### Short-term

4. [ ] Prototype LLM-driven test execution
   - Start with simplest case (CLI)

5. [ ] Integrate with PhaseRunner tool execution
   - ADW already has LLM executor with tool support

6. [ ] Update orchestrator to use new approach

### Future

7. [ ] Revisit mobile evidence gathering
8. [ ] Consider fix loop integration
9. [ ] User documentation for customization

---

## Appendix: File Locations

### Current Implementation

| Component | Location |
|-----------|----------|
| Orchestrator | `src/adw/core/orchestrator.py` |
| PhaseRunner | `src/adw/core/phase_runner.py` |
| ValidationPhase | `src/adw/validation/phase.py` |
| TestValidator | `src/adw/validation/validators/test_validator.py` |
| ReviewValidator | `src/adw/validation/validators/review_validator.py` |
| EvidenceValidator | `src/adw/validation/validators/evidence_validator.py` |
| TriageSystem | `src/adw/validation/triage.py` |
| FixEngine | `src/adw/validation/fix_engine.py` |
| LoopController | `src/adw/validation/loop_controller.py` |
| Evidence Package | `src/adw/evidence/` |
| Evidence Models | `src/adw/models/evidence.py` |

### Default Prompts

| Prompt | Location |
|--------|----------|
| Validate | `src/adw/defaults/commands/validate/prompt.md` |
| Validate Config | `src/adw/defaults/commands/validate/config.yaml` |

---

## Appendix: Current Evidence Tools

### CLI Capture
- `CLIEvidenceGatherer` - Orchestrator
- `CLICaptureStrategy` - Command execution
- `EvidenceFileWriter` - Output writing

### Web Capture
- `WebCaptureStrategy` - Playwright-based screenshots
- Requires: `playwright` package

### API Capture
- `APICaptureStrategy` - httpx-based HTTP calls
- Requires: `httpx` package

### Mobile Capture
- `capture_ios_screenshot()` - xcrun simctl
- `capture_android_screenshot()` - adb
- `capture_flutter_screenshot()` - flutter screenshot

### Optimization
- `EvidenceOptimizer` - Image compression, text truncation
- Requires: `pillow` package (optional)

### Manifest
- `ManifestGenerator` - Creates evidence_manifest.json
- `PlanStepLinker` - Links evidence to plan steps
