# Epic 14: Interactive Init Wizard

**Goal:** Provide a guided, interactive setup experience for first-time ADW users that walks them through all configuration options with sensible defaults and clear explanations.

**Priority:** Post-MVP
**Dependencies:** Epic 6 (Run Management - existing init command)

---

## Overview

When running `adw init`, users can choose between:
- **Guided Setup:** Interactive wizard walking through all configuration options
- **Minimal Setup:** Quick setup with auto-detected defaults (current behavior)

The wizard covers: basics, git integration, ports, task manager, phase customization, LLM retry, security, and webhooks.

---

## Story 14.1: Wizard Entry Point & Flow Control

As a user running `adw init`,
I want to choose between guided setup and minimal setup,
So that I can get the level of configuration help I need.

**Acceptance Criteria:**

- [ ] `adw init` prompts "Would you like guided setup? [Y/n]"
- [ ] Answering No creates minimal config (language + name only)
- [ ] Answering Yes enters wizard flow
- [ ] `--no-interactive` flag skips prompt, uses minimal setup
- [ ] `--wizard` flag skips prompt, enters wizard directly
- [ ] Detects existing `.adw/` directory
- [ ] Shows warning: "Existing configuration found. This will overwrite all settings."
- [ ] Requires explicit confirmation to proceed with overwrite
- [ ] Wizard state tracks completed steps for back/forward navigation
- [ ] Ctrl+C at any point shows "Setup cancelled. No files created."

---

## Story 14.2: Basics Configuration Step

As a user in the wizard,
I want to configure basic project settings,
So that ADW knows what kind of project I'm working on.

**Acceptance Criteria:**

- [ ] Auto-detects language from project markers (pyproject.toml, package.json, go.mod, etc.)
- [ ] Shows "Language detected: {lang}. Correct? [Y/n]"
- [ ] If No, shows selection: python / javascript / go / rust / java / ruby / php
- [ ] Prompts for platform: "Platform type? [cli] / web / api"
- [ ] Auto-detects test command based on language (pytest, npm test, go test, etc.)
- [ ] Shows "Test command: {cmd} [Enter to accept or type override]"
- [ ] Prompts "Build command: [none] (Enter to skip or type command)"
- [ ] All values stored in wizard state for final generation

---

## Story 14.3: Git Integration Step

As a user in the wizard,
I want to configure git integration,
So that ADW can manage branches and PRs automatically.

**Acceptance Criteria:**

- [ ] Prompts "Enable git integration? [Y/n]"
- [ ] If No, git section disabled in config
- [ ] If Yes:
  - [ ] Auto-detects default branch from git (main/master/develop)
  - [ ] "Base branch: {detected} [Enter or override]"
  - [ ] "Branch prefix: feature/ [Enter or override]"
  - [ ] "Auto-create PR after successful run? [Y/n]"
- [ ] Validates base branch exists in repository (warning if not)
- [ ] Validates branch prefix format (no spaces, valid git branch chars)

---

## Story 14.4: Port Configuration Step (Optional)

As a user in the wizard,
I want to optionally configure port ranges,
So that concurrent runs don't conflict with my other services.

**Acceptance Criteria:**

- [ ] Prompts "Configure port ranges for concurrent runs? [y/N]"
- [ ] Default No uses defaults (9100, 9200)
- [ ] If Yes:
  - [ ] "Backend services start port: 9100 [Enter or override]"
  - [ ] "Frontend services start port: 9200 [Enter or override]"
- [ ] Validates ports are 1-65535
- [ ] Validates backend and frontend ranges don't overlap (given max_concurrent)
- [ ] Shows warning if ports conflict with common services (3000, 5000, 8080)

---

## Story 14.5: Task Manager Setup (Optional, Full)

As a user in the wizard,
I want to configure task manager integration,
So that ADW syncs with my project management tool.

**Acceptance Criteria:**

