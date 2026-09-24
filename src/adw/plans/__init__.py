"""Plan directories in the plan skills' format (docs/artifacts/plans/<slug>/).

ADW's own copy of the format that the create-plan, implement-plan and
archive-plan skills read and write:

- adw.plans.paths: where plans live, slugs
- adw.plans.templates: the bundled templates (adw/defaults/plans/)
- adw.plans.authoring: init_plan, add_task, add_final_task

Every function takes the project root explicitly.
"""
