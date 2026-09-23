# TASK-006: Add the three waste categories to ADR-001

Depends on: None
Suggested commit: `docs(adr): add markup, prose and placeholder tests to ADR-001 eliminate list`

## Goal

ADR-001 names the three kinds of test this phase deleted, so future reviews reject them by rule.

## Files

- `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`: add three rows to the "Categories to Eliminate" table (lines 22-32), in the existing `Category | Description | Example` format:

  | Category | Description | Example |
  |---|---|---|
  | **HTML Markup Substrings** | Tests asserting that rendered HTML contains a tag, class or attribute string, not the data or behaviour behind it | `assert 'class="badge-success"' in response.text` |
  | **Prompt/Instruction Prose** | Tests asserting wording in `prompt.md`, `instructions.xml` or other LLM-facing text. The LLM follows it; no code executes it. Structural checks (config validates, XML parses) are enough | `assert "STEP 5: FAILURE DIAGNOSIS" in instructions` |
  | **`pass` Placeholders** | Test functions whose body is only a docstring and `pass`. They always pass and document intent in the wrong place | `def test_failure_stops_sequence(self): """…"""; pass` |

## Acceptance

- [ ] The table has 10 rows, and the three new ones render as table rows (no broken pipes).
- [ ] `grep -n "HTML Markup Substrings\|Prompt/Instruction Prose\|Placeholders" docs/architecture/adrs/ADR-001-test-reduction-strategy.md` returns 3 lines.

Evidence: the ADR diff and the grep output.

## Steps

- [ ] Add the three rows after "Help Text Verification".
- [ ] Preview the table (any Markdown renderer, or check the pipe count per row). Confirm the `|` inside the backticked HTML example doesn't split a cell; it has none, but check any edit.
- [ ] Run the grep.

## Notes

- Leave the "Metrics" and "Implementation" sections as they are. Their numbers date from the original reduction, and refreshing them is out of scope.