- [ ] Prompts "Set up task manager integration? [y/N]"
- [ ] If No, task_manager.type remains "none"
- [ ] If Yes:
  - [ ] "Task manager: [Linear]" (Linear only for MVP, extensible)
  - [ ] "Team key (e.g., 'RULE' for RULE-123): ____"
  - [ ] Validates team key format (uppercase letters)
  - [ ] "Sync comments on status changes? [y/N]"
  - [ ] If sync_comments=Yes: "Comment on failures only? [y/N]"
  - [ ] "PR title format: {task_id}: {description} [Enter or override]"
  - [ ] "Enable label management? [Y/n]"
  - [ ] If labels enabled: "Label prefix: adw: [Enter or override]"
  - [ ] "Auto-close task when PR merged? [y/N]"
  - [ ] "Include task labels in context? [Y/n]"
  - [ ] "Include parent task info? [Y/n]"
  - [ ] "Configure state mapping? [y/N]"
  - [ ] If Yes, for each state (plan, build, validate, document, failed):
    - [ ] "{phase} → {default} [Enter or override]"

---

## Story 14.6: Phase Customization (Optional, Full)

As a user in the wizard,
I want to customize individual phase settings,
So that I can tune timeouts, hooks, and inputs for my workflow.

**Acceptance Criteria:**

- [ ] Prompts "Customize phase settings? [y/N]"
- [ ] If No, uses all defaults
- [ ] If Yes:
  - [ ] "Which phases to customize?" [multi-select checklist]
  - [ ] Options: plan, build, validate, document
  - [ ] For each selected phase:
    - [ ] "─── {PHASE} Phase ───"
    - [ ] "Enabled? [Y/n]"
    - [ ] "Timeout (seconds): {default} [Enter or override]"
    - [ ] "Pre-hook script path: [none]"
    - [ ] "Post-hook script path: [none]"
    - [ ] "Add input files? [y/N]"
    - [ ] If Yes, loop: "key=path (empty to finish): ____"
  - [ ] **IF validate phase selected**, additional prompts:
    - [ ] "Enable evidence gathering? [Y/n]"
    - [ ] "Enable code review? [Y/n]"
    - [ ] "Enable tests? [Y/n]"
    - [ ] "Test timeout (seconds): 300 [Enter or override]"
    - [ ] "Max validation iterations: 5 [Enter or override]"
    - [ ] "Triage mode: [auto] / manual / hybrid"
    - [ ] "Review focus areas? [multi-select: security, error_handling, edge_cases]"

---

## Story 14.7: LLM Retry Configuration (Optional)

As a user in the wizard,
I want to configure LLM retry behavior,
So that I can tune how ADW handles transient failures.

**Acceptance Criteria:**

- [ ] Prompts "Configure LLM retry behavior? [y/N]"
- [ ] If No, uses defaults (3 retries, 1s base, 60s max, 2x multiplier)
- [ ] If Yes:
  - [ ] "Max retries: 3 [Enter or override]"
  - [ ] "Base delay (seconds): 1.0 [Enter or override]"
  - [ ] "Max delay (seconds): 60.0 [Enter or override]"
  - [ ] "Delay multiplier: 2.0 [Enter or override]"
- [ ] Validates multiplier > 1.0
- [ ] Validates max_delay >= base_delay

---

## Story 14.8: Security Configuration (Optional)

As a user in the wizard,
I want to configure security settings,
So that I can control what operations ADW is allowed to perform.

**Acceptance Criteria:**

- [ ] Prompts "Configure security settings? [y/N]"
- [ ] If No, uses safe defaults (allow_dangerous=false)
- [ ] If Yes:
  - [ ] "Allow dangerous operations (warns instead of blocking)? [y/N]"
  - [ ] Shows warning if Yes: "⚠️ This reduces safety. Only enable if you understand the risks."
  - [ ] "Add blocked command patterns? [y/N]"
  - [ ] If Yes, loop: "Regex pattern (empty to finish): ____"
  - [ ] "Add blocked env file patterns? [y/N]"
  - [ ] If Yes, loop: "File pattern (empty to finish): ____"
