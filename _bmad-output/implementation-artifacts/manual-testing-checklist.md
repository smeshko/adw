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

---

## 9. Git Integration (Epic 9)

### 9.1 Feature Branch Creation

```bash
# Verify git integration enabled
cat .adw/project.yaml | grep -A5 "git:"
# Expected: git.enabled: true

# Start run with git integration
adw run "Add user authentication"
# Expected: Creates branch feature/add-user-authentication

# Verify branch created
git branch --list "feature/*"
# Expected: feature/add-user-authentication listed

# Test branch name sanitization
adw run "Fix bug #123 with special/chars"
# Expected: Creates branch feature/fix-bug-123-with-special-chars

# Test existing branch (switch instead of create)
adw run "Add user authentication"
# Expected: Switches to existing branch, no error

# Test with uncommitted changes
echo "test" > uncommitted.txt
adw run "New feature"
# Expected: Error suggesting to commit or stash changes
rm uncommitted.txt
```

### 9.2 Auto-Commit via Post-Hook

```bash
# After build phase completes
git log --oneline -1
# Expected: Commit message like "[adw] Build: <feature-name>"

# Verify commit includes run_id
git log -1 --format="%B"
# Expected: Contains run_id reference in commit body

# Test no changes scenario
# (Make a run that produces no file changes)
# Expected: Commit is skipped silently, no error

# Disable auto-commit in project.yaml
# git:
#   auto_commit: false
adw run "Test feature" --phase build
# Expected: No automatic commit made
```

### 9.3 Git Diff Artifact

```bash
# After build phase
cat .adw/runs/<run_id>/artifacts/build/diff.txt
# Expected: Shows git diff output

# Verify diff size limit
# For large changes, verify truncation
wc -c .adw/runs/<run_id>/artifacts/build/diff.txt
# Expected: < 100KB (truncated if larger)

# Test with no commits (staged changes)
# Expected: Captures staged diff instead
```

### 9.4 PR Description Generation

```bash
# After document phase
cat .adw/runs/<run_id>/artifacts/document/pr_description.md
# Expected: Structured markdown with Summary, Changes, Testing sections

# Verify evidence references included
grep -i "screenshot\|evidence" .adw/runs/<run_id>/artifacts/document/pr_description.md
# Expected: References to evidence items if any were captured
```

### 9.5 PR Creation Command

```bash
# Create PR for completed run
adw pr <run_id>
# Expected: Opens PR with pre-filled title and description

# With gh CLI available
which gh && adw pr <run_id>
# Expected: Uses gh pr create, shows PR URL

# Without gh CLI
# Expected: Outputs description and manual instructions

# Attempt PR for incomplete run
adw pr <incomplete_run_id>
# Expected: Error "Run must be complete to create PR"

# Verify PR URL stored
cat .adw/runs/<run_id>/artifacts/pr_url.txt
# Expected: Contains created PR URL
```

---

## 10. Worktree Isolation (Epic 10)

### 10.1 Worktree Creation & Lifecycle

```bash
# Start run (worktree mode)
adw run "Test worktree feature"
# Expected: Creates worktree at trees/<run_id>/

# Verify worktree created
git worktree list
# Expected: Shows entry for trees/<run_id>/

# Verify branch created
git branch --list "adw/*"
# Expected: adw/<run_id> branch exists

# After successful completion
ls trees/
# Expected: Worktree removed (if cleanup_on_success: true)

# After failed run (preserve_on_failure: true)
# Expected: Worktree preserved for debugging

# Legacy mode
adw run "Test feature" --no-worktree
# Expected: Execution happens in current directory
```

### 10.2 Directory Structure

```bash
# Verify trees directory setup
ls -la trees/
# Expected: Directory exists with .gitignore

cat trees/.gitignore
# Expected: Contains * (ignores all worktree contents)

# Check project .gitignore
grep "trees/" .gitignore
# Expected: trees/ is listed

# Verify worktree structure
ls -la trees/<run_id>/
# Expected: Full project copy including .adw/ directory

# Check artifacts location
ls trees/<run_id>/.adw/runs/<run_id>/
# Expected: Run artifacts stored in worktree

# After completion - artifact preservation
ls .adw/runs/<run_id>/
# Expected: Key artifacts copied from worktree before removal
```

### 10.3 Port Allocation

```bash
# Check port allocation file
cat trees/<run_id>/.ports.env
# Expected: BACKEND_PORT=91XX, FRONTEND_PORT=92XX

# Verify slot-based allocation
# For run with slot 0: ports 9100/9200
# For run with slot 5: ports 9105/9205

# Test port in use scenario
# (Start a service on port 9100)
lsof -i :9100
# Expected: Next available slot tried (up to 3 attempts)

# Verify ports are unique across concurrent runs
# Run multiple adw instances
# Expected: Each gets different port pair
```

### 10.4 Concurrent Run Management

```bash
# Start multiple runs in parallel
adw run "Feature 1" &
adw run "Feature 2" &
adw run "Feature 3" &
# Expected: Each gets own worktree and ports

# List running
adw list --running
# Expected: Shows all active runs with worktree paths and ports

# Attempt 16th concurrent run
# (After starting 15 runs)
adw run "Feature 16"
# Expected: Error "Maximum concurrent runs reached..."

# Cleanup orphaned worktrees
adw cleanup
# Expected: Lists stale worktrees, prompts for confirmation

# Force cleanup without confirmation
adw cleanup --force
# Expected: Removes stale worktrees immediately
```

### 10.5 Worktree Context in Phases

```bash
# Verify phase executes in worktree
# During build phase, check working directory
# Expected: Working directory is trees/<run_id>/

# Check environment variable
echo $ADW_WORKTREE_PATH
# Expected: Absolute path to worktree

# Template variable in prompt
# {{worktree_path}} in phase prompt
# Expected: Resolves to absolute worktree path

# Verify artifact paths are relative
cat .adw/runs/<run_id>/artifacts/manifest.json
# Expected: Paths relative to worktree root
```

### 10.6 Branch Management

```bash
# Verify branch naming
git branch --list "adw/*"
# Expected: adw/<run_id> format

# After run with PR created
git branch --list "adw/<run_id>"
# Expected: Branch preserved (needed for PR)

# Cleanup with branch deletion
adw cleanup <run_id> --delete-branch
# Expected: Both worktree and branch removed

# Cleanup without branch deletion (default)
adw cleanup <run_id>
# Expected: Worktree removed, branch preserved
```

---

## 11. Worktree Error States

```bash
# No git repository
cd /tmp/no-git && adw run "test"
# Expected: Error about git repository required

# Dirty worktree
echo "test" > trees/<run_id>/dirty.txt
adw cleanup <run_id>
# Expected: Warning about uncommitted changes

# Branch already exists
git branch adw/test-branch
adw run "Test" # (if it would create adw/test-branch)
# Expected: Handles gracefully (new name or uses existing)

# Port range exhausted
# (All 15 slots in use with port conflicts)
# Expected: Clear error message with suggestion
```

---

## Quick Smoke Test Sequence (Extended)

```bash
# 1-7. Original smoke test sequence...

# 8. Test worktree isolation
adw run "Smoke test feature" --dry-run
ls trees/
# Expected: Worktree would be created

# 9. Test git integration
git branch --list "feature/*"
# Expected: Feature branches listed

# 10. Check port allocation
cat .adw/project.yaml | grep -A5 "port_range"
# Expected: Port configuration visible
```
