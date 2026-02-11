# Issue: Init wizard phase configuration step has multiple UX issues

**ID:** ISS-027
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-19
**Reporter:** Ivo

## Related

- **Epic:** 14
- **Story:** 14-6
- **Component:** Init Wizard (Phase Configuration)

## Description

The Phase Configuration step (Step 5/9) has several usability problems: clunky individual y/n prompts for phase selection, prompts for non-configurable options, unused config options, contradictory messaging, and confusing completion message.

## Reproduction Steps

1. Run `adw init --wizard`
2. Progress to Step 5/9: Phase Configuration
3. Select "y" to customize phases
4. Observe individual y/n prompts for each phase (clunky)
5. Observe pre/post-hook path prompts (non-configurable)
6. Observe focus options (security/error handling/edge cases) that are unused
7. Enable danger mode and note contradictory confirmation message
8. Complete wizard and observe confusing "Summary step" note

## Expected Behavior

1. **Phase selection**: Should use multiselect or comma-separated list input instead of individual y/n prompts for each phase
2. **Hook paths**: Pre/post-hook script path prompts should be removed entirely (SDK always uses fixed `pre.sh`/`post.sh` in phase folder)
3. **Focus options**: Security, error handling, and edge cases options should be removed from wizard and config (not used in code)
4. **Danger mode message**: Should not mention "You'll be prompted to confirm risky operations" - this contradicts the purpose of enabling danger mode
5. **Completion message**: Should not say "Full configuration will be applied in the Summary step" when summary has already been displayed

## Actual Behavior

1. **Phase selection**: Individual y/n prompts for each phase (5 separate prompts required)
2. **Hook paths**: Pre/post-hook script path prompts are shown despite being non-configurable
3. **Focus options**: Focus options (security, error handling, edge cases) are collected but never used in code
4. **Danger mode message**: Says "You'll be prompted to confirm risky operations" which contradicts the purpose of danger mode
5. **Completion message**: Says "Full configuration will be applied in the Summary step" but summary was already displayed

## Impact

Makes the wizard feel unpolished and confusing. Users may configure options that have no effect, wasting time and causing confusion about what the SDK actually supports.

## User Impact Score

- **Users Affected:** All first-time users running wizard
- **Frequency:** Every wizard run

## Workaround

None - issues are cosmetic/UX only, wizard still functions correctly.

## Environment

- **OS:** macOS
- **App Version:** 0.1.16
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-027-init-wizard-phase-config-ux-issues.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This issue consolidates 5 related UX problems in the Phase Configuration wizard step:
1. Clunky phase selection UX (individual y/n prompts)
2. Non-configurable hook path prompts
3. Unused focus options in config
4. Contradictory danger mode messaging
5. Confusing completion message