- [ ] Validates regex patterns are valid

---

## Story 14.9: Webhook Server Setup (Optional, Full)

As a user in the wizard,
I want to configure webhook integrations,
So that external events can trigger ADW runs.

**Acceptance Criteria:**

- [ ] Prompts "Set up webhook server? [y/N]"
- [ ] If No, webhooks section uses defaults (disabled)
- [ ] If Yes:
  - [ ] "Webhook server port: 8000 [Enter or override]"
  - [ ] "Webhook server host: 0.0.0.0 [Enter or override]"
  - [ ] "Which providers to configure?" [multi-select: Linear, GitHub]
  - [ ] **For Linear** (if selected):
    - [ ] "Enable Linear webhooks? [Y/n]"
    - [ ] "Secret env variable: LINEAR_WEBHOOK_SECRET [Enter or override]"
    - [ ] "Command prefix: /adw [Enter or override]"
    - [ ] "Trigger label: adw [Enter or override]"
    - [ ] "Configure event mappings? [Y/n]"
    - [ ] If Yes:
      - [ ] "On issue created - trigger run? [Y/n]"
      - [ ] "  Require label? [none or label name]"
      - [ ] "On issue updated - trigger run? [y/N]"
      - [ ] "  Require label? [none or label name]"
      - [ ] "On comment created - trigger run? [Y/n]"
      - [ ] "  Require mention: @adw [Enter or override]"
      - [ ] "  Parse command from comment? [Y/n]"
  - [ ] **For GitHub** (if selected):
    - [ ] Same structure as Linear
    - [ ] "Secret env variable: GITHUB_WEBHOOK_SECRET [Enter or override]"

---

## Story 14.10: Summary & File Generation

As a user completing the wizard,
I want to see a summary and confirm before files are created,
So that I can verify my choices before committing.

**Acceptance Criteria:**

- [ ] Displays Rich panel with full configuration summary:
  ```
  ╭─ Configuration Summary ─────────────────────────────────╮
  │                                                         │
  │  Basics:                                                │
  │    Name: my-project                                     │
  │    Language: python                                     │
  │    Platform: api                                        │
  │    Test: pytest                                         │
  │    Build: python -m build                               │
  │                                                         │
  │  Git: ✓ Enabled (main → feature/, auto-PR)             │
  │  Ports: Default (9100/9200)                            │
  │  Task Manager: Linear (RULE-xxx)                       │
  │  Phases: plan ✎, build ✎, validate (default), doc     │
  │  LLM Retry: Custom (5 retries, 2s base)                │
  │  Security: Default (safe mode)                         │
  │  Webhooks: Linear ✓, GitHub ✗                          │
  │                                                         │
  │  Files to create:                                       │
  │    .adw/project.yaml                                    │
  │    .adw/commands/plan/config.yaml                      │
  │    .adw/commands/build/config.yaml                     │
  │                                                         │
  ╰─────────────────────────────────────────────────────────╯
  ```
- [ ] Prompts "Create configuration? [Y/n]"
- [ ] If No, prompts "Start over or cancel? [s/C]"
- [ ] If Yes:
  - [ ] Creates `.adw/` directory if not exists
  - [ ] Generates `project.yaml` with all settings
  - [ ] Generates `commands/{phase}/config.yaml` for customized phases only
  - [ ] Creates `.adw/.gitignore` (ignore runs/, logs)
- [ ] Shows success message:
  ```
  ✓ Configuration created!

  Next steps:
    adw run "your feature description"
    adw --help for more commands
  ```
- [ ] If file write fails, shows error and doesn't create partial config

---

## Technical Notes

### Dependencies
- Rich for all prompts and display (Prompt, Confirm, Panel, Table)
- Existing config models for validation
- Existing detector for language/test command auto-detection

