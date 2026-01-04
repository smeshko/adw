# Story 8.3: Capture Web Screenshots

Status: done
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-03

---

## Story

As a developer,
I want screenshots captured for web projects,
so that UI changes can be visually verified.

## Acceptance Criteria

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

## Tasks / Subtasks

### Task 1: Create Web Screenshot Models (models/evidence.py)
- [x] Create `RouteConfig` model for route configuration
- [x] Create `ViewportConfig` model for viewport sizes
- [x] Create `ScreenshotResult` model with path, route, viewport, status
- [x] Create `WebEvidenceSummary` model for aggregate results
- [x] Export from `models/__init__.py`

### Task 2: Implement Playwright Integration (evidence/web_capture.py)
- [x] Create `WebCaptureStrategy` class
- [x] Implement optional Playwright dependency check
- [x] Create browser context with headless mode
- [x] Implement graceful degradation if Playwright not installed

### Task 3: Implement Route Screenshot Capture
- [x] Implement `capture_route(route: RouteConfig) -> ScreenshotResult`
- [x] Navigate to route URL
- [x] Wait for page load (configurable timeout)
- [x] Take full-page screenshot
- [x] Handle navigation errors gracefully

### Task 4: Implement Viewport Support
- [x] Support multiple viewport configurations
- [x] Default viewports: desktop (1920x1080), tablet (768x1024), mobile (375x667)
- [x] Generate separate screenshots per viewport
- [x] Name files with viewport suffix: `home_desktop.png`, `home_mobile.png`

### Task 5: Implement Error Screenshot Capture
- [x] On navigation failure, capture current state
- [x] Include error message overlay or metadata
- [x] Save error screenshots with `_error` suffix
- [x] Record error details in result model

### Task 6: Implement Config-Based Route Loading
- [x] Read `evidence.routes` from `.adw/project.yaml`
- [x] Support route configuration format:
  ```yaml
  evidence:
    base_url: "http://localhost:3000"
    routes:
      - name: "home"
        path: "/"
        wait_for: "networkidle"
      - name: "dashboard"
        path: "/dashboard"
        wait_for: "load"
    viewports:
      - name: "desktop"
        width: 1920
        height: 1080
      - name: "mobile"
        width: 375
        height: 667
  ```
- [x] Validate configuration
- [x] Handle missing config (skip with warning)

### Task 7: Implement Evidence File Organization
- [x] Create directory: `.adw/runs/<run_id>/evidence/screenshots/`
- [x] Save screenshots as PNG
- [x] Generate metadata JSON alongside screenshots
- [x] Handle filename sanitization for routes

### Task 8: Write Unit Tests
- [x] Test Playwright availability check
- [x] Test route configuration loading
- [x] Test viewport configuration
- [x] Test screenshot path generation
- [x] Test error handling (mock Playwright)
- [x] Test result model serialization

---

## Relevant Feature Documentation

**From Architecture (Evidence Gathering):**
> Deferred: Web screenshots (Playwright), mobile screenshots, video recording.

**Note:** This story implements web screenshots as a post-MVP enhancement. The architecture marks it as deferred, but the epic includes it for comprehensive evidence gathering.

---

## Developer Context

### Technical Requirements

**From PRD FR13-FR18 (Verify Phase):**
- FR16: Web projects capture screenshots for visual verification
- FR14: Evidence stored in run artifacts directory
- FR18: Evidence failure doesn't fail the phase

**From Epic 8.3 Acceptance Criteria:**
- Routes defined in `evidence.routes` config
- Headless Playwright (or configured tool)
- Error screenshots on failure
- Multiple viewport support

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create/Modify:**
```
src/adw/evidence/
├── __init__.py          # Package exports (update)
├── detector.py          # From Story 8.1
├── cli_capture.py       # From Story 8.2
├── web_capture.py       # Web screenshot capture (NEW)
└── strategies/
    ├── __init__.py
    ├── cli.py           # From Story 8.2
    └── web.py           # WebCaptureStrategy (NEW)

src/adw/models/
└── evidence.py          # Add web-specific models (MODIFY)
```

**Evidence Output Structure:**
```
.adw/runs/<run_id>/
└── evidence/
    └── screenshots/
        ├── home_desktop.png
        ├── home_mobile.png
        ├── dashboard_desktop.png
        ├── dashboard_mobile.png
        ├── metadata.json      # Screenshot metadata
        └── summary.json       # Aggregate results
```

**Dependencies:**
- Playwright (optional) - `pip install playwright`
- Pydantic for models (already installed)
- PyYAML for config loading (already installed)

**Integration Points:**
- Uses `PlatformDetector` from Story 8.1
- Results used by Story 8.5 (manifest generation)
- Results compressed by Story 8.6

### Library & Framework Requirements

**Playwright Integration:**
```python
# Optional import with graceful fallback
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def check_playwright_available() -> bool:
    """Check if Playwright is installed and browsers available."""
    if not PLAYWRIGHT_AVAILABLE:
        return False
    try:
        with sync_playwright() as p:
            # Quick check - just verify we can start
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
    except Exception:
        return False
```

