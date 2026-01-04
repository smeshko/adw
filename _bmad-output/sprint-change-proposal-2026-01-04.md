# Sprint Change Proposal

**Date:** 2026-01-04
**Triggered By:** Story 8.1 — Detect Project Platform Type
**Change Scope:** Minor
**Status:** Pending Approval

---

## Section 1: Issue Summary

### Problem Statement

The original Epic 8 (Evidence Gathering) scope only covers three platform types: CLI, Web, and Backend. Mobile development (iOS, Android, Flutter) represents a significant platform category that was not included, creating a gap in evidence gathering coverage for mobile projects.

### Context

- Discovered during implementation of Story 8.1 (platform detection)
- Branch: `story/8-1`
- User identified the need for mobile platform support with specific detection markers and screenshot tooling

### Evidence

- Current `PlatformType` enum lacks `MOBILE` variant
- No detection markers for iOS (.xcodeproj, .xcworkspace), Android (build.gradle, AndroidManifest.xml), or Flutter (pubspec.yaml) projects
- No tooling integration for iOS Simulator (`xcrun simctl`) or Android Emulator (`adb`) screenshots

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Description |
|------|--------|-------------|
| **Epic 8** | Scope Expansion | Add mobile platform type and new story for mobile screenshots |
| Other Epics | None | Change is self-contained |

### Story Impact

| Story | Change Type | Description |
|-------|-------------|-------------|
| **8.1** | Modify | Add `PlatformType.MOBILE` and mobile project markers |
| **8.3b** | **New** | Capture Mobile Screenshots (iOS Simulator, Android Emulator) |
| 8.5 | None | Manifest structure already supports new evidence types |
| 8.6 | None | Compression applies to all screenshots generically |

### Artifact Conflicts

| Artifact | Conflict | Resolution |
|----------|----------|------------|
| PRD | None | FR13-FR18 already specify "platform-appropriate evidence" |
| Architecture | None | Fits existing patterns (new enum value, new strategy) |
| UX Spec | None | CLI output patterns unchanged |

### Technical Impact

- Add `PlatformType.MOBILE` enum value in `models/config.py`
- Add `EvidenceStrategy.SCREENSHOT` mapping for mobile
- Implement mobile project marker detection (iOS, Android, Flutter)
- Integrate `xcrun simctl io booted screenshot` for iOS
- Integrate `adb exec-out screencap` for Android
- Handle graceful failure when no simulator/emulator running

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (Option 1) + New Story (Option 2 Hybrid)

**Approach:**
1. Modify Story 8.1 to add mobile platform detection
2. Create new Story 8.3b for mobile screenshot capture
3. Update Epic 8 dependency flowchart to include 8.3b in Wave 2

**Rationale:**
- Clean separation of concerns (web screenshots vs mobile screenshots)
- Story 8.3 remains focused on Playwright/browser tooling
- Story 8.3b focuses on simulator/emulator tooling
- Fully parallelizable — 8.3b can be worked independently alongside 8.2, 8.3, 8.4
- Minimal disruption to existing story definitions

**Effort Estimate:** Low-Medium
- Story 8.1 modification: ~1 hour
- Story 8.3b implementation: ~4-6 hours

**Risk Assessment:** Low
- Well-defined scope
- No architectural changes required
- Graceful failure handling prevents phase failures

**Timeline Impact:** Minimal — adds one parallelizable story to Wave 2

---

## Section 4: Detailed Change Proposals

### 4.1 Story 8.1 Modification

**Add to Acceptance Criteria:**

```markdown
**Given** project config with `platform: mobile`
**When** evidence gathering starts
**Then** mobile screenshot strategy is used

**Given** no platform specified
**When** detection is attempted
**Then** it's inferred from project markers:
  - `package.json` with react/vue/angular → web
  - `*.xcodeproj` or `*.xcworkspace` or `Info.plist` → mobile (iOS)
  - `build.gradle` with android plugin or `AndroidManifest.xml` → mobile (Android)
  - `pubspec.yaml` with flutter dependency → mobile (Flutter)
```

### 4.2 New Story 8.3b: Capture Mobile Screenshots

```markdown
## Story 8.3b: Capture Mobile Screenshots

As a developer,
I want screenshots captured from iOS simulators and Android emulators,
So that mobile UI changes can be visually verified.

**Acceptance Criteria:**

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
```

### 4.3 Epic 8 Dependency Flowchart Update

- Wave 2 changes from "PARALLEL x3" to "PARALLEL x4"
- Add Story 8.3b alongside 8.2, 8.3, 8.4
- Wave Summary table updated to include 8.3b

### 4.4 Epic Index Update

- Add Story 8.3b entry to Epic 8 section in table of contents

---

## Section 5: Implementation Handoff

### Change Scope Classification: Minor

This change can be implemented directly by the development team without requiring backlog reorganization or strategic replanning.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Development Team** | Implement Story 8.1 modifications and Story 8.3b |
| **QA** | Verify mobile detection and screenshot capture |

### Implementation Tasks

1. [ ] Update `PlatformType` enum with `MOBILE` value
2. [ ] Add mobile project marker detection logic
3. [ ] Implement iOS Simulator screenshot capture (`xcrun simctl`)
4. [ ] Implement Android Emulator screenshot capture (`adb`)
5. [ ] Add graceful failure handling for missing simulator/emulator
6. [ ] Add `evidence.mobile_screens` config schema
7. [ ] Update evidence manifest to include mobile evidence type
8. [ ] Write unit tests for mobile detection
9. [ ] Write integration tests for screenshot capture

### Success Criteria

- `PlatformType.MOBILE` correctly detected for iOS, Android, and Flutter projects
- Screenshots captured from running iOS Simulator
- Screenshots captured from running Android Emulator
- Graceful warning (not failure) when no simulator/emulator available
- Evidence manifest includes mobile screenshots with metadata

---

## Approval

**Proposed by:** John (PM Agent)
**Approved by:** _________________
**Date:** _________________

---

*Sprint Change Proposal generated by Correct Course workflow on 2026-01-04*
