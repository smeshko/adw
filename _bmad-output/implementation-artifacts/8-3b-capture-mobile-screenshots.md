# Story 8.3b: Capture Mobile Screenshots

Status: ready-for-dev
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-04

---

## Story

As a developer,
I want screenshots captured from iOS simulators and Android emulators,
so that mobile UI changes can be visually verified.

## Acceptance Criteria

**Given** mobile platform type (iOS native)
**When** evidence gathering runs
**Then** iOS Simulator screenshots are captured via `xcrun simctl io booted screenshot`

**Given** mobile platform type (Android native)
**When** evidence gathering runs
**Then** Android Emulator screenshots are captured via `adb exec-out screencap`

**Given** mobile platform type (Flutter)
**When** evidence gathering runs
**Then** screenshots are captured from the active simulator/emulator (iOS or Android)

**Given** configured screens in project.yaml `evidence.mobile_screens`
**When** each screen is captured
**Then** screenshot is saved to `evidence/screenshots/mobile/<screen_name>.png`

**Given** navigation to feature screen required
**When** no deeplink is available
**Then** system navigates to screen via configured steps before capture

**Given** no simulator or emulator is running
**When** capture is attempted
**Then** capture fails gracefully with warning (does not fail the phase)

**Given** screenshot capture
**When** successful
**Then** it includes metadata: device_type, os_version, screen_name, timestamp

## Tasks / Subtasks

### Task 1: Create Mobile Screenshot Models (models/evidence.py)
- [x] Create `MobileDeviceType` enum (IOS, ANDROID, FLUTTER)
- [x] Create `MobileScreenConfig` model for screen configuration
- [x] Create `MobileScreenshotResult` model with path, screen_name, device_type, status
- [x] Create `MobileEvidenceSummary` model for aggregate results
- [x] Export from `models/__init__.py`

### Task 2: Implement iOS Simulator Screenshot Capture (evidence/mobile_capture.py)
- [ ] Create `MobileCaptureStrategy` class
- [ ] Implement `check_ios_simulator_available() -> bool`
- [ ] Implement `get_booted_simulator() -> str | None` (returns UDID)
- [ ] Implement `capture_ios_screenshot(output_path: Path) -> MobileScreenshotResult`
- [ ] Use `xcrun simctl io booted screenshot <path>` for capture
- [ ] Extract device info via `xcrun simctl list devices booted --json`

### Task 3: Implement Android Emulator Screenshot Capture
- [ ] Implement `check_android_emulator_available() -> bool`
- [ ] Implement `get_running_emulator() -> str | None` (returns device serial)
- [ ] Implement `capture_android_screenshot(output_path: Path) -> MobileScreenshotResult`
- [ ] Use `adb exec-out screencap -p > <path>` for capture
- [ ] Extract device info via `adb shell getprop`

### Task 4: Implement Flutter Cross-Platform Support
- [ ] Detect active Flutter device (iOS simulator or Android emulator)
- [ ] Use `flutter devices --machine` for device detection
- [ ] Route to appropriate iOS or Android capture method
- [ ] Handle hybrid projects with both simulators

### Task 5: Implement Screen Navigation (Optional Feature)
- [ ] Support `navigation_steps` in screen config for complex navigation
- [ ] Implement basic tap/swipe commands via xcrun/adb
- [ ] Implement deeplink navigation for supported screens
- [ ] Add configurable wait time between navigation and capture

### Task 6: Implement Config-Based Screen Loading
- [ ] Read `evidence.mobile_screens` from `.adw/project.yaml`
- [ ] Support screen configuration format:
  ```yaml
  evidence:
    mobile_screens:
      - name: "home"
        deeplink: "myapp://home"
        capture_delay_ms: 500
      - name: "profile"
        deeplink: "myapp://profile/123"
      - name: "settings"
        navigation_steps:
          - type: "tap"
            selector: "Settings Button"
  ```
- [ ] Validate configuration
- [ ] Handle missing config (capture current screen with warning)

### Task 7: Implement Evidence File Organization
- [ ] Create directory: `.adw/runs/<run_id>/evidence/screenshots/mobile/`
- [ ] Save screenshots as PNG
- [ ] Generate metadata JSON with device info, timestamps
- [ ] Handle filename sanitization for screen names

