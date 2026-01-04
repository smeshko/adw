# Story 8.4: Capture API Request/Response Pairs

Status: ready-for-dev
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-03

---

## Story

As a developer,
I want API interactions captured for backend projects,
so that endpoint behavior can be verified.

## Acceptance Criteria

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

## Tasks / Subtasks

### Task 1: Create API Evidence Models (models/evidence.py)
- [x] Create `EndpointConfig` model for endpoint configuration
- [x] Create `APIRequest` model with method, url, headers, body
- [x] Create `APIResponse` model with status_code, headers, body, duration
- [x] Create `APIEvidenceResult` model combining request + response
- [x] Create `APIEvidenceSummary` model for aggregate results
- [x] Export from `models/__init__.py`

### Task 2: Implement HTTP Client Wrapper (evidence/api_capture.py)
- [x] Create `APICaptureStrategy` class
- [x] Use `httpx` or `subprocess` + `curl` for requests
- [x] Implement `call_endpoint(config: EndpointConfig) -> APIEvidenceResult`
- [x] Support all HTTP methods (GET, POST, PUT, DELETE, PATCH)
- [x] Handle timeouts gracefully

### Task 3: Implement Request/Response Capture
- [x] Capture full request details (method, url, headers, body)
- [x] Capture full response details (status, headers, body, timing)
- [x] Preserve response body as JSON when possible, raw string otherwise
- [x] Calculate request duration

### Task 4: Implement Authentication Support
- [x] Support Bearer token authentication
- [x] Support API key headers
- [x] Read auth from config or environment variables
- [x] Support auth config format:
  ```yaml
  evidence:
    auth:
      type: "bearer"
      token_env: "API_TOKEN"
    # or
    auth:
      type: "api_key"
      header: "X-API-Key"
      key_env: "API_KEY"
  ```

### Task 5: Implement Config-Based Endpoint Loading
- [ ] Read `evidence.endpoints` from `.adw/project.yaml`
- [ ] Support endpoint configuration format:
  ```yaml
  evidence:
    base_url: "http://localhost:8000"
    endpoints:
      - name: "health"
        method: "GET"
        path: "/health"
      - name: "create_user"
        method: "POST"
        path: "/users"
        body:
          name: "test"
          email: "test@example.com"
        expected_status: 201
      - name: "get_users"
        method: "GET"
        path: "/users"
        headers:
          Accept: "application/json"
  ```
- [ ] Validate configuration
- [ ] Handle missing config (skip with warning)

### Task 6: Implement Evidence File Writer
- [ ] Create directory: `.adw/runs/<run_id>/evidence/api/`
- [ ] Write individual API results to `<endpoint_name>.json`
- [ ] Include complete request/response details
- [ ] Generate summary file with all results

### Task 7: Implement Summary Generation
- [ ] Track successful/failed API calls
- [ ] Track expected vs actual status codes
- [ ] Generate summary output
- [ ] Log summary to console via LogManager

### Task 8: Write Unit Tests
- [ ] Test endpoint configuration loading
- [ ] Test HTTP method support (mock responses)
- [ ] Test authentication header injection
- [ ] Test error response handling
- [ ] Test evidence file writing
- [ ] Test summary generation
- [ ] Test timeout handling

---

## Relevant Feature Documentation

**From Architecture (Evidence Gathering MVP):**
> MVP Scope:
> - API responses via subprocess calls to `curl`
> - JSON response storage in `artifacts/verify/api/`

This aligns with MVP scope - API capture is explicitly supported.

---

## Developer Context

### Technical Requirements

**From PRD FR13-FR18 (Verify Phase):**
- FR17: Backend projects capture API responses
- FR14: Evidence stored in run artifacts directory
- FR18: Evidence failure doesn't fail the phase

**From Architecture (Evidence Gathering MVP):**
> - API responses via subprocess calls to `curl`
> - JSON response storage in `artifacts/verify/api/`

