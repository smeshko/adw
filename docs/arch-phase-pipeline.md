# Phase Pipeline Architecture

## Overview

The phase pipeline is the core execution flow of the agentic development system. It transforms a feature request into shipped code through a sequence of discrete, resumable phases.

**Pipeline Sequence:**

```
Plan → Build → Verify → Validate → Document → Ship
```

**Design Principles:**

- **Fixed sequence** — Phases always execute in this order; skip phases via configuration, not reordering
- **Artifact accumulation** — Each phase produces artifacts consumed by subsequent phases
- **Checkpoint resumption** — Pipeline can resume from any completed phase after failure
- **Determinism/autonomy split** — Scripts handle predictable operations; LLM handles reasoning
- **Platform awareness** — Evidence gathering adapts to project type (web, mobile, CLI, backend)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE PIPELINE                                     │
│                                                                             │
│  ┌──────┐    ┌───────┐    ┌────────┐    ┌──────────┐    ┌─────┐    ┌──────┐│
│  │ Plan │───▶│ Build │───▶│ Verify │───▶│ Validate │───▶│ Doc │───▶│ Ship ││
│  └──┬───┘    └───┬───┘    └───┬────┘    └────┬─────┘    └──┬──┘    └──┬───┘│
│     │            │            │              │             │          │     │
│     ▼            ▼            ▼              ▼             ▼          ▼     │
│  plan.md    files_mod.    evidence/     test_results   docs.md   deploy_   │
│  plan.json  json          manifest.json lint_results            record.json│
│                           screenshots/  .json                              │
│                           terminal/                                        │
│                           api/                                             │
│                                                                             │
│  ◄──────────────────── Artifact Flow ────────────────────────────────────► │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Summary

| Phase | Purpose | Key Artifact | LLM Role | Typical Duration |
|-------|---------|--------------|----------|------------------|
| **Plan** | Analyze request, design solution | `plan.md` | Reasoning, decomposition | 30-60s |
| **Build** | Implement the code changes | `files_modified.json` | Code generation | 1-5min |
| **Verify** | Gather proof it works | `evidence/` | Determine what to capture | 30s-2min |
| **Validate** | Run automated checks | `test_results.json` | Interpret failures | 30s-2min |
| **Document** | Update docs and comments | `docs.md` | Technical writing | 30-60s |
| **Ship** | Deploy or create PR | `deploy_record.json` | PR description, release notes | 30s-2min |

---

## Phase 1: Plan

### Purpose

