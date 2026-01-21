# Issue: Init Wizard Should Generate Complete Config Files with Commented Defaults

**ID:** ISS-032
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** 14 (Interactive Init Wizard)
- **Story:** N/A
- **Component:** Init Wizard / CLI Commands

## Description

The init wizard currently only writes settings that the user explicitly configures during the wizard flow. This leaves users without visibility into the full range of available configuration options and their default values.

The wizard should generate ALL config files (`project.yaml` and `config.yaml` for each phase) at completion, with every setting that was NOT changed during the wizard added as a comment showing the default value. This gives users a complete reference of all available settings directly in their config files.

## Reproduction Steps

1. Run `adw init` and go through the wizard
2. Accept defaults for most settings, only change a few
3. Examine the generated config files in `.adw/`
4. Notice that only explicitly configured settings are present
5. User has no visibility into other available options without reading documentation

## Expected Behavior

After wizard completion:
- `project.yaml` contains ALL available project-level settings
- Each phase's `config.yaml` contains ALL available phase settings
- Settings changed by user are written as active config
- Settings NOT changed are written as comments with default values, e.g.:
  ```yaml
  # timeout: 300  # default
  # enabled: true  # default
  retry_attempts: 5  # user configured this
  ```

## Actual Behavior

- Only settings explicitly configured during wizard are written
- Users must consult documentation to discover additional options
- No visibility into default values without reading source code

## Impact

- Poor discoverability of configuration options
- Users don't know what settings are available to customize
- Requires external documentation lookup to understand full capabilities
- Makes it harder for users to fine-tune ADW behavior post-setup

## User Impact Score

- **Users Affected:** All new users running init wizard
- **Frequency:** Every project setup

## Workaround

Manually copy settings from documentation or source code into config files.

## Environment

- **OS:** macOS / Linux / Windows
- **App Version:** 0.1.21
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-032-init-wizard-generate-complete-config-files.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This improvement aligns with the principle of "configuration as documentation" - users should be able to understand all available options by examining their own config files rather than searching external docs.

Implementation considerations:
- Need to maintain a registry of all settings with their defaults and descriptions
- Comments should include brief description of what each setting does
- Group related settings together for readability
- Consider YAML anchors or separate "defaults reference" section