**From Epic 8.4 Acceptance Criteria:**
- Endpoints defined in `evidence.endpoints` config
- Capture includes: method, url, headers, body, status_code, response_body, duration
- Authentication support (env vars or config)
- Error responses captured for verification

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create/Modify:**
```
src/adw/evidence/
├── __init__.py          # Package exports (update)
├── detector.py          # From Story 8.1
├── cli_capture.py       # From Story 8.2
├── web_capture.py       # From Story 8.3
├── api_capture.py       # API capture (NEW)
└── strategies/
    ├── __init__.py
    ├── cli.py
    ├── web.py
    └── api.py           # APICaptureStrategy (NEW)

src/adw/models/
└── evidence.py          # Add API-specific models (MODIFY)
```

**Evidence Output Structure:**
```
.adw/runs/<run_id>/
└── evidence/
    └── api/
        ├── health.json
        ├── create_user.json
        ├── get_users.json
        └── summary.json
```

**Dependencies:**
- subprocess + curl (for MVP approach)
- OR httpx (cleaner Python-native option)
- Pydantic for models (already installed)
- PyYAML for config loading (already installed)

**Integration Points:**
- Uses `PlatformDetector` from Story 8.1
- Results used by Story 8.5 (manifest generation)
- Results compressed by Story 8.6

### Library & Framework Requirements

**Option A: subprocess + curl (MVP approach per architecture):**
```python
import subprocess
import json
from datetime import datetime

def call_endpoint_curl(
    method: str,
    url: str,
    headers: dict | None = None,
    body: dict | None = None,
    timeout: int = 30,
) -> APIEvidenceResult:
    cmd = ["curl", "-s", "-w", "\n%{http_code}\n%{time_total}", "-X", method]

    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])

    if body:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["-d", json.dumps(body)])

    cmd.append(url)

    start = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    duration = (datetime.now() - start).total_seconds()

    # Parse curl output (body, status_code, time)
    lines = result.stdout.strip().split("\n")
    response_body = "\n".join(lines[:-2])
    status_code = int(lines[-2])
    curl_time = float(lines[-1])

    return APIEvidenceResult(
        request=APIRequest(method=method, url=url, headers=headers, body=body),
        response=APIResponse(status_code=status_code, body=response_body, duration=curl_time),
        success=200 <= status_code < 300,
    )
```

**Option B: httpx (cleaner alternative):**
```python
import httpx
from datetime import datetime

def call_endpoint_httpx(
    method: str,
    url: str,
    headers: dict | None = None,
    body: dict | None = None,
    timeout: int = 30,
) -> APIEvidenceResult:
    start = datetime.now()

    with httpx.Client(timeout=timeout) as client:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
        )

    duration = (datetime.now() - start).total_seconds()

    return APIEvidenceResult(
        request=APIRequest(method=method, url=url, headers=headers, body=body),
        response=APIResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.text,
            duration=duration,
        ),
        success=response.is_success,
    )
```

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class EndpointConfig(BaseModel):
    name: str
    method: str = "GET"
    path: str
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None
    expected_status: int | None = None
    timeout_seconds: int = 30

class AuthConfig(BaseModel):
    type: str  # "bearer", "api_key", "basic"
    token_env: str | None = None  # For bearer
    header: str | None = None     # For api_key
    key_env: str | None = None    # For api_key

class APIRequest(BaseModel):
    method: str
    url: str
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None

class APIResponse(BaseModel):
    status_code: int
    headers: dict[str, str] | None = None
    body: str | dict[str, Any]
    duration_seconds: float

class APIEvidenceResult(BaseModel):
    endpoint_name: str
    request: APIRequest
    response: APIResponse
    success: bool
    expected_status: int | None = None
    status_match: bool = True
    error: str | None = None
    captured_at: datetime = Field(default_factory=datetime.now)

class APIEvidenceSummary(BaseModel):
    base_url: str
    total_endpoints: int
    successful: int
    failed: int
    status_mismatches: int
    results: list[APIEvidenceResult]