### Task 8: Write Unit Tests
- [ ] Test iOS simulator availability check (mock subprocess)
- [ ] Test Android emulator availability check (mock subprocess)
- [ ] Test screenshot path generation
- [ ] Test configuration loading and validation
- [ ] Test error handling for unavailable devices
- [ ] Test result model serialization

---

## Relevant Feature Documentation

**From Epic 8.3b Acceptance Criteria:**
- iOS screenshots via `xcrun simctl io booted screenshot`
- Android screenshots via `adb exec-out screencap`
- Configurable screens in `evidence.mobile_screens`
- Graceful failure when no simulator/emulator running
- Metadata includes: device_type, os_version, screen_name, timestamp

---

## Developer Context

### Technical Requirements

**From PRD FR13-FR18 (Verify Phase):**
- FR17: Mobile projects capture device/simulator screenshots
- FR14: Evidence stored in run artifacts directory
- FR18: Evidence failure doesn't fail the phase

**From Epic 8.3b Acceptance Criteria:**
- iOS Simulator: `xcrun simctl io booted screenshot`
- Android Emulator: `adb exec-out screencap -p`
- Flutter: Detect which platform, route to appropriate capture
- Graceful degradation when no device available

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create/Modify:**
```
src/adw/evidence/
├── __init__.py          # Package exports (MODIFY - add mobile exports)
├── detector.py          # From Story 8.1 (NO CHANGES)
├── mobile_capture.py    # Mobile screenshot capture (NEW)
└── strategies/          # Optional: if using strategy pattern
    ├── __init__.py
    └── mobile.py        # MobileCaptureStrategy (NEW)

src/adw/models/
└── evidence.py          # Add mobile-specific models (MODIFY)
```

**Evidence Output Structure:**
```
.adw/runs/<run_id>/
└── evidence/
    └── screenshots/
        └── mobile/
            ├── home_ios.png
            ├── home_android.png
            ├── profile_ios.png
            ├── metadata.json      # Device and capture metadata
            └── summary.json       # Aggregate results
```

**Integration Points:**
- Uses `PlatformDetector` from Story 8.1 (checks for `PlatformType.MOBILE`)
- Uses same pattern as Story 8.3 (web screenshots) for consistency
- Results used by Story 8.5 (manifest generation)
- Results compressed by Story 8.6

### Library & Framework Requirements

**iOS Simulator Commands:**
```bash
# Check for booted simulator
xcrun simctl list devices booted --json

# Capture screenshot
xcrun simctl io booted screenshot /path/to/output.png

# Get device info
xcrun simctl list devices booted --json | jq '.devices | to_entries[] | .value[] | select(.state == "Booted")'
```

**Android Emulator Commands:**
```bash
# Check for running emulator
adb devices

# Capture screenshot (binary output, redirect to file)
adb exec-out screencap -p > /path/to/output.png

# Get device properties
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
```

**Flutter Device Detection:**
```bash
# List devices in machine-readable format
flutter devices --machine

# Example output:
# [{"name":"iPhone 15","id":"UDID","platform":"ios"},{"name":"sdk_gphone64","id":"emulator-5554","platform":"android"}]
```

**Python Implementation Patterns:**
```python
import subprocess
import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field


class MobileDeviceType(str, Enum):
    """Type of mobile device for evidence gathering."""
    IOS = "ios"
    ANDROID = "android"
    FLUTTER_IOS = "flutter_ios"
    FLUTTER_ANDROID = "flutter_android"


class MobileScreenshotResult(BaseModel):
    """Result of a mobile screenshot capture."""
    path: Path
    screen_name: str
    device_type: MobileDeviceType
    device_name: str | None = None
    os_version: str | None = None
    success: bool
    error: str | None = None
    captured_at: datetime = Field(default_factory=datetime.now)


def check_ios_simulator_available() -> bool:
    """Check if an iOS Simulator is booted and available."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        # Check if any device is booted
        for runtime, devices in data.get("devices", {}).items():
            if any(d.get("state") == "Booted" for d in devices):
                return True
        return False
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return False


def capture_ios_screenshot(output_path: Path, screen_name: str) -> MobileScreenshotResult:
    """Capture screenshot from booted iOS Simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "io", "booted", "screenshot", str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return MobileScreenshotResult(
                path=output_path,
                screen_name=screen_name,
                device_type=MobileDeviceType.IOS,
                success=False,
                error=result.stderr or "Screenshot capture failed",
            )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.IOS,
            device_name=_get_ios_device_name(),
            os_version=_get_ios_version(),
            success=True,
        )
    except subprocess.TimeoutExpired:
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.IOS,
            success=False,
            error="Screenshot capture timed out",
        )
```

