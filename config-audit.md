# ADW Configuration Audit Report (Updated)

**Date:** 2026-02-09 | **Branch:** refactoring/remove-hook-config-strings | **Commit:** `9416217` + uncommitted

## Changes Since Last Audit

PRs #159, #160, #161 removed 16 dead fields, 2 dead classes (`PipelineConfig`, `ArtifactConfig`), and wired 4 previously-dead configs. This branch continues the cleanup:

### This Branch (committed + uncommitted)
- **Wired**: `security.blocked_patterns` + `security.blocked_env_files` → now passed to `SecurityInterceptor` via `bootstrap.py:243-247`
- **Removed**: `security.allow_dangerous` (was DISCONNECT), `PhaseLLMConfig.temperature` (was PARTIAL), `ValidateCommandConfig.triage_mode` + `auto_dismiss_info` (TEMPLATE only), `ShipPRConfig` class (`merge_on_success`, `delete_branch_on_merge`, `merge_method`), `CommandConfig.pre_hook` + `post_hook` (string fields), `PhaseConfig.pre_hook` + `post_hook`
- **Restructured**: `pr.bypass_ci` → flat `bypass_ci` on `ShipCommandConfig` (default changed `false` → `true`)

### Previous PRs
- **Wired** (PR #160/#161): `logging.redaction.*`, `build_command`/`test_command` injection, `ship.commands.*` template vars, `git.skip_hooks`
- **Removed** (PR #159/#161): `llm.max_retries`, `pipeline.strict_artifacts`, `worktree.preserve_artifacts`, `worktree.artifact_manifest_file`, `CommandConfig.artifacts`, plus 8 fields from PR #159

---

## Column Legend

| Column | Meaning |
|--------|---------|
| **Runtime** | How the field is consumed by running code |
| **Wizard** | Which `adw init --wizard` step collects this (`--` = not asked) |
| **Generated YAML** | How it appears in generated config files |

**Runtime statuses:**
- **USED** — Explicitly read by Python runtime code
- **TEMPLATE** — Injected into prompt template via `model_dump()`, not individually extracted

**Generated YAML statuses:**
- **Active** — Always written as a live, uncommented key
- **Commented** — Written as `# key: default`
- **Conditional** — Active if user configured it, otherwise commented
- **Not generated** — Must be manually edited into config files

---

## 1. ProjectConfig — Top-Level

> `src/adw/models/config.py:472`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `name` | USED | BASICS | Active | required | `dry_run.py:213` — Display in dry-run table. Directory name auto-detected. |
| `language` | USED | BASICS | Active | required | `dry_run.py:214` — Auto-detected from marker files. |
| `framework` | USED | BASICS | Conditional | `None` | `dry_run.py:215` — Active if set, `# framework: null` otherwise. |
| `platform` | USED | BASICS | Active | `"cli"` | `dry_run.py:217` — Choices: cli, web, api, custom. |
| `test_command` | USED | BASICS | Conditional | `None` | `phase_runner.py:396-397,422-423` — Injected into validate & ship template context. |
| `build_command` | USED | BASICS | Conditional | `None` | `phase_runner.py:406-409,419-420` — Injected into ship template context. |

---

## 2. LLMConfig

> `src/adw/models/config.py:78`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `llm.path` | USED | -- | Commented | `"claude"` | `dry_run.py:226`, `executors/claude_code.py:652` — Path to Claude Code executable. |
| `llm.timeout_seconds` | USED | -- | Commented | `300` | `executors/claude_code.py:97-98` — Timeout for LLM subprocess calls. |

*Removed in PR #161:* ~~`llm.max_retries`~~ (was shadowed by `RetryConfig.max_retries`)

---

## 3. RetryConfig

> `src/adw/models/config.py:21`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `retry.max_retries` | USED | LLM_RETRY | Conditional | `3` | `executors/retry.py:97` — Loop count in RetryExecutor. |
| `retry.base_delay_seconds` | USED | LLM_RETRY | Conditional | `1.0` | `executors/retry.py:166` — Exponential backoff initial delay. |
| `retry.max_delay_seconds` | USED | LLM_RETRY | Conditional | `60.0` | `executors/retry.py:188` — Caps backoff delay. |
| `retry.multiplier` | USED | LLM_RETRY | Conditional | `2.0` | `executors/retry.py:167` — Backoff multiplier (must be > 1.0). |

**Note:** Generator emits `retry:` keys as `max_retries`, `base_delay`, `max_delay`, `multiplier` (without `_seconds` suffix), but model expects `base_delay_seconds` / `max_delay_seconds`. This is a **key name mismatch** — the generated YAML won't parse into the model correctly.

---

## 4. HookConfig

> `src/adw/models/config.py:136`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `hooks.shell` | USED | -- | Not generated | `"/bin/bash"` | `hooks/runner.py:196` — Shell executable for hook subprocess. Manual edit only. |
| `hooks.timeout_seconds` | USED | -- | Not generated | `60` | `hooks/runner.py:77-78` — Timeout hierarchy fallback. Manual edit only. |

---

## 5. LoggingConfig / RedactionConfig

> `src/adw/models/config.py:150-193`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `logging.redaction.enabled` | USED | -- | Not generated | `true` | `bootstrap.py:115` — Passed to `create_redactor_from_config()`. Wired in PR #160. |
| `logging.redaction.patterns` | USED | -- | Not generated | `[]` | `bootstrap.py:116` — Custom regex patterns for log redaction. |
| `logging.redaction.disable_defaults` | USED | -- | Not generated | `false` | `bootstrap.py:117` — Skip default redaction patterns. |

---

## 6. SecurityConfig

> `src/adw/models/security.py:55`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `security.blocked_patterns` | **USED** | SECURITY | Commented | `[]` | `bootstrap.py:243-246` — Passed to `SecurityInterceptor(additional_patterns=...)`. Merged with hardcoded defaults. **Wired in this branch.** |
| `security.blocked_env_files` | **USED** | SECURITY | Commented | `[]` | `bootstrap.py:243-247` — Passed to `SecurityInterceptor(additional_file_patterns=...)`. Merged with hardcoded defaults. **Wired in this branch.** |

*Removed in this branch:* ~~`security.allow_dangerous`~~ (was DISCONNECT — wizard wrote to config but runtime read from CLI `--allow-dangerous` flag)

---

## 7. GitConfig

> `src/adw/models/config.py:431`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `git.branch_prefix` | USED | GIT | Active | `"feature/"` | `run_lifecycle.py:610` — Prefix for feature branch naming. |
| `git.skip_hooks` | USED | -- | Commented | `false` | `phase_runner.py:1176` — Passed to `create_commit(skip_hooks=...)`. Wired in PR #161. |
| `git.base_branch` | USED | -- | Commented | `None` | `cli/pr.py:604-605` — Base branch for PR creation. Falls back to `"main"`. |

---

## 8. WorktreeConfig

> `src/adw/models/config.py:226`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `worktree.enabled` | USED | -- | Commented | `true` | `orchestrator.py:216`, `run_lifecycle.py:190` — Gates worktree isolation. |
| `worktree.base_dir` | USED | -- | Commented | `"trees"` | `orchestrator.py:219` — Passed to WorktreeManager constructor. |
| `worktree.cleanup_branch_on_remove` | USED | -- | Not generated | `false` | `orchestrator.py:1061` — Passed to `remove_worktree(delete_branch=...)`. Manual edit only. |
| `worktree.max_concurrent` | USED | -- | Commented | `15` | `orchestrator.py:224` — Passed to ConcurrentRunManager for slot limiting. |

### PortRangeConfig (`worktree.port_range`)

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `port_range.backend_start` | USED | PORTS | Conditional | `9100` | `worktree/ports.py:61,89` — Starting port for backend services. |
| `port_range.frontend_start` | USED | PORTS | Conditional | `9200` | `worktree/ports.py:62,89` — Starting port for frontend services. |

*Removed in PR #159/161:* ~~`worktree.preserve_artifacts`~~, ~~`worktree.artifact_manifest_file`~~, ~~`worktree.preserve_on_failure`~~

---

## 9. TaskManagerConfig

> `src/adw/models/config.py:351`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `task_manager.type` | USED | TASK_MANAGER | Conditional | `"none"` | `app.py:274`, `run_lifecycle.py:220,833` — Passed to `TaskManagerFactory.create()`. |
| `task_manager.team_key` | USED | TASK_MANAGER | Conditional | `None` | `linear.py:304` — Team prefix for issue ID detection (e.g., `"RULE"` → `RULE-123`). |
| `task_manager.state_mapping` | USED | TASK_MANAGER | Not generated | `{plan: "In Progress", ...}` | `sync.py:194`, `linear.py:204,394` — Maps ADW phases to external system states. |
| `task_manager.sync_comments` | USED | TASK_MANAGER | Conditional | `false` | `sync.py:225,266,318,367` — Gates comment posting on status transitions. |
| `task_manager.auto_close` | USED | TASK_MANAGER | Commented | `false` | `closer.py:71` — Checked before closing task on PR merge. |
| `task_manager.labels.enabled` | USED | TASK_MANAGER | Not generated | `true` | `bootstrap.py:314` — Gates LabelManager creation. |
| `task_manager.labels.prefix` | USED | TASK_MANAGER | Not generated | `"adw:"` | `labels.py:61` — Prefix for label names (e.g., `"adw:running"`). |

---

## 10. WebhookConfig

> `src/adw/models/webhook.py:76`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `webhook.port` | USED | WEBHOOKS | Conditional | `8000` | `webhook/server.py:72`, `cli/webhook.py:69` — Server port, overridable via CLI. |
| `webhook.host` | USED | WEBHOOKS | Conditional | `"0.0.0.0"` | `webhook/server.py:71`, `cli/webhook.py:68` — Server bind address. |
| `webhook.providers` | USED | WEBHOOKS | Conditional | `{}` | `providers/loader.py:66-67` — Iterated to load enabled providers. |
| `webhook.mappings` | USED | -- | Not generated | `None` | `webhook/server.py:109` — Passed to EventMapper. Complex nested structure, manual edit only. |

### ProviderConfig (per provider)

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `provider.enabled` | USED | WEBHOOKS | Active | `false` | `providers/loader.py:67` — Gates provider initialization. |
| `provider.secret_env` | USED | WEBHOOKS | Active | `None` | `github.py:97`, `linear.py:77` — Via `get_secret()` for webhook signature verification. |
| `provider.command_prefix` | USED | WEBHOOKS | Not generated | `"/adw"` | `github.py:99,102` — Used to build command pattern for comment parsing. |
| `provider.trigger_label` | USED | WEBHOOKS | Not generated | `"adw"` | `github.py:98,295` — Label name that triggers ADW on issues. |

---

## 11. CommandConfig — Phase Shared Fields

> `src/adw/models/command.py:38`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `enabled` | USED | PHASES | Active | `true` | `phase_runner.py:839-850` — Gates phase execution. |
| `timeout_seconds` | USED | PHASES | Conditional | phase-dependent | `phase_runner.py:180` — Passed to LLM executor. Defaults: plan:600 build:1200 validate:600 doc:600 ship:900 |
| `input_files` | USED | PHASES | Conditional | `None` | `phase_runner.py:351-362` — Files loaded and injected as `{{inputs.name}}`. |
| `llm.model` | USED | PHASES | Commented | `None` | `phase_runner.py:181` — Extracted and passed to executor for model selection. |

*Removed in PR #161:* ~~`artifacts`~~ (list of `ArtifactConfig`)
*Removed in this branch:* ~~`pre_hook`~~, ~~`post_hook`~~ (string fields — runtime uses file-based hooks via `pre_hook_path`/`post_hook_path`), ~~`llm.temperature`~~ (was PARTIAL — included in model_dump but never extracted by executor)

---

## 12. ValidateCommandConfig

> `src/adw/models/command.py:136`

Empty typed marker subclass of `CommandConfig`. Preserves the per-phase config class pattern used by `loader.py`.

No phase-specific fields — all 6 previous fields (`enable_evidence`, `enable_review`, `enable_tests`, `max_iterations`, `max_fix_attempts_per_issue`, `stall_threshold`) were injected into template context via `model_dump()` but never consumed by any prompt template. Removed.

*Removed in PR #159:* ~~`test_timeout_seconds`~~, ~~`review_prompt`~~, ~~`review_focus`~~
*Removed in this branch:* ~~`triage_mode`~~, ~~`auto_dismiss_info`~~, ~~`enable_evidence`~~, ~~`enable_review`~~, ~~`enable_tests`~~, ~~`max_iterations`~~, ~~`max_fix_attempts_per_issue`~~, ~~`stall_threshold`~~

---

## 13. DocumentCommandConfig

> `src/adw/models/command.py:228`

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `doc_mappings` | USED | -- | Not generated | `None` | `phase_runner.py:425-428` — Serialized and injected as `{{doc_mappings}}` list. Manual edit only (commented in bundled default config). |

---

## 14. ShipCommandConfig

> `src/adw/models/command.py:270`

### ShipCommandsConfig (`commands:`)

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `commands.version_bump` | USED | PHASES | Conditional | `None` | `phase_runner.py:414-415` — Injected as `{{version_bump_command}}` flat variable. Wired in PR #161. |
| `commands.publish` | USED | PHASES | Conditional | `None` | `phase_runner.py:416-417` — Injected as `{{publish_command}}` flat variable. Wired in PR #161. |

### bypass_ci

| Setting | Runtime | Wizard | Generated YAML | Default | Notes |
|---------|---------|--------|----------------|---------|-------|
| `bypass_ci` | USED | -- | Commented | `true` | `extensions/ship.py:160` — Exposed as `ADW_SHIP_BYPASS_CI` env var for `post.sh`. Default changed to `true` in this branch. |

*Removed in this branch:* ~~`ShipPRConfig`~~ class with ~~`pr.merge_on_success`~~, ~~`pr.delete_branch_on_merge`~~, ~~`pr.merge_method`~~ (post.sh now always uses squash + delete-branch; merge is LLM-approved). ~~`pr.bypass_ci`~~ moved to flat `bypass_ci` field on ShipCommandConfig with default `true`. ~~`post_publish`~~ removed (was TEMPLATE only — never consumed by any prompt template; superseded by `post.sh` hook).

---

## Summary Statistics

| Category | Count | Description |
|----------|-------|-------------|
| USED at Runtime | 51 | Explicitly consumed by running Python code |
| TEMPLATE only | 0 | (`post_publish` removed — was last TEMPLATE-only field) |
| PARTIAL | 0 | (temperature removed in this branch) |
| UNUSED | 0 | (blocked_patterns/blocked_env_files wired in this branch) |
| DISCONNECT | 0 | (allow_dangerous removed in this branch) |
| **Total fields** | **51** | Down from 58 (removed 6 dead ValidateCommandConfig fields + `post_publish`) |

---

## Issues & Findings

### Category C: Hidden — Used but Not Discoverable

Runtime reads these, but they don't appear in wizard or generated files:

1. **`hooks.shell`** — Manual edit only
2. **`hooks.timeout_seconds`** — Manual edit only
3. **`worktree.cleanup_branch_on_remove`** — Manual edit only
4. **`logging.redaction.enabled`** — Manual edit only
5. **`logging.redaction.patterns`** — Manual edit only
6. **`logging.redaction.disable_defaults`** — Manual edit only
7. **`task_manager.state_mapping`** — Wizard collects, but generator doesn't emit
8. **`task_manager.labels.enabled`** — Manual edit only
9. **`task_manager.labels.prefix`** — Manual edit only
10. **`doc_mappings`** — Manual edit only (commented example in bundled defaults)
11. **`webhook.mappings`** — Manual edit only
12. **`provider.command_prefix`** — Not emitted by generator
13. **`provider.trigger_label`** — Not emitted by generator

### Category D: Key Name Mismatch

The YAML generator at `yaml_generator.py:239-241` emits retry keys as:
```yaml
retry:
  max_retries: 3
  base_delay: 1.0    # <-- Model expects "base_delay_seconds"
  max_delay: 60.0    # <-- Model expects "max_delay_seconds"
  multiplier: 2.0
```
But `RetryConfig` expects `base_delay_seconds` and `max_delay_seconds`. Generated YAML will fail to parse into the model due to `extra="forbid"` (if set) or silently ignore the values.

### Resolved in This Branch

All issues from previous Categories A, B, and E have been resolved:
- **Category A** (Dead fields): `security.blocked_patterns` and `security.blocked_env_files` are now wired to `SecurityInterceptor`
- **Category B** (Disconnect): `security.allow_dangerous` removed entirely
- **Category E** (Partial use): `llm.temperature` removed entirely
- Additionally removed: `triage_mode`, `auto_dismiss_info`, `ShipPRConfig` (4 fields), `pre_hook`/`post_hook` (string fields)