Analyze the feature request and produce a detailed implementation plan that guides the Build phase.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Feature request | `{{run.feature_request}}` | Original ask from user/webhook |
| Project context | `{{project.*}}` | Language, framework, conventions |
| Codebase context | `{{pre_hook_output}}` | File structure, recent changes |
| Conventions | `{{file:.agent/CONVENTIONS.md}}` | Project coding standards |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `plan.md` | Markdown | Human-readable implementation plan |
| `plan.json` | JSON | Structured plan for programmatic access |

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PLAN PHASE                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Map directory structure                                             ││
│  │   • Identify relevant files for the feature                             ││
│  │   • Gather recent commit context                                        ││
│  │   • Output: codebase summary for LLM                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION                                                           ││
│  │   • Analyze feature request                                             ││
│  │   • Break down into implementation steps                                ││
│  │   • Identify files to create/modify                                     ││
│  │   • Consider edge cases and error handling                              ││
│  │   • Estimate complexity                                                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Validate plan structure against schema                              ││
│  │   • Extract structured data to plan.json                                ││
│  │   • Verify referenced files exist (warnings only)                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Plan Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["summary", "steps", "files"],
  "properties": {
    "summary": {
      "type": "string",
      "description": "Brief description of the implementation approach"
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "description", "files"],
        "properties": {
          "id": { "type": "integer" },
          "description": { "type": "string" },
          "files": { 
            "type": "array", 
            "items": { "type": "string" } 
          },
          "dependencies": { 
            "type": "array", 
            "items": { "type": "integer" },
            "description": "IDs of steps that must complete first"
          }
        }
      }
    },
    "files": {
      "type": "object",
      "properties": {
        "create": { "type": "array", "items": { "type": "string" } },
        "modify": { "type": "array", "items": { "type": "string" } },
        "delete": { "type": "array", "items": { "type": "string" } }
      }
    },
    "complexity": {
      "type": "string",
      "enum": ["low", "medium", "high"]
    },
    "risks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": { "type": "string" },
          "mitigation": { "type": "string" }
        }
      }
    },
    "verification": {
      "type": "object",
      "description": "Hints for the Verify phase",
      "properties": {
        "screens_to_check": { "type": "array", "items": { "type": "string" } },
        "commands_to_run": { "type": "array", "items": { "type": "string" } },
        "endpoints_to_test": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

---

## Phase 2: Build

### Purpose

Implement the code changes described in the plan.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Implementation plan | `{{artifacts.plan}}` | Full plan.md content |
| Structured plan | `{{artifacts.plan_json}}` | Parsed plan.json |
| Conventions | `{{file:.agent/CONVENTIONS.md}}` | Coding standards |
| Pre-hook output | `{{pre_hook_output}}` | Branch info, current state |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `files_modified.json` | JSON | List of all files created/modified/deleted |
| `build_summary.md` | Markdown | Human-readable summary of changes |

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BUILD PHASE                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Create feature branch: feature/<run_id>                             ││
│  │   • Snapshot current file state (for diff later)                        ││
│  │   • Install dependencies if needed                                      ││
│  │   • Output: branch name, baseline commit                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION (Agentic)                                                 ││
│  │   • Read plan and execute step by step                                  ││
│  │   • Create new files                                                    ││
│  │   • Modify existing files                                               ││
│  │   • Run commands (install packages, etc.)                               ││
│  │   • Self-correct on errors                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Run code formatter (prettier, black, etc.)                          ││
│  │   • Run type checker                                                    ││
│  │   • Generate files_modified.json from git status                        ││
│  │   • Commit changes with structured message                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Files Modified Schema

```json
{
  "baseline_commit": "abc123",
  "build_commit": "def456",
  "branch": "feature/run_abc123",
  "files": {
    "created": [
      {
        "path": "src/auth/oauth-provider.ts",
        "lines": 248
      }
    ],
    "modified": [
      {
        "path": "src/app.ts",
        "lines_added": 15,
        "lines_removed": 3
      }
    ],
    "deleted": []
  },
  "commands_executed": [
    "npm install @auth/core"
  ],
  "summary": {
    "files_created": 3,
    "files_modified": 2,
    "files_deleted": 0,
    "total_lines_added": 412,
    "total_lines_removed": 8
  }
}
```

---

## Phase 3: Verify

### Purpose

Gather evidence that the implementation works as intended. This produces human-reviewable proof that the feature functions correctly, distinct from automated test results.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Plan | `{{artifacts.plan}}` | What was supposed to be built |
| Files modified | `{{artifacts.files_modified}}` | What was actually changed |
| Verification hints | `{{artifacts.plan_json.verification}}` | Screens/commands/endpoints to check |
| Platform config | `{{project.platform}}` | web, mobile, cli, backend, library |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `evidence_manifest.json` | JSON | Index of all captured evidence |
| `screenshots/` | Directory | Visual evidence (PNG/JPEG) |
| `terminal/` | Directory | CLI output captures |
| `api/` | Directory | API response captures |
| `recordings/` | Directory | Video/asciinema recordings |

### Platform-Specific Evidence Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLATFORM EVIDENCE MATRIX                                 │
│                                                                             │
│  ┌──────────────┬────────────────────────────────────────────────────────┐  │
│  │ Platform     │ Evidence Types                                         │  │
│  ├──────────────┼────────────────────────────────────────────────────────┤  │
│  │ web          │ • Screenshots of key routes                            │  │
│  │              │ • Browser console output                               │  │
│  │              │ • Network request/response                             │  │
│  │              │ • Video recording of user flow                         │  │
│  ├──────────────┼────────────────────────────────────────────────────────┤  │
│  │ mobile       │ • Simulator/emulator screenshots                       │  │
│  │              │ • Screen recordings                                    │  │
│  │              │ • Device logs                                          │  │
│  ├──────────────┼────────────────────────────────────────────────────────┤  │
│  │ cli          │ • Terminal output for key commands                     │  │
│  │              │ • Asciinema recordings                                 │  │
│  │              │ • Help text output                                     │  │
│  │              │ • Error handling demonstrations                        │  │
│  ├──────────────┼────────────────────────────────────────────────────────┤  │
│  │ backend      │ • curl/httpie request-response pairs                   │  │
│  │              │ • API response JSON                                    │  │
│  │              │ • Database state before/after                          │  │
│  │              │ • Log output                                           │  │
│  ├──────────────┼────────────────────────────────────────────────────────┤  │
│  │ library      │ • REPL session output                                  │  │
│  │              │ • Example code execution                               │  │
│  │              │ • Benchmark results                                    │  │
│  └──────────────┴────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             VERIFY PHASE                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Start application/service if needed                                 ││
│  │   • Wait for healthy state                                              ││
│  │   • Set up test data/fixtures                                           ││
│  │   • Launch browser/simulator if needed                                  ││
│  │   • Output: base URL, process IDs, health status                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION                                                           ││
│  │   • Analyze plan to determine what evidence to capture                  ││
│  │   • Execute evidence gathering based on platform:                       ││
│  │     - Web: Navigate and screenshot routes                               ││
│  │     - CLI: Run commands and capture output                              ││
│  │     - API: Make requests and capture responses                          ││
│  │   • Annotate evidence with descriptions                                 ││
│  │   • Map evidence back to plan steps                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Stop application/services                                           ││
│  │   • Clean up test data                                                  ││
│  │   • Optimize images (compress screenshots)                              ││
│  │   • Validate evidence_manifest.json                                     ││
│  │   • Generate evidence summary                                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Evidence Manifest Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["platform", "captured_at", "evidence"],
  "properties": {
    "platform": {
      "type": "string",
      "enum": ["web", "mobile", "cli", "backend", "library"]
    },
    "captured_at": {
      "type": "string",
      "format": "date-time"
    },
    "app_version": {
      "type": "string"
    },
    "environment": {
      "type": "object",
      "properties": {
        "os": { "type": "string" },
        "runtime": { "type": "string" },
        "browser": { "type": "string" }
      }
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "file", "description"],
        "properties": {
          "id": { 
            "type": "string",
            "description": "Unique identifier for this evidence item"
          },
          "type": { 
            "type": "string",
            "enum": ["screenshot", "terminal_output", "api_response", "video", "log", "repl_session"]
          },
          "file": { 
            "type": "string",
            "description": "Relative path within artifacts/verify/"
          },
          "description": { 
            "type": "string",
            "description": "What this evidence shows"
          },
          "validates_plan_step": { 
            "type": "integer",
            "description": "Which plan step this evidence supports"
          },
          "metadata": {
            "type": "object",
            "description": "Type-specific metadata",
            "properties": {
              "url": { "type": "string" },
              "command": { "type": "string" },
              "endpoint": { "type": "string" },
              "status_code": { "type": "integer" },
              "dimensions": { 
                "type": "object",
                "properties": {
                  "width": { "type": "integer" },
                  "height": { "type": "integer" }
                }
              },
              "duration_ms": { "type": "integer" }
            }
          }
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_items": { "type": "integer" },
        "plan_steps_covered": { 
          "type": "array", 
          "items": { "type": "integer" } 
        },
        "plan_steps_missing": { 
          "type": "array", 
          "items": { "type": "integer" } 
        },
        "notes": { "type": "string" }
      }
    }
  }
}
```

### Example Evidence Manifest

```json
{
  "platform": "web",
  "captured_at": "2024-01-15T10:30:00Z",
  "app_version": "1.2.0-feature-auth",
  "environment": {
    "os": "macOS 14.0",
    "runtime": "Node 20.10",
    "browser": "Chromium 120 (Playwright)"
  },
  "evidence": [
    {
      "id": "ev_001",
      "type": "screenshot",
      "file": "screenshots/01_login_page.png",
      "description": "Login page showing new Google OAuth button",
      "validates_plan_step": 1,
      "metadata": {
        "url": "http://localhost:3000/login",
        "dimensions": { "width": 1280, "height": 720 }
      }
    },
    {
      "id": "ev_002",
      "type": "screenshot",
      "file": "screenshots/02_oauth_redirect.png",
      "description": "Google OAuth consent screen",
      "validates_plan_step": 2,
      "metadata": {
        "url": "https://accounts.google.com/o/oauth2/..."
      }
    },
    {
      "id": "ev_003",
      "type": "screenshot",
      "file": "screenshots/03_dashboard_authenticated.png",
      "description": "Dashboard after successful OAuth login showing user info",
      "validates_plan_step": 3,
      "metadata": {
        "url": "http://localhost:3000/dashboard"
      }
    },
    {
      "id": "ev_004",
      "type": "api_response",
      "file": "api/user_profile.json",
      "description": "GET /api/me returns authenticated user data",
      "validates_plan_step": 3,
      "metadata": {
        "endpoint": "GET /api/me",
        "status_code": 200
      }
    }
  ],
  "summary": {
    "total_items": 4,
    "plan_steps_covered": [1, 2, 3],
    "plan_steps_missing": [],
    "notes": "All planned authentication flow steps verified"
  }
}
```

### Project Configuration for Evidence

```yaml
# .agent/project.yaml

