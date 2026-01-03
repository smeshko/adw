# Epic 8: Evidence Gathering

**Goal:** Capture platform-appropriate evidence during the Verify phase based on project type (CLI, web, backend), generate evidence manifests, and optimize captured artifacts.

## Story 8.1: Detect Project Platform Type

As a developer,
I want the system to detect the project platform type,
So that appropriate evidence gathering strategies are used.

**Acceptance Criteria:**

**Given** project config with `platform: cli`
**When** evidence gathering starts
**Then** CLI evidence strategy is used

**Given** project config with `platform: web`
**When** evidence gathering starts
**Then** web screenshot strategy is used

**Given** project config with `platform: backend`
**When** evidence gathering starts
**Then** API capture strategy is used

**Given** no platform specified
**When** detection is attempted
**Then** it's inferred from project markers (e.g., package.json with react → web)

**Given** platform cannot be determined
**When** Verify phase runs
**Then** default CLI strategy is used with warning

---

## Story 8.2: Capture CLI Terminal Output

As a developer,
I want terminal output captured for CLI projects,
So that command execution can be verified.

**Acceptance Criteria:**

**Given** CLI platform type
**When** evidence gathering runs
**Then** configured commands are executed and output captured

**Given** commands from project.yaml `evidence.commands`
**When** each command executes
**Then** stdout and stderr are captured to `evidence/<cmd_name>.txt`

**Given** command output
**When** captured
**Then** it includes: command executed, exit code, duration, full output

**Given** command fails (non-zero exit)
**When** capturing
**Then** failure is recorded but doesn't fail the phase

**Given** evidence capture
**When** complete
**Then** exit codes are summarized (X passed, Y failed)

---

## Story 8.3: Capture Web Screenshots

As a developer,
I want screenshots captured for web projects,
So that UI changes can be visually verified.

**Acceptance Criteria:**

**Given** web platform type
**When** evidence gathering runs
**Then** configured routes are loaded and screenshotted

**Given** routes from project.yaml `evidence.routes`
**When** each route is captured
**Then** screenshot is saved to `evidence/screenshots/<route_name>.png`

**Given** screenshot capture
**When** browser automation runs
**Then** it uses headless Playwright or configured tool

**Given** route fails to load
**When** capturing
**Then** error screenshot is captured with error message

**Given** multiple viewport sizes configured
**When** capturing
**Then** screenshots at each viewport are generated

---

## Story 8.4: Capture API Request/Response Pairs

As a developer,
I want API interactions captured for backend projects,
So that endpoint behavior can be verified.

**Acceptance Criteria:**

**Given** backend platform type
**When** evidence gathering runs
**Then** configured API endpoints are called and responses captured

**Given** endpoints from project.yaml `evidence.endpoints`
**When** each endpoint is called
**Then** request and response are saved to `evidence/api/<endpoint_name>.json`

**Given** API call
**When** captured
**Then** it includes: method, url, headers, body, status_code, response_body, duration

**Given** endpoint returns error
**When** capturing
**Then** error response is captured for verification

**Given** authentication required
**When** capturing
**Then** auth headers from config or env vars are used

---

## Story 8.5: Generate Evidence Manifest

As a developer,
I want an evidence manifest linking evidence to plan steps,
So that verification is traceable.

**Acceptance Criteria:**

**Given** evidence gathering completes
**When** manifest is generated
**Then** it's saved to `evidence/manifest.json`

**Given** the manifest
**When** inspected
**Then** it includes: timestamp, platform, evidence_items list

**Given** each evidence item
**When** included in manifest
**Then** it references: plan_step (if linkable), path, type, status (pass/fail/error)

**Given** plan step references
**When** linking
**Then** step IDs from plan.md are matched to evidence items

**Given** manifest
**When** processed by Validate phase
**Then** it's used to assess verification coverage

---

## Story 8.6: Compress and Optimize Evidence

As a developer,
I want captured evidence compressed,
So that storage and transfer are efficient.

**Acceptance Criteria:**

**Given** evidence directory with screenshots
**When** optimization runs
**Then** images are compressed (lossy acceptable for screenshots)

**Given** large terminal outputs
**When** optimization runs
**Then** they're truncated or summarized if over threshold

**Given** all evidence
**When** run completes
**Then** total size is logged for monitoring

**Given** evidence optimization
**When** configured
**Then** max sizes are respected per file type

---

## Epic 8: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [8.1] Detect Project Platform Type                                          ║
║        Foundation for all evidence strategies                                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 8.1 (PARALLEL x3)                                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [8.2] CLI Capture    ║    [8.3] Web Screenshots    ║    [8.4] API Capture   ║
║  Terminal output      ║    Playwright-based         ║    curl/httpx          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 8.1, 8.2, 8.3, 8.4                                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [8.5] Generate Evidence Manifest                                             ║
║        Links evidence items to plan steps, calculates coverage                ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 8.2, 8.3, 8.4, 8.5                                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [8.6] Compress and Optimize Evidence                                         ║
║        Image compression, text truncation, size monitoring                    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Wave Summary

| Wave | Stories | Description |
|------|---------|-------------|
| 1 | 8.1 | Platform detection (foundation) |
| 2 | 8.2, 8.3, 8.4 | Evidence capture strategies (parallelizable) |
| 3 | 8.5 | Manifest generation |
| 4 | 8.6 | Optimization |

### Parallelization Opportunities

**Wave 2** offers significant parallelization: Stories 8.2, 8.3, and 8.4 can all be developed simultaneously by different developers or in parallel agent sessions after Story 8.1 completes.

---
