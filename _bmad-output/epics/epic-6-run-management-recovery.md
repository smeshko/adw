# Epic 6: Run Management & Recovery

**Goal:** Enable users to start, resume, abort, and monitor runs through CLI commands. This epic provides the user-facing interface to the orchestration capabilities.

## Story 6.1: Start New Run with Feature Description

As a user,
I want to start a new run by providing a feature description,
So that I can begin AI-assisted development.

**Acceptance Criteria:**

**Given** command `adw run "Add user authentication"`
**When** executed
**Then** a new run is created with ULID run_id
**And** the run header panel displays run ID, feature, started timestamp (UX-12)

**Given** a new run starts
**When** project config exists at `.adw/project.yaml`
**Then** configuration is loaded and validated (NFR9)

**Given** no project config exists
**When** run is started
**Then** default configuration is used for common project types (NFR19)

**Given** the feature description
**When** it contains special characters
**Then** they are properly escaped in templates

**Given** CLI startup
**When** I measure time to first output
**Then** it's under 2 seconds (NFR1)

---

## Story 6.2: Resume Failed or Interrupted Run

As a user,
I want to resume a run from where it failed or was interrupted,
So that I don't lose progress.

**Acceptance Criteria:**

**Given** a run that failed at the Build phase
**When** I run `adw resume <run_id>`
**Then** it continues from the Build phase using Plan artifacts

**Given** a run that was interrupted
**When** I run `adw resume` without run_id
**Then** it resumes the most recent incomplete run

**Given** a completed run
**When** resume is attempted
**Then** ConfigError is raised with message "Run already completed"

**Given** a run with corrupted state
**When** resume is attempted
**Then** StateError is raised with suggestion to check snapshots

**Given** successful resume
**When** the resumed phase completes
**Then** it continues to the next phase automatically

---

## Story 6.3: Check Run Status

As a user,
I want to check the status of any run,
So that I know its current state and outcome.

**Acceptance Criteria:**

**Given** command `adw status <run_id>`
**When** the run exists
**Then** it displays: run_id, feature, status, current/last phase, started_at, completed_at

**Given** command `adw status` without run_id
**When** runs exist
**Then** it shows status of the most recent run

**Given** the run is complete
**When** status is shown
**Then** it includes: total duration, phases completed, artifact count

**Given** the run failed
**When** status is shown
**Then** it includes: error message, suggestion, resume command (UX-3)

**Given** an invalid run_id
**When** status is requested
**Then** ConfigError is raised with code "RUN_NOT_FOUND"

---

## Story 6.4: List Recent Runs

As a user,
I want to list my recent runs,
So that I can find runs to resume or inspect.

**Acceptance Criteria:**

**Given** command `adw list`
**When** runs exist
**Then** it displays recent runs (default: 10) sorted by creation time

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, feature (truncated), status, started_at

**Given** command `adw list --limit 20`
**When** executed
**Then** up to 20 runs are displayed

**Given** command `adw list --status failed`
**When** executed
**Then** only failed runs are displayed

**Given** no runs exist
**When** list is requested
**Then** message "No runs found" is displayed

---

## Story 6.5: Abort Running Execution

As a user,
I want to abort a running execution,
So that I can stop a stuck or unwanted run.

**Acceptance Criteria:**

**Given** Ctrl+C during a run
**When** pressed
**Then** prompt "Abort run?" with Y/N confirmation (UX-8)

**Given** abort confirmed
**When** processed
**Then** current state is saved, run status set to "aborted"

**Given** abort cancelled
**When** processed
**Then** run continues from where it was

**Given** command `adw abort <run_id>`
**When** a run is in progress
**Then** the run is aborted remotely (if supported)

**Given** abort of a run not in progress
**When** attempted
**Then** ConfigError is raised with "Run is not active"

---

## Story 6.6: Initialize New Project

As a user,
I want to initialize a project with default configuration,
So that I can start using adw in my repository.

**Acceptance Criteria:**

**Given** command `adw init` in a directory
**When** `.adw/` doesn't exist
**Then** it creates `.adw/` with `project.yaml` containing defaults

**Given** the project appears to be Python
**When** init detects `pyproject.toml`
**Then** defaults are set appropriately (language: python, test_command: pytest)

**Given** the project appears to be Node.js
**When** init detects `package.json`
**Then** defaults are set appropriately (language: javascript, test_command: npm test)

**Given** `.adw/` already exists
**When** init is run
**Then** ConfigError is raised with "Project already initialized"

**Given** command `adw init --force`
**When** `.adw/` exists
**Then** configuration is regenerated with fresh defaults

---