platform: web

evidence:
  # Tool configuration
  screenshot_tool: playwright  # playwright | puppeteer | selenium
  
  # What to capture
  web:
    base_url: http://localhost:3000
    screenshots:
      viewport: { width: 1280, height: 720 }
      full_page: false
      routes:
        - path: /
          name: home
        - path: /login
          name: login
        - path: /dashboard
          auth_required: true
          name: dashboard
    
    # Optional: user flows to record
    flows:
      - name: login_flow
        steps:
          - goto: /login
          - click: "[data-testid=google-oauth]"
          - wait_for_url: /dashboard
  
  # For API evidence
  backend:
    base_url: http://localhost:3000/api
    endpoints:
      - method: POST
        path: /auth/login
        body_file: fixtures/login_request.json
      - method: GET
        path: /users/me
        auth_required: true
```

---

## Phase 4: Validate

### Purpose

Run automated checks (tests, linting, type checking) to verify code quality and correctness.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Files modified | `{{artifacts.files_modified}}` | What changed in Build |
| Test results (raw) | `{{pre_hook_output}}` | Output from test runner |
| Evidence | `{{artifacts.evidence}}` | Proof from Verify phase |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `test_results.json` | JSON | Structured test runner output |
| `lint_results.json` | JSON | Linter warnings/errors |
| `coverage_report.json` | JSON | Code coverage data |
| `type_check_results.json` | JSON | Type checker output |

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VALIDATE PHASE                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Run test suite: npm test / pytest / go test                         ││
│  │   • Run linter: eslint / ruff / golangci-lint                           ││
│  │   • Run type checker: tsc / mypy / pyright                              ││
│  │   • Collect coverage data                                               ││
│  │   • Output: raw results for LLM analysis                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION                                                           ││
│  │   • Analyze test failures                                               ││
│  │   • Categorize issues: bug vs flaky test vs environment                 ││
│  │   • Suggest fixes for failures                                          ││
│  │   • Optionally: implement fixes and re-run                              ││
│  │   • Generate human-readable summary                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Parse results into structured JSON                                  ││
│  │   • Check against quality gates (coverage threshold, etc.)              ││
│  │   • Exit non-zero if gates not met                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Test Results Schema

```json
{
  "runner": "jest",
  "timestamp": "2024-01-15T10:35:00Z",
  "duration_ms": 12450,
  "summary": {
    "total": 142,
    "passed": 140,
    "failed": 2,
    "skipped": 0,
    "pending": 0
  },
  "coverage": {
    "lines": 87.5,
    "branches": 82.3,
    "functions": 91.2,
    "statements": 87.8
  },
  "failures": [
    {
      "test": "OAuth flow > should handle token refresh",
      "file": "src/auth/__tests__/oauth.test.ts",
      "line": 45,
      "error": "Expected token to be refreshed but got 401",
      "stack": "...",
      "analysis": "Token refresh endpoint not implemented yet",
      "suggested_fix": "Implement /auth/refresh endpoint in oauth-provider.ts"
    }
  ],
  "quality_gates": {
    "coverage_threshold": { "required": 80, "actual": 87.5, "passed": true },
    "no_failures": { "required": true, "actual": false, "passed": false }
  }
}
```

---

## Phase 5: Document

### Purpose

Generate or update documentation for the implemented feature.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Plan | `{{artifacts.plan}}` | What was built |
| Files modified | `{{artifacts.files_modified}}` | What files changed |
| Evidence | `{{artifacts.evidence}}` | Visual proof |
| Test results | `{{artifacts.test_results}}` | Test coverage |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `docs.md` | Markdown | Generated documentation |
| `changelog_entry.md` | Markdown | Entry for CHANGELOG |
| `api_docs.json` | JSON | API documentation updates |

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DOCUMENT PHASE                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Identify existing docs to update                                    ││
│  │   • Extract JSDoc/docstrings from modified files                        ││
│  │   • Gather API schema changes                                           ││
│  │   • Output: existing docs context                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION                                                           ││
│  │   • Write feature documentation                                         ││
│  │   • Update README if needed                                             ││
│  │   • Generate changelog entry                                            ││
│  │   • Add inline code comments where helpful                              ││
│  │   • Update API documentation                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Validate markdown formatting                                        ││
│  │   • Check for broken links                                              ││
│  │   • Run documentation linter                                            ││
│  │   • Commit documentation changes                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Documentation Configuration

```yaml
# .agent/project.yaml

