# ADW Manual Testing Checklist (Sprints 1-10)

Quick reference for testing main workflows and error states.

---

## 1. Basic CLI & Help

```bash
# Version check
adw --version
# Expected: Displays version number (e.g., adw 0.1.0)

# Help output
adw --help
# Expected: Shows all commands (run, resume, status, list, abort, logs, init, pr, cleanup)
```

---

## 2. Project Initialization

```bash
# Init in clean directory
mkdir /tmp/test-adw && cd /tmp/test-adw && git init
adw init
# Expected: Creates .adw/ directory with config, shows success message

# Init with force (re-init)
adw init --force
# Expected: Overwrites existing config

# Init with language
adw init --language python
# Expected: Creates config with python language setting
```

---

## 3. Run Management

```bash
# Start new run (dry-run to test without execution)
adw run "Add login button" --dry-run
# Expected: Shows what would execute, no actual changes

# Start single phase
adw run "Add login button" --phase plan
# Expected: Only executes plan phase, stops after

# Run without worktree isolation (legacy mode)
adw run "Quick fix" --no-worktree
# Expected: Executes in current directory instead of worktree

# Check status of latest run
adw status
# Expected: Shows run ID, status, phases, duration, worktree path

# List recent runs
adw list
# Expected: Table of up to 10 runs with ID, feature, status

# List running only
adw list --running
# Expected: Active runs with worktree paths and ports

# Status as JSON
adw status --json
# Expected: JSON output for scripting
```

---

## 4. Run Recovery & Abort

```bash
# Resume latest incomplete run
adw resume
# Expected: Picks up from last failed/interrupted phase

# Resume specific run
adw resume 01ABC123...
# Expected: Resumes that specific run

# Resume from specific phase
adw resume --from-phase build
# Expected: Starts from build phase, skipping plan

# Abort active run
adw abort <run_id>
# Expected: Stops execution, marks as aborted
```

---

## 5. Logging & Observability

```bash
# View logs for a run
adw logs show <run_id>
# Expected: Recent log entries with timestamps

# Filter by log level
adw logs show <run_id> --level error
# Expected: Only ERROR level entries

# View LLM interactions
adw logs llm <run_id>
# Expected: Shows prompts sent to Claude

# Export debug bundle
adw logs export <run_id> --format json
# Expected: Creates JSON file with full run data
```

---

## 6. Verbosity Levels

```bash
# Quiet mode (errors only)
adw --quiet status
# Expected: Minimal output

# Verbose mode
adw --verbose status
# Expected: Additional detail

# Trace mode (full debug)
adw --trace status
# Expected: All internal debug info
```

---

## 7. Error States to Test

```bash
# Run without init
cd /tmp/empty-dir && adw run "test"
# Expected: Error "No ADW project found. Run 'adw init' first."

# Resume completed run
adw resume <completed_run_id>
# Expected: Error "Run already completed"

# Invalid run ID
adw status INVALIDID
# Expected: Error "Run not found"

# Abort already completed
adw abort <completed_run_id>
# Expected: Error "Cannot abort completed run"

# PR for incomplete run
adw pr <incomplete_run_id>
# Expected: Error "Run must be complete to create PR"

# Max concurrent runs exceeded (15)
# Expected: Error "Maximum concurrent runs reached..."
```

---

## 8. Evidence Gathering

```bash
# For CLI project - triggers command capture
adw run "Add --version flag" --phase verify

# For Web project - triggers screenshot capture
adw run "Add dark mode toggle" --phase verify

# Check evidence artifacts
ls .adw/runs/<run_id>/artifacts/
# Expected: Evidence files (screenshots, command outputs, API responses)
```

---

## 9. Git Integration & Worktrees

```bash
# Verify worktree created during run
git worktree list
# Expected: Shows entry for trees/<run_id>/

# Verify feature branch created
git branch --list "adw/*"
# Expected: adw/<run_id> branch exists

# Check port allocation
cat trees/<run_id>/.ports.env
# Expected: BACKEND_PORT=91XX, FRONTEND_PORT=92XX

# After build phase - check auto-commit
git log --oneline -1
# Expected: Commit message like "[adw] Build: <feature-name>"

# Check generated PR description
cat .adw/runs/<run_id>/artifacts/document/pr_description.md
# Expected: Structured markdown with Summary, Changes, Testing

# Create PR for completed run
adw pr <run_id>
# Expected: Creates PR via gh CLI or outputs manual instructions

# Cleanup worktrees
adw cleanup
# Expected: Lists stale worktrees, prompts for confirmation

# Cleanup specific run with branch deletion
adw cleanup <run_id> --delete-branch
# Expected: Removes worktree and branch
```

---

## Quick Smoke Test Sequence

```bash
# 1. Setup
mkdir /tmp/adw-test && cd /tmp/adw-test && git init
adw init

# 2. Verify init
ls -la .adw/

# 3. Check version/help
adw --version && adw --help

# 4. Dry run (verify worktree would be created)
adw run "Test feature" --dry-run

# 5. List runs
adw list

# 6. Status
adw status

# 7. Verify worktree setup
ls trees/ 2>/dev/null || echo "trees/ created on actual run"

# 8. Check git branches
git branch --list "adw/*"

# 9. Logs help
adw logs --help

# 10. Cleanup help
adw cleanup --help
```
