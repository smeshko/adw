"""Plan directories in the plan skills' format (docs/artifacts/plans/<slug>/).

ADW's own copy of the format that the create-plan, implement-plan and
archive-plan skills read and write:

- adw.plans.paths: where plans live, slugs
- adw.plans.templates: the bundled templates (adw/defaults/plans/)
- adw.plans.authoring: init_plan, add_task, add_final_task
- adw.plans.model: Plan and PlanTask, parsed from PLAN.md
- adw.plans.reader: load_plan, list_plans, list_tasks, resolve_plan_by_branch
- adw.plans.state: mark_task_done, set_plan_status, set_plan_branch
- adw.plans.epics: resolve_epic_file, link_plan, epic_status
- adw.plans.archive: archive_plan

Every function takes the project root explicitly.
"""
