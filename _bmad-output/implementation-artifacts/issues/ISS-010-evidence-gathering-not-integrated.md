# Issue: Evidence gathering not integrated into verify phase

**ID:** ISS-010
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 8
- **Story:** 8-2, 8-3, 8-4, 8-5
- **Component:** Evidence Gathering

## Description

The evidence gathering modules exist (CLI capture, web screenshots, API capture, mobile screenshots) but they are **never invoked** during the verify phase. Platform detection runs, evidence optimization runs, but actual evidence capture is missing from the pipeline.

## Reproduction Steps

1. Run `adw init` in a project
2. Run `adw run "Create hello world command"`
3. Check artifacts after completion:
   ```bash
   ls .adw/runs/<run_id>/artifacts/verify/
   ```
4. Only `verify_output.md` and `verify_tool_calls.json` exist
5. No `evidence_manifest.json`
6. No evidence directory: `.adw/runs/<run_id>/evidence/` doesn't exist

## Expected Behavior

During VERIFY phase:
1. Platform type detected (CLI/WEB/MOBILE/BACKEND)
2. Evidence gathered based on platform:
   - CLI: Command outputs captured
   - WEB: Screenshots taken via Playwright
   - MOBILE: Simulator screenshots
   - BACKEND: API response pairs
3. Evidence manifest generated at `.adw/runs/<run_id>/evidence/manifest.json`
4. Evidence copied to verify artifacts

## Actual Behavior

- Platform detection runs ✓
- Evidence optimization runs (on empty directory) ✓
- BUT no evidence is actually captured ✗
- No evidence directory created
- No evidence manifest generated
- Verify artifacts only contain LLM output

## Impact

- No automated evidence for PR descriptions
- No screenshots or command outputs to verify implementation
- Document phase can't reference evidence
- Defeats purpose of Epic 8 (Evidence Gathering)

## User Impact Score

- **Users Affected:** All users
- **Frequency:** Every run

## Workaround

None - evidence modules aren't callable from CLI or anywhere.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0

## Evidence

### Artifacts Directory

```bash
$ ls -la .adw/runs/01KE6YXDTRCSZHKXTZWA32JSYC/artifacts/verify/
verify_output.md
verify_tool_calls.json
# No evidence_manifest.json
```

### Missing Evidence Directory

```bash
$ ls .adw/runs/01KE6YXDTRCSZHKXTZWA32JSYC/evidence/
ls: .../evidence/: No such file or directory
```

### Context Shows No Platform

```bash
$ cat .adw/runs/.../context.json | jq '.platform_type'
null
```

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

The evidence module at `src/adw/evidence/` contains:
- `detector.py` - Platform detection (works, called from orchestrator)
- `cli_capture.py`, `cli_gatherer.py` - CLI evidence (NOT called)
- `web_capture.py` - Web screenshots (NOT called)
- `mobile_capture.py` - Mobile screenshots (NOT called)
- `api_capture.py` - API capture (NOT called)
- `manifest.py` - Manifest generation (NOT called)
- `optimizer.py` - Evidence optimization (called, but on empty dir)

The orchestrator imports `detect_platform` and `optimize_evidence` but NOT the actual gathering functions. The verify phase prompt doesn't mention evidence gathering either.

**Missing integration:**
1. Orchestrator needs to call evidence gathering after LLM verify phase
2. OR verify phase prompt needs to instruct LLM to use evidence tools
3. OR hooks need to trigger evidence capture