documentation:
  # What to generate
  generate:
    - feature_docs      # Standalone feature documentation
    - changelog_entry   # CHANGELOG.md entry
    - readme_update     # Update README if needed
    - api_docs          # API documentation
    - inline_comments   # Add code comments
  
  # Where to put docs
  output:
    feature_docs: docs/features/
    changelog: CHANGELOG.md
    api_docs: docs/api/
  
  # Style preferences
  style:
    include_screenshots: true
    include_code_examples: true
    max_heading_depth: 3
```

---

## Phase 6: Ship

### Purpose

Deploy the feature or create a pull request for review.

### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| All previous artifacts | `{{artifacts.*}}` | Complete context |
| Files modified | `{{artifacts.files_modified}}` | What to ship |
| Evidence | `{{artifacts.evidence}}` | Proof for PR description |
| Documentation | `{{artifacts.docs}}` | Generated docs |

### Outputs

| Artifact | Format | Description |
|----------|--------|-------------|
| `deploy_record.json` | JSON | Deployment metadata |
| `pr_description.md` | Markdown | Pull request body |
| `release_notes.md` | Markdown | Release notes |

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SHIP PHASE                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PRE-HOOK: pre.sh                                                        ││
│  │   • Ensure all changes committed                                        ││
│  │   • Push branch to remote                                               ││
│  │   • Check CI status (if applicable)                                     ││
│  │   • Output: branch URL, commit SHAs                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LLM EXECUTION                                                           ││
│  │   • Generate PR title and description                                   ││
│  │   • Include evidence screenshots in PR                                  ││
│  │   • Write release notes                                                 ││
│  │   • Suggest reviewers based on files changed                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST-HOOK: post.sh                                                      ││
│  │   • Create pull request via API                                         ││
│  │   • Add labels and reviewers                                            ││
│  │   • Upload evidence as PR attachments                                   ││
│  │   • Record deployment metadata                                          ││
│  │   • Notify external systems (Linear, Slack, etc.)                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ⚠️  APPROVAL GATE (if require_approval: true)                            ││
│  │   • Wait for human approval before creating PR                          ││
│  │   • In interactive mode: prompt in terminal                             ││
│  │   • In non-interactive: pause and wait for signal                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deploy Record Schema

```json
{
  "run_id": "run_abc123",
  "shipped_at": "2024-01-15T10:45:00Z",
  "method": "pull_request",
  "git": {
    "branch": "feature/run_abc123",
    "base_branch": "main",
    "commits": ["abc123", "def456", "ghi789"],
    "commit_range": "main..feature/run_abc123"
  },
  "pull_request": {
    "number": 142,
    "url": "https://github.com/org/repo/pull/142",
    "title": "Add OAuth authentication with Google",
    "reviewers": ["alice", "bob"],
    "labels": ["feature", "auth", "agent-generated"]
  },
  "artifacts_included": {
    "evidence_screenshots": 3,
    "documentation_files": 2
  },
  "external_updates": [
    {
      "system": "linear",
      "issue_id": "ENG-123",
      "action": "moved_to_done",
      "comment_added": true
    }
  ]
}
```

---

## Artifact Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ARTIFACT FLOW                                        │
│                                                                             │
│  PLAN ─────────────────────────────────────────────────────────────────────▶│
│  │ plan.md                                                                  │
│  │ plan.json                                                                │
│  │    │                                                                     │
│  │    ├──────────▶ BUILD                                                    │
│  │    │            │ files_modified.json                                    │
│  │    │            │ build_summary.md                                       │
│  │    │            │    │                                                   │
│  │    │            │    ├──────────▶ VERIFY                                 │
│  │    │◀───────────┘    │            │ evidence_manifest.json               │
│  │    │                 │            │ screenshots/                         │
│  │    │                 │            │ terminal/                            │
│  │    │                 │            │ api/                                 │
│  │    │                 │            │    │                                 │
│  │    │                 │            │    ├──────────▶ VALIDATE             │
│  │    │                 │◀───────────┘    │            │ test_results.json  │
│  │    │                 │                 │            │ lint_results.json  │
│  │    │                 │                 │            │ coverage.json      │
│  │    │                 │                 │            │    │               │
│  │    │                 │                 │            │    ├────▶ DOCUMENT │
│  │    │◀────────────────┼─────────────────┼────────────┘    │     │ docs.md │
│  │    │                 │                 │                 │     │ chlog.md│
│  │    │                 │                 │◀────────────────┘     │         │
│  │    │                 │                 │                       │         │
│  │    │                 │                 │                       ├──▶ SHIP │
│  │    │◀────────────────┼─────────────────┼───────────────────────┘         │
│  │                      │◀────────────────┼─────────────────────────────────│
│  │                                        │◀────────────────────────────────│
│  │                                                                          │
│  └──────────────────────────────────────────────────────────────────────────│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Artifact Availability by Phase

| Variable | Plan | Build | Verify | Validate | Document | Ship |
|----------|:----:|:-----:|:------:|:--------:|:--------:|:----:|
| `{{artifacts.plan}}` | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| `{{artifacts.plan_json}}` | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| `{{artifacts.files_modified}}` | — | — | ✓ | ✓ | ✓ | ✓ |
| `{{artifacts.evidence}}` | — | — | — | ✓ | ✓ | ✓ |
| `{{artifacts.test_results}}` | — | — | — | — | ✓ | ✓ |
| `{{artifacts.lint_results}}` | — | — | — | — | ✓ | ✓ |
| `{{artifacts.docs}}` | — | — | — | — | — | ✓ |

---

## Pipeline Control

### Running Specific Phases

```bash
# Full pipeline
agent run "Add feature"