```

### File Structure Requirements

**Evidence File Format (<endpoint_name>.json):**
```json
{
  "endpoint_name": "create_user",
  "captured_at": "2026-01-03T10:30:45Z",
  "request": {
    "method": "POST",
    "url": "http://localhost:8000/users",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer [REDACTED]"
    },
    "body": {
      "name": "test",
      "email": "test@example.com"
    }
  },
  "response": {
    "status_code": 201,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "id": 123,
      "name": "test",
      "email": "test@example.com"
    },
    "duration_seconds": 0.045
  },
  "success": true,
  "expected_status": 201,
  "status_match": true
}
```

**Summary File Format (summary.json):**
```json
{
  "captured_at": "2026-01-03T10:30:45Z",
  "platform": "backend",
  "base_url": "http://localhost:8000",
  "total_endpoints": 5,
  "successful": 4,
  "failed": 1,
  "status_mismatches": 0,
  "results": [
    {
      "endpoint_name": "health",
      "method": "GET",
      "path": "/health",
      "status_code": 200,
      "duration_seconds": 0.012,
      "success": true
    }
  ]
}
```

### Testing Requirements

**Test File Structure:**
```
tests/unit/evidence/
├── __init__.py
├── test_detector.py
├── test_cli_capture.py
├── test_web_capture.py
├── test_api_capture.py    # API capture tests (NEW)
└── fixtures/
    ├── cli_configs/
    ├── web_configs/
    └── api_configs/       # Test config files (NEW)
```

**Testing Patterns:**
- Mock HTTP responses (httpx.MockTransport or responses library)
- Test each HTTP method (GET, POST, PUT, DELETE, PATCH)
- Test authentication injection
- Test error response handling
- Use `tmp_path` for evidence output
- Test timeout handling

**Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 8.1 (Platform Detection):**
- `PlatformDetector` determines when API strategy is used
- Check for `PlatformType.BACKEND` before executing

**From Story 8.2 (CLI Capture):**
- Similar pattern for evidence capture strategy
- Use same summary/result model patterns
- Error handling approach (capture failure, don't fail phase)

**From Epic 7 (Observability & Logging):**
- Use LogManager for execution logging
- IMPORTANT: Redact auth tokens in logs (Story 7.6 patterns)
- Log each endpoint call with structured context

---

## Git Intelligence

Recent commits show patterns for:
- subprocess execution with capture
- Pydantic model creation in `models/`
- JSON file writing with atomic operations

---

## Latest Technical Information

**httpx 0.27+ (if used):**
```python
import httpx

# Sync client (simpler for evidence capture)
with httpx.Client(timeout=30.0) as client:
    response = client.get("http://localhost:8000/health")
    response.raise_for_status()

# Async available for parallel capture
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

**curl Write-Out Format:**
```bash
curl -w '\n%{http_code}\n%{time_total}\n%{size_download}' -s URL
# Returns:
# <response body>
# 200
# 0.123
# 1234
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required
- NEVER log secrets - redact auth tokens
- Context managers for HTTP clients

---

## Dev Notes

- MVP uses curl subprocess per architecture decision
- Consider httpx for cleaner Python-native implementation
- Auth tokens must be redacted in logs and evidence files
- Response bodies may be large - Story 8.6 will handle size
- Error responses are valid evidence (capture, don't fail)

### Project Structure Notes

- Add `api_capture.py` to `evidence/` package
- Update `evidence.py` models with API-specific types
- Evidence output goes to run directory under `evidence/api/`
- Consider adding `[http]` optional dependency group for httpx

### References

- [Source: _bmad-output/architecture.md#Evidence-Gathering-MVP] - MVP scope (curl approach)
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md#Story-8.4] - Story definition
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: src/adw/logging/] - Secret redaction patterns

---

## Dependencies

- **Depends On:** Story 8.1 (Platform Detection)
- **Blocks:** Story 8.5, Story 8.6
- **Can Parallel With:** Story 8.2, Story 8.3

### Dependency Rationale
- Requires platform detection (8.1) to know when to use API strategy
- Produces evidence files consumed by manifest (8.5) and compression (8.6)
- Can be developed in parallel with CLI capture (8.2) and web screenshots (8.3)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

