# ADW Manual Testing Checklist (Sprints 1-8)

Quick reference for testing main workflows and error states.

---

## 1. Basic CLI & Help

```bash
# Version check
adw --version
# Expected: Displays version number (e.g., adw 0.1.0)

# Help output
adw --help
# Expected: Shows all commands (run, resume, status, list, abort, logs, init)
```

---

## 2. Project Initialization

```bash
# Init in clean directory
mkdir /tmp/test-adw && cd /tmp/test-adw
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

# Check status of latest run
adw status
# Expected: Shows run ID, status, phases, duration

# List recent runs
adw list
# Expected: Table of up to 10 runs with ID, feature, status

# List with filters
adw list --limit 5 --status failed
# Expected: Only failed runs, max 5

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

# Error: Abort non-existent run
adw abort 01NONEXISTENT
# Expected: Error message "Run not found"
```

---

## 5. Logging & Observability

```bash
# View logs for a run
adw logs show <run_id>
# Expected: Recent log entries with timestamps

# View with tail limit
adw logs show <run_id> --tail 50
# Expected: Last 50 entries

# Filter by log level
adw logs show <run_id> --level error
# Expected: Only ERROR level entries

# Search logs
adw logs search "failed" --run <run_id>
# Expected: Matching log entries highlighted

# View LLM interactions
adw logs llm <run_id>
# Expected: Shows prompts sent to Claude

# View only responses
adw logs llm <run_id> --response
# Expected: Shows Claude's responses

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

# Resume non-existent phase
adw resume --from-phase nonexistent
# Expected: Error about invalid phase name
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

## Quick Smoke Test Sequence

```bash
# 1. Setup
mkdir /tmp/adw-test && cd /tmp/adw-test
adw init

# 2. Verify init
ls -la .adw/

# 3. Check version/help
adw --version && adw --help

# 4. Dry run
adw run "Test feature" --dry-run

# 5. List (should be empty or show dry run)
adw list

# 6. Status (latest)
adw status

# 7. Logs help
adw logs --help
```