**Screenshot Capture:**
```python
from playwright.sync_api import sync_playwright

def capture_screenshot(
    url: str,
    output_path: Path,
    viewport: tuple[int, int] = (1920, 1080),
    timeout: int = 30000,
) -> ScreenshotResult:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()

        try:
            page.goto(url, timeout=timeout, wait_until="networkidle")
            page.screenshot(path=str(output_path), full_page=True)
            return ScreenshotResult(
                path=output_path,
                route=url,
                viewport=f"{viewport[0]}x{viewport[1]}",
                success=True,
            )
        except PlaywrightTimeout:
            # Capture error state
            page.screenshot(path=str(output_path.with_suffix(".error.png")))
            return ScreenshotResult(
                path=output_path,
                route=url,
                viewport=f"{viewport[0]}x{viewport[1]}",
                success=False,
                error="Timeout waiting for page load",
            )
        finally:
            browser.close()
```

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from pathlib import Path

class ViewportConfig(BaseModel):
    name: str
    width: int
    height: int

class RouteConfig(BaseModel):
    name: str
    path: str
    wait_for: str = "networkidle"  # load, domcontentloaded, networkidle
    timeout_ms: int = 30000

class ScreenshotResult(BaseModel):
    path: Path
    route: str
    viewport: str
    success: bool
    error: str | None = None
    captured_at: datetime = Field(default_factory=datetime.now)

class WebEvidenceSummary(BaseModel):
    base_url: str
    total_screenshots: int
    successful: int
    failed: int
    results: list[ScreenshotResult]
```

### File Structure Requirements

**Screenshot Naming Convention:**
```
<route_name>_<viewport_name>.png
```
Examples:
- `home_desktop.png`
- `home_mobile.png`
- `dashboard_desktop.png`
- `login_error_desktop.png` (for failed captures)

**Metadata File Format (metadata.json):**
```json
{
  "captured_at": "2026-01-03T10:30:45Z",
  "base_url": "http://localhost:3000",
  "viewports": ["desktop", "mobile"],
  "screenshots": [
    {
      "route": "home",
      "path": "/",
      "files": {
        "desktop": "home_desktop.png",
        "mobile": "home_mobile.png"
      },
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
├── test_web_capture.py    # Web capture tests (NEW)
└── fixtures/
    ├── cli_configs/
    └── web_configs/       # Test config files (NEW)
```

**Testing Patterns:**
- Mock Playwright for unit tests (don't require browser)
- Test graceful degradation when Playwright not installed
- Test configuration validation
- Use `tmp_path` for screenshot output
- Test error handling paths

**Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 8.1 (Platform Detection):**
- `PlatformDetector` determines when web strategy is used
- Platform type stored in RunContext
- Check for `PlatformType.WEB` before executing

**From Story 8.2 (CLI Capture):**
- Similar pattern for evidence capture strategy
- Use same summary/result model patterns
- Error handling approach (capture failure, don't fail phase)

---

## Git Intelligence

Recent commits show patterns for:
- Optional dependency handling with try/import
- Pydantic model creation in `models/`
- Graceful degradation for missing tools

---

## Latest Technical Information

**Playwright 1.40+ (Latest):**
```python
# Modern page.screenshot options
page.screenshot(
    path="screenshot.png",
    full_page=True,           # Capture full scrollable area
    type="png",               # or "jpeg"
    animations="disabled",    # Disable CSS animations
)

# Wait strategies
page.goto(url, wait_until="networkidle")  # Wait for network idle
page.wait_for_load_state("domcontentloaded")  # DOM ready
page.wait_for_selector(".loaded")  # Custom selector
```

**Playwright Installation:**
```bash
# Install Python package
uv add --optional playwright

# Install browser binaries
python -m playwright install chromium
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required
- Context managers for browser resources
- Graceful error handling

---

## Dev Notes

- Playwright is an OPTIONAL dependency (not required for MVP)
- Gracefully skip if Playwright not installed (warning, not error)
- Consider async implementation for parallel screenshot capture
- Browser context should be reused across routes for efficiency
- Full-page screenshots may be large - Story 8.6 will compress

### Project Structure Notes

- Add `web_capture.py` to `evidence/` package
- Update `evidence.py` models with web-specific types
- Evidence output goes to run directory under `evidence/screenshots/`
- Consider adding `[web]` optional dependency group in pyproject.toml

### References

- [Source: _bmad-output/architecture.md#Evidence-Gathering-MVP] - Deferred scope note
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md#Story-8.3] - Story definition
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: https://playwright.dev/python/docs/screenshots] - Playwright docs

---

## Dependencies

- **Depends On:** Story 8.1 (Platform Detection)
- **Blocks:** Story 8.5, Story 8.6
- **Can Parallel With:** Story 8.2, Story 8.4

### Dependency Rationale
- Requires platform detection (8.1) to know when to use web strategy
- Produces evidence files consumed by manifest (8.5) and compression (8.6)
- Can be developed in parallel with CLI capture (8.2) and API capture (8.4)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created web screenshot models (ViewportConfig, RouteConfig, ScreenshotResult, WebEvidenceSummary) in models/evidence.py with full Pydantic validation, field validators for path conversion, and proper model configuration. Added comprehensive tests for all new models.

### File List

**Created:**
- `src/adw/evidence/web_capture.py` - WebCaptureStrategy and helper functions for Playwright screenshot capture
- `tests/unit/evidence/test_web_capture.py` - Unit tests for web capture functionality (37 tests)

**Modified:**
- `src/adw/models/evidence.py` - Added RouteConfig, ViewportConfig, ScreenshotResult, WebEvidenceSummary models
- `src/adw/models/__init__.py` - Export new evidence models
- `src/adw/evidence/__init__.py` - Export WebCaptureStrategy and helpers
- `tests/unit/models/test_evidence.py` - Added tests for new evidence models (43 tests)

