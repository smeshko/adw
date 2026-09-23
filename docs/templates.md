# Template Variables Reference

This document describes ADW's prompt template syntax, the order in which a template is rendered, and the variables available in ADW prompt templates.

## Template Syntax

| Form | Meaning |
|------|---------|
| `{{name.path}}` | Variable, resolved by walking the dotted path from the top-level name `name` |
| `{{name.*}}` | Wildcard variable: lists the entries at that path as `- key: value` lines, or renders empty if the path under a known name does not exist |
| `{{include:rel}}` | Contents of `rel` under the command's own directory (for example `defaults/commands/validate/`) |
| `{{shared:rel}}` | Contents of `rel` under the commands directory, which is the command directory's parent |
| `{{file:rel}}` | Contents of `rel` under the project root |

A directive's path must stay inside its root. A `..` that leaves the root, or an absolute path outside it, raises `INCLUDE_PATH_TRAVERSAL`, `SHARED_PATH_TRAVERSAL` or `TEMPLATE_PATH_TRAVERSAL`. The other errors use the same prefixes: `*_FILE_NOT_FOUND`, `*_FILE_PERMISSION`, `*_FILE_IS_DIRECTORY` and `*_FILE_ENCODING` (files are read as UTF-8), plus `INCLUDE_NO_ROOT` or `SHARED_NO_ROOT` when `render()` is called without a `command_root` or `shared_root`.

## Render Order

1. **Directives are expanded.** Every `{{include:}}`, `{{shared:}}` and `{{file:}}` is replaced with its file's contents in a single pass. Included text is not scanned for further directives, so directives do not nest: an included file's own `{{file:…}}` reaches the output as literal text.
2. **Variables are filled** in the combined text, so ADW variables work inside included files as well as in `prompt.md`.
3. **Values are inserted literally.** A variable's value is never expanded, so a ticket description or build diff that contains `{{file:.env}}` stays text and does not read the file.

## Which Placeholders ADW Fills

A `{{name.path}}` placeholder is filled only when `name`, its first segment, is a variable ADW passes to the renderer:

| Top-level name | Source |
|----------------|--------|
| `context` | The full `RunContext` model (`{{context.run_id}}`, `{{context.branch_name}}`, …) |
| `run_id`, `phase` | Current run ID and phase name |
| `feature`, `feature_description` | The feature request (two names for the same value) |
| `worktree_path` | The run's worktree path, or empty |
| `task` | Task-manager fields, see [Task Variables](#task-variables-story-125) |
| `artifacts` | Earlier phases' artifacts: `{{artifacts.<phase>.<file name without extension>}}` |
| `inputs` | Contents of the files in the phase's `input_files` mapping, keyed by the name given there |
| `pre_hook_output` | The pre-hook's stdout |
| `project_config` | `.adw/project.yaml` as a mapping |
| `schema` | The command's `schema.json`, or empty |
| `build_command`, `test_command` | From `.adw/project.yaml` |
| `lint_command` | From `.adw/commands/validate/config.yaml` (validate only; empty otherwise) |
| `doc_mappings` | From `.adw/commands/document/config.yaml` (document only; `[]` otherwise) |
| `ship_config` | Ship settings as YAML, from `.adw/commands/ship/config.yaml`, or empty |
| `version_bump_command`, `publish_command` | From `.adw/commands/ship/config.yaml`; defined only when that file exists |
| Pre-hook variables | Every key a pre-hook writes to `$ADW_ARTIFACTS_DIR/pre_hook_vars.json`, such as ship's `pr_number` and `pr_url` |

Everything else is left alone:

- A placeholder with any other top-level name is left verbatim for the LLM, and nothing is logged. This is how the BMAD workflow files' `{{story_key}}`, `{{analysis.*}}` and similar placeholders reach Claude.
- A known name whose path does not resolve, such as `{{artifacts.build.diff}}` before build has run, is left verbatim and logged as a warning. A `.*` wildcard is the exception: it renders empty, without a warning.
- A `None` value renders as an empty string. Other values render through `str()`.
- Only lowercase dotted names are variables. `{{#x}}`, `{{/x}}`, `{{x | default: "…"}}` and `{{PASS/FAIL}}` are never touched.

The fill rule also applies to a project file pulled in with `{{file:}}`: if that file shows `{{task.identifier}}` as an example, it is rendered as the task's identifier.

## Task Variables (Story 12.5)

When a run is initiated from a task ID (e.g., `adw run RULE-123`), task information is fetched from the configured task manager and made available in templates via `{{task.*}}` variables.

### Available Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{task.id}}` | Internal task ID from the task manager | `abc123-uuid` |
| `{{task.identifier}}` | Human-readable task identifier | `RULE-123` |
| `{{task.title}}` | Task title/summary | `Fix login bug` |
| `{{task.description}}` | Full task description | `Users cannot log in...` |
| `{{task.status}}` | Current status in task manager | `In Progress` |
| `{{task.priority}}` | Priority number (1-4) | `2` |
| `{{task.priority_label}}` | Priority label | `High` |
| `{{task.labels}}` | Comma-separated labels | `bug, urgent` |
| `{{task.assignee}}` | Assigned user | `john.doe` |
| `{{task.parent_id}}` | Parent issue ID (if exists) | `RULE-100` |
| `{{task.parent_title}}` | Parent issue title | `Epic: Authentication` |

### Priority Labels

| Priority | Label |
|----------|-------|
| 1 | Urgent |
| 2 | High |
| 3 | Medium |
| 4 | Low |

### Custom Fields

Access custom fields from the task manager using dot notation:

```
{{task.custom.my_field}}
{{task.custom.nested.deep.value}}
```

### Graceful Degradation

When no task manager is configured or the run is started with a feature description instead of a task ID, all `{{task.*}}` variables resolve to empty strings. This allows templates to reference task variables without errors when task context is unavailable.

**Example:**
```markdown
# Implementation Plan

Task: {{task.identifier}} - {{task.title}}
Priority: {{task.priority_label}}

## Description
{{task.description}}
```

When run with `adw run RULE-123`:
```markdown
# Implementation Plan

Task: RULE-123 - Fix login bug
Priority: High

## Description
Users cannot log in when using special characters in password.
```

When run with `adw run "Add user authentication"`:
```markdown
# Implementation Plan

Task:  -
Priority:

## Description

```