### Files to Create/Modify
- `src/adw/cli/init.py` - wizard entry point
- `src/adw/cli/wizard/` - new package for wizard steps
  - `__init__.py`
  - `flow.py` - wizard flow controller
  - `basics.py`
  - `git.py`
  - `ports.py`
  - `task_manager.py`
  - `phases.py`
  - `retry.py`
  - `security.py`
  - `webhooks.py`
  - `summary.py`

### Wizard Flow

```
adw init
  │
  ├─ "Would you like guided setup?" [Y/n]
  │     No → Minimal setup (current behavior)
  │     Yes ↓
  │
  ├─ STEP 1: Basics (always)
  │     • Language (auto-detect + confirm)
  │     • Platform (cli/web/api)
  │     • Test command (auto-detect + confirm)
  │     • Build command (optional)
  │
  ├─ STEP 2: Git Integration (always)
  │     • Enable? → base_branch, branch_prefix, auto_create_pr
  │
  ├─ STEP 3: Ports (optional)
  │     • "Configure port ranges?" [y/N]
  │         → backend_start, frontend_start
  │
  ├─ STEP 4: Task Manager (optional)
  │     • "Set up task manager?" [y/N]
  │         → Full Linear config
  │
  ├─ STEP 5: Phase Customization (optional)
  │     • "Customize phases?" [y/N]
  │         → Multi-select phases
  │         → Per-phase: enabled, timeout, hooks, input_files
  │         → IF validate: evidence, review, tests, iterations
  │
  ├─ STEP 6: LLM/Retry (optional)
  │     • "Configure LLM retry behavior?" [y/N]
  │         → max_retries, base_delay, max_delay, multiplier
  │
  ├─ STEP 7: Security (optional)
  │     • "Configure security?" [y/N]
  │         → allow_dangerous, blocked_patterns, blocked_env_files
  │
  ├─ STEP 8: Webhooks (optional)
  │     • "Set up webhooks?" [y/N]
  │         → port, host
  │         → "Which provider?" [Linear / GitHub / Both]
  │         → Full provider config + event mappings
  │
  └─ STEP 9: Summary & Generate
        • Show config summary
        • Confirm & create files
```

---

## Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Foundation                                                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [14-1] Wizard Entry Point & Flow Control                         ║
║  [14-2] Basics Configuration Step                                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: Core Optional Steps (PARALLEL)                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [14-3] Git Integration Step                                      ║
║  [14-4] Port Configuration Step                                   ║
║  [14-5] Task Manager Setup                                        ║
║  [14-6] Phase Customization                                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 3: Advanced Optional Steps (PARALLEL)                       ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [14-7] LLM Retry Configuration                                   ║
║  [14-8] Security Configuration                                    ║
║  [14-9] Webhook Server Setup                                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 4: Completion                                                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [14-10] Summary & File Generation                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Success Criteria

- [ ] New users can fully configure ADW without reading documentation
- [ ] Experienced users can skip wizard with `--no-interactive`
- [ ] Existing projects show clear overwrite warning
- [ ] Generated config files are valid and complete
- [ ] All prompts use Rich for consistent styling
- [ ] Wizard state allows backing up to previous steps
- [ ] Ctrl+C cleanly exits without partial config files

---

## Estimated Effort

| Story | Estimate |
|-------|----------|
| 14-1 Entry Point & Flow | 0.5 day |
| 14-2 Basics | 0.5 day |
| 14-3 Git Integration | 0.25 day |
| 14-4 Ports | 0.25 day |
| 14-5 Task Manager | 0.5 day |
| 14-6 Phase Customization | 0.5 day |
| 14-7 LLM Retry | 0.25 day |
| 14-8 Security | 0.25 day |
| 14-9 Webhooks | 0.5 day |
| 14-10 Summary & Generation | 0.5 day |
| **Total** | **~4 days** |

---
