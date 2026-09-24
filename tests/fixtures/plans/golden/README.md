# Golden plan tree

`add-a-dry-run-flag-to-the-importer/` is the tree that the create-plan skill's scripts wrote for one title, risk and task list. It is committed untouched.

`test_cli_scaffold_matches_skill_golden_tree` in `tests/unit/cli/test_plan.py` feeds the same inputs to `adw plan init`, `add-task` and `add-final`, and compares the two trees byte for byte. That test's `NORMALISATIONS` list names every difference it tolerates.

When a create-plan script or template changes, regenerate this tree and update `src/adw/defaults/plans/` in the same commit:

```bash
S=~/.claude/skills/create-plan/scripts
SLUG=add-a-dry-run-flag-to-the-importer
REPO=$(git rev-parse --show-toplevel)
cd "$(mktemp -d)"
python3 $S/init_plan.py --root . --title "Add a --dry-run flag to the importer" --risk medium
python3 $S/add_task.py $SLUG --root . --type impl --title "Parse the --dry-run flag"
python3 $S/add_task.py $SLUG --root . --type checklist --title "Document the flag in the README" --depends TASK-001
python3 $S/add_final_task.py $SLUG --root .
rm -rf "$REPO/tests/fixtures/plans/golden/$SLUG"
cp -R "docs/artifacts/plans/$SLUG" "$REPO/tests/fixtures/plans/golden/"
```
