# TASK-003: Rewrite the settings docs for the read-only page

Depends on: TASK-002
Suggested commit: `docs(dashboard): describe the read-only settings page`

## Goal

The docs describe the Settings page as it now is, a read-only view, and no doc sends a reader to the deleted editing code.

## Files

- `docs/features/settings-page-config-viewing.md`: rewritten.
- `docs/features/phase-config-editor.md`, `docs/features/complex-field-editors-task-manager-security.md` and `docs/features/reset-defaults-changed-indicators-validation.md`: deleted.
- `docs/CONDITIONAL_DOCS.md`:
  - Delete the three entries for the deleted docs.
  - Rewrite the conditions of the `settings-page-config-viewing.md` entry for viewing: adding a config section, and how phase configs are shown.
- `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`, phase 2.8's list of read sites that `load_command_config` replaces: change `dashboard/partials.py` to `dashboard/settings.py` (`_phase`, which copies `PhaseRunner`'s merge rules). Without this, 2.8 would miss the dashboard's copy (validation round 2 #1). Add an acceptance criterion to phase 2.8 so the handoff is enforced (validation round 3 #3): "`dashboard/settings.py` reads phase configs through `load_command_config`. `grep -rn \"yaml.safe_load\\|model_validate\" src/adw/dashboard` returns nothing." Add the same line to Linear ADW-24's acceptance criteria.

## Acceptance

- [ ] `settings-page-config-viewing.md` covers:
  - the routes: `GET /settings` and `GET /partials/settings-content`
  - `settings_context()` and how it derives sections from `ProjectConfig`
  - how phase values are read and merged (resolved tier, then project file, by `PhaseRunner`'s rules), and what an invalid phase file shows
  - that the page never writes, and that settings are changed by editing `.adw/project.yaml` or `.adw/commands/<phase>/config.yaml`
- [ ] `grep -rnE "settings/save|settings-phase|settings-section|settings_phase_editor|settings_task_manager_fields|phase-config-editor|complex-field-editors|reset-defaults-changed|_SECTION_FIELD_MAP|build_settings_context" docs README.md AGENTS.md | grep -v "docs/artifacts/"` returns nothing.

Evidence: the empty grep output and the rewritten doc's diff.

## Steps

- [ ] Rewrite `docs/features/settings-page-config-viewing.md`. Keep the house format (title, Date, Related Files, Overview, Technical Implementation, How to Use). Point Related Files at `dashboard/settings.py`, the two routes and the two templates.
- [ ] Delete the three editing docs with `git rm`.
- [ ] Edit `docs/CONDITIONAL_DOCS.md` as listed above.
- [ ] Edit epic 02's phase 2.8 read-site bullet, and add its new acceptance criterion, as listed above. Add that criterion to Linear ADW-24 as well (`mcp__linear-server__save_issue`, patching its acceptance list). Then check that `grep -n "dashboard/settings.py" docs/artifacts/epics/02-cleanup-remove-and-consolidate.md` shows it in phase 2.8, and that `grep -n "dashboard/partials.py" docs/artifacts/epics/02-cleanup-remove-and-consolidate.md` no longer lists it there.
- [ ] Run the acceptance grep.

## Notes

- Leave the rest of `docs/artifacts/` alone: epic and plan files record history. The only exceptions are phase 2.8's read-site bullet and its new acceptance criterion, which describe future work that this plan moves.
- Epic 03's phase that merges `docs/features/*.md` into `docs/dashboard.md` cites "21" feature docs. After this task, 18 remain; that phase recounts when it is planned.