### File Structure Requirements

**Screenshot Naming Convention:**
```
<screen_name>_<device_type>.png
```
Examples:
- `home_ios.png`
- `home_android.png`
- `profile_ios.png`
- `settings_error_ios.png` (for failed captures)

**Metadata File Format (metadata.json):**
```json
{
  "captured_at": "2026-01-04T10:30:45Z",
  "platform_type": "mobile",
  "screenshots": [
    {
      "screen_name": "home",
      "device_type": "ios",
      "device_name": "iPhone 15 Pro",
      "os_version": "17.2",
      "file": "home_ios.png",
      "success": true
    },
    {
      "screen_name": "home",
      "device_type": "android",
      "device_name": "sdk_gphone64",
      "os_version": "14",
      "file": "home_android.png",
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
├── test_mobile_capture.py    # Mobile capture tests (NEW)
└── fixtures/
    ├── mobile_configs/       # Test config files (NEW)
    └── mock_subprocess/      # Mock command outputs (NEW)
```

**Testing Patterns:**
- Mock subprocess calls for xcrun/adb (don't require actual devices)
- Test graceful degradation when no device available
- Test configuration validation
- Use `tmp_path` for screenshot output
- Test error handling paths
- Use pytest parametrize for iOS/Android variations

**Mock Examples:**
```python
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_ios_simulator_booted():
    """Mock a booted iOS Simulator."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                {
                    "dataPath": "/path/to/data",
                    "logPath": "/path/to/logs",
                    "udid": "12345-ABCDE",
                    "name": "iPhone 15 Pro",
                    "state": "Booted"
                }
            ]
        }
    })
    with patch("subprocess.run", return_value=mock_result):
        yield


def test_check_ios_simulator_available_when_booted(mock_ios_simulator_booted):
    """Test that iOS simulator is detected when booted."""
    from adw.evidence.mobile_capture import check_ios_simulator_available
    assert check_ios_simulator_available() is True


def test_check_ios_simulator_not_available_when_no_xcrun():
    """Test graceful handling when xcrun not available."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        from adw.evidence.mobile_capture import check_ios_simulator_available
        assert check_ios_simulator_available() is False
```

**Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 8.1 (Platform Detection) - CRITICAL:**
- `PlatformDetector` already detects mobile markers:
  - iOS: `.xcodeproj`, `.xcworkspace`, `Info.plist`
  - Android: `AndroidManifest.xml` + `build.gradle`
  - Flutter: `pubspec.yaml` with `sdk: flutter`
- Mobile platform returns `PlatformType.MOBILE`
- `get_evidence_strategy(PlatformType.MOBILE)` returns `EvidenceStrategy.SCREENSHOT`
- Detection logic in `detector.py:_detect_mobile_markers()` (lines 340-400)

**From Story 8.3 (Web Screenshots) - PATTERN REFERENCE:**
- Use similar `CaptureStrategy` pattern
- Similar result models (`ScreenshotResult`, `EvidenceSummary`)
- Same error handling approach (capture failure doesn't fail phase)
- Same file organization under `evidence/screenshots/`
- Story 8.3 is in "review" status - web_capture.py not yet merged

**Existing Evidence Models (models/evidence.py):**
```python
class PlatformType(str, Enum):
    CLI = "cli"
    WEB = "web"
    MOBILE = "mobile"    # Already defined!
    BACKEND = "backend"
    UNKNOWN = "unknown"

class EvidenceStrategy(str, Enum):
    TERMINAL_OUTPUT = "terminal_output"
    SCREENSHOT = "screenshot"    # Used for both WEB and MOBILE
    API_CAPTURE = "api_capture"
```

---

## Git Intelligence

**Recent Commits (last 10):**
```
ed4df63 story update
6861dd4 story update
68a7534 Sprint update
0e30790 Update sprint status
eb806d9 Updates
1245a2b Fixes
2b99f97 feat(story-8-1): Detect Project Platform Type (#42)
039721c Merge branch 'staging'
4801ab0 Fixes
bdfdcad feat(story-3-6): Security Hook Infrastructure (#40)
```

**Key Patterns from Story 8.1:**
- Platform detection uses subprocess for checking tools
- JSON parsing of command output
- Graceful error handling with try/except
- Type annotations on all functions
- Structured logging with `LogCategory`

---

## Latest Technical Information

**iOS Simulator Commands (Xcode 15+):**
```bash
# List all simulators with state
xcrun simctl list devices --json

# Capture screenshot from booted device
xcrun simctl io booted screenshot <path.png>

# Get specific simulator info
xcrun simctl list devices booted --json

# Alternative: Capture specific device by UDID
xcrun simctl io <UDID> screenshot <path.png>
```

**Android ADB Commands (latest):**
```bash
# List connected devices
adb devices -l

# Capture screenshot (binary PNG output)
adb exec-out screencap -p > output.png

# Alternative: Capture to device, then pull
adb shell screencap /sdcard/screen.png && adb pull /sdcard/screen.png

# Get device properties
adb shell getprop | grep -E "model|version.release|manufacturer"
```

**Flutter Device Detection:**
```bash
# JSON output of connected devices
flutter devices --machine

# Check if flutter is available
flutter doctor --verbose
```

**Platform-Specific Considerations:**
- **macOS only**: `xcrun simctl` requires macOS with Xcode installed
- **Cross-platform**: `adb` works on macOS, Linux, Windows
- **CI/CD**: GitHub Actions macOS runners have Xcode pre-installed
- **Timeout handling**: Device commands may hang if device is unresponsive

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required (Python 3.13+ syntax: `str | None`)
- Context managers for subprocess resources
- Graceful error handling (don't crash on missing tools)
- Use Rich for CLI output, but this module is not CLI-facing

---

## Dev Notes

- iOS screenshot capture is macOS-only (requires Xcode/Simulator)
- Android capture requires ADB in PATH (Android SDK platform-tools)
- Flutter detection helps route to correct capture method
- Consider running iOS and Android captures in parallel if both available
- Deeplink navigation is optional/nice-to-have for MVP
- Screen navigation steps are complex - consider deferring to post-MVP

### Project Structure Notes

- Add `mobile_capture.py` to `evidence/` package (parallel to future web_capture.py)
- Update `evidence.py` models with mobile-specific types
- Evidence output goes to `evidence/screenshots/mobile/` (separate from web)
- No new dependencies required (uses subprocess for system commands)

### References

- [Source: _bmad-output/epics/epic-8-evidence-gathering.md#Story-8.3b] - Story definition
- [Source: src/adw/evidence/detector.py:340-400] - Mobile marker detection
- [Source: src/adw/models/evidence.py] - Existing evidence models
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: _bmad-output/implementation-artifacts/8-3-capture-web-screenshots.md] - Sibling story patterns

---

## Dependencies

- **Depends On:** Story 8.1 (Platform Detection) - DONE
- **Blocks:** Story 8.5 (Generate Evidence Manifest), Story 8.6 (Compress Evidence)
- **Can Parallel With:** Story 8.2 (CLI Capture), Story 8.3 (Web Screenshots), Story 8.4 (API Capture)

### Dependency Rationale
- Requires platform detection (8.1) to know when to use mobile strategy
- Produces evidence files consumed by manifest (8.5) and compression (8.6)
- Can be developed in parallel with other evidence capture strategies

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

- src/adw/models/evidence.py (modified - added mobile evidence models)
- src/adw/models/__init__.py (modified - exported new models)
- tests/unit/models/test_evidence.py (modified - added mobile model tests)