# Single phase
agent run "Add feature" --phase plan
agent run "Add feature" --phase verify

# Phase range
agent run "Add feature" --start-from build --stop-after validate

# Multiple specific phases
agent run "Add feature" --phases plan,build,verify

# Skip verification (not recommended)
agent run "Add feature" --phases plan,build,validate,document,ship
```

### Resumption

```bash
# Resume from last successful phase
agent resume run_abc123

# Resume from specific phase
agent resume run_abc123 --from verify

# Retry failed phase
agent retry run_abc123 --phase validate
```

### Dry Run

```bash
# See what would happen without executing
agent run "Add feature" --dry-run
```

---

## Phase Configuration

Each phase can be configured in `config.yaml`:

```yaml
# commands/<phase>/config.yaml

# Execution limits
timeout_seconds: 300
max_retries: 2

# Human gates
require_approval: false

# LLM settings
llm:
  temperature: 0
  max_tokens: 16000

# Phase-specific settings (examples)

# For verify phase:
evidence:
  max_screenshots: 10
  video_enabled: false
  
# For validate phase:
quality_gates:
  coverage_threshold: 80
  allow_warnings: true
  
# For ship phase:
deployment:
  create_pr: true
  auto_merge: false
  required_reviewers: 1
```

---

## Error Handling

### Phase Failure Modes

| Error Type | Behavior | Recovery |
|------------|----------|----------|
| `pre_hook` failure | Phase fails immediately | Fix script, retry phase |
| `llm` timeout | Retry up to max_retries | Increase timeout, retry |
| `llm` error | Retry if transient | Check prompt, retry |
| `post_hook` failure | Phase fails | Fix script, retry phase |
| `validation` failure | Phase fails | Fix schema or output |
| `quality_gate` failure | Phase fails | Address issues, retry |

### Error Recovery Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ERROR RECOVERY                                        │
│                                                                             │
│  Phase fails                                                                │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐                                                        │
│  │ Checkpoint      │ Save current state to .agent/runs/<id>/context.json    │
│  │ State           │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ Log Error       │ Full context in logs/structured.jsonl                  │
│  │ Details         │ Human-readable in logs/raw.log                         │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │ Transient?      │─Yes─▶│ Auto-retry      │─Ok──▶│ Continue        │       │
│  │ (timeout, 5xx)  │     │ (up to limit)   │     │ Pipeline        │       │
│  └────────┬────────┘     └────────┬────────┘     └─────────────────┘       │
│           │ No                    │ Failed                                  │
│           ▼                       ▼                                         │
│  ┌─────────────────────────────────────────┐                               │
│  │ Pipeline Paused                          │                               │
│  │                                          │                               │
│  │ Options:                                 │                               │
│  │ • agent resume <run_id>                  │                               │
│  │ • agent retry <run_id> --phase <phase>   │                               │
│  │ • agent logs <run_id> (inspect)          │                               │
│  │ • Manual fix, then resume                │                               │
│  └─────────────────────────────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure After Run

```
.agent/
  runs/
    run_abc123/
      context.json                    # Run state (for resumption)
      
      artifacts/
        plan/
          plan.md                     # Implementation plan
          plan.json                   # Structured plan
          
        build/
          files_modified.json         # What changed
          build_summary.md            # Human-readable summary
          
        verify/
          evidence_manifest.json      # Index of evidence
          screenshots/
            01_login_page.png
            02_dashboard.png
          terminal/
            help_output.txt
          api/
            user_response.json
            
        validate/
          test_results.json           # Test runner output
          lint_results.json           # Linter output
          coverage_report.json        # Coverage data
          
        document/
          docs.md                     # Generated documentation
          changelog_entry.md          # Changelog addition
          
        ship/
          deploy_record.json          # Deployment metadata
          pr_description.md           # PR body
          
      logs/
        raw.log                       # Full text log
        structured.jsonl              # Machine-readable log
        
      snapshots/
        001_run_start.json
        002_plan_complete.json
        003_build_complete.json
        004_verify_complete.json
        005_validate_complete.json
        006_document_complete.json
        007_ship_complete.json
```

---

## Summary

| Phase | Input | Output | Key Responsibility |
|-------|-------|--------|-------------------|
| **Plan** | Feature request | `plan.md` | Design the solution |
| **Build** | Plan | `files_modified.json` | Write the code |
| **Verify** | Code + Plan | `evidence/` | Prove it works (visual) |
| **Validate** | Code | `test_results.json` | Prove it works (automated) |
| **Document** | All above | `docs.md` | Explain the feature |
| **Ship** | All above | `deploy_record.json` | Deliver to users |