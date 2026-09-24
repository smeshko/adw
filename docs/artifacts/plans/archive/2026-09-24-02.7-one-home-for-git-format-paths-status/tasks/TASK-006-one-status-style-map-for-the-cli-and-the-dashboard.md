# TASK-006: One status style map for the CLI and the dashboard

Depends on: TASK-004, TASK-005
Suggested commit: `refactor(format): one status style map for the CLI and the dashboard`

## Goal

One `STATUS_STYLES` map, keyed by `RunStatus`, gives each run status a Rich colour, an icon and dashboard badge classes. All of these use it:

- `adw list` (local and global)
- `adw global list`
- `adw status`
- the end-of-run summary
- the dashboard badge

The runs filter bar lists its options from `RunStatus`.

## Files

- `src/adw/format.py`:
  - `class StatusStyle(NamedTuple)` with fields `color: str` (a Rich colour), `icon: str` and `badge: str` (DaisyUI classes).
  - `STATUS_STYLES: Final[Mapping[RunStatus, StatusStyle]]`:
    - running: `("yellow", "●", "badge-warning phase-active")`
    - completed: `("green", "✓", "badge-success badge-soft")`
    - failed: `("red", "✗", "badge-error")`
    - interrupted: `("orange1", "⊘", "badge-warning badge-outline")`
    - aborted: `("bright_black", "⦻", "badge-ghost")`
  - `UNKNOWN_STATUS_STYLE = StatusStyle("white", "?", "badge-ghost")`.
  - `status_style(status: str) -> StatusStyle` returns `STATUS_STYLES[RunStatus(status)]`, with `except ValueError: return UNKNOWN_STATUS_STYLE`. Under mypy `--strict`, `Mapping[RunStatus, …].get(str)` fails with call-overload (validation round 1, #20).
- CLI. Delete each map and call `status_style(s).color`:
  - `cli/global_commands.py:67`–`:83` `_get_status_style` (used at `:164`)
  - `cli/list.py:249`–`:265` `_get_status_style` (used at `:221`)
  - `cli/list_display.py:30`–`:36` `STATUS_COLORS` and its `:68` fallback
  - `cli/status_display.py:40`–`:46` `STATUS_COLORS`, used for the status text and the panel border at `:68`, `:85` and `:101`
  - `cli/progress.py:308`–`:316`, the if/elif chain for the summary text and border (`:322`, `:344`)
  - `cli/progress.py:68`–`:75` `STATUS_ICONS`, which nothing in `src` reads, and its line in the class docstring at `:50`

  `list.py:221` and `global_commands.py:164` assign a local named `status_style`, which would shadow the imported function (ruff F823). Rename those locals to `color` (validation round 1, #1).
- Dashboard:
  - `dashboard/server.py` `build_templates()` also sets the globals `status_style` (the function) and `run_statuses` (`list(RunStatus)`).
  - `templates/components/status_badge.html`: replace the macro's `config` map with `{%- set s = status_style(status) -%}`, then `<span class="badge badge-{{ size }} {{ s.badge }}">{{ s.icon }} {{ status }}</span>`. The pulse class now sits in `badge`.
  - `templates/partials/runs_filter_bar.html:22`–`:26`: the five hand-written `<option>`s become `{% for s in run_statuses %}<option value="{{ s }}" …>{{ s|capitalize }}</option>{% endfor %}`, keeping today's `selected` logic and labels.
- Tests:
  - `tests/unit/cli/test_status_styles.py` (new): `test_list_and_status_colour_each_status_alike`.
    - Parametrize over `RunStatus`. Render the local `adw list` table row (`list_display`) and the `adw status` panel (`status_display`) for a `RunContext` in that status. Use a `Console(file=StringIO(), force_terminal=True, color_system="256", width=200)`.
    - Assert that the ANSI escape sequence just before the status word is the same in both outputs, and equals the sequence Rich emits for `status_style(status).color`.
    - A second case renders `progress`'s end-of-run summary for the same status and asserts the same sequence.
  - `tests/unit/test_format.py`: add `test_status_style_covers_every_run_status` (every `RunStatus` member has an entry, and an unknown string gets `UNKNOWN_STATUS_STYLE`). This is a behaviour test of the fallback, not an enum-count test.
  - `tests/unit/dashboard/test_stat_cards.py:626`–`:700`: the badge tests render through `build_templates().env`. Keep the per-status class and icon assertions, since the dashboard's look is unchanged.
  - `tests/unit/cli/test_progress.py:61`–`:73`: delete the `STATUS_ICONS` membership tests (ADR-001 enum-existence).
  - Update any test that asserts a colour that changes (`adw global list`: running blue → yellow, interrupted yellow → orange1, aborted magenta → bright_black; progress: interrupted cyan → orange1, aborted dark_orange → bright_black, running red → yellow).

## Acceptance

- [ ] `rg -n 'STATUS_COLORS|STATUS_ICONS|_get_status_style' src` prints nothing. `rg -n '"(running|completed|failed|interrupted|aborted)":\s*"' src/adw/cli src/adw/format.py` prints nothing: the map is keyed by `RunStatus` members.
- [ ] `rg -n 'badge-(warning|success|error|ghost)' src/adw/dashboard/templates/components/status_badge.html` prints nothing: the macro has no map of its own.
- [ ] `test_list_and_status_colour_each_status_alike` passes for all five statuses, and so do the badge tests.
- [ ] `uv run pytest tests/unit/cli tests/unit/dashboard tests/unit/test_format.py -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_list_and_status_colour_each_status_alike` for `aborted` (bright_black vs red) and for `interrupted` in the progress summary, then the GREEN tail, the `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Write `test_list_and_status_colour_each_status_alike`; run it: `aborted` (list vs status) and the progress cases fail.

### GREEN
- [ ] Add `StatusStyle`, `STATUS_STYLES` and `status_style` to `adw.format`.
- [ ] Switch the five CLI sites; delete `STATUS_ICONS`.
- [ ] Register the two globals; rewrite the badge macro and the filter bar.
- [ ] Update the badge and progress tests; run the partial suite: green.

### REFACTOR
- [ ] Re-run the `rg` checks; `scripts/preflight.sh` passes.

## Notes

- Jinja makes environment globals visible inside `{% import %}`ed macros, so `status_style` works in `status_badge.html` without `with context`.
- `format.py` imports `RunStatus` from `adw.models.context`. `adw.models` imports nothing from `adw.format`, so there is no cycle.
- The phase-pipeline classes (`step-success` / `step-warning` / `step-error`) and glyphs are out of scope (phase 2.11).
