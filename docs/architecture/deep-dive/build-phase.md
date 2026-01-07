# Build Phase Deep Dive

This document explains the complete execution flow of the Build phase in ADW.

## Overview

The Build phase is the second phase in the ADW pipeline (`plan → build → verify → validate → document`). It implements the feature according to the plan from the previous phase.

**Command:** `adw run "Feature description"` (runs full pipeline) or `adw run "Feature" --phase build --from-run <plan_run_id>`

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Orchestrator calls PhaseRunner.run("build", context)        │
│     - Loads artifacts from previous phases                      │
│     - Prepares template variables                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Load Artifacts from Plan Phase                              │
│     PhaseRunner._build_artifacts_map()                          │
│     - Reads: .adw/runs/<run_id>/artifacts/plan/plan_output.md   │
│     - Stores in: artifacts_map["plan"]["plan_output"]           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Resolve Command                                             │
│     CommandResolver.resolve("build")                            │
│     Searches: .adw/commands/build/ → ~/.adw/commands/build/     │
│               → bundled: src/adw/defaults/commands/build/       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Render Prompt Template                                      │
│     Variables available:                                        │
│       {{plan}}              → plan_output.md content            │
│       {{context}}           → RunContext model                  │
│       {{feature}}           → Feature description               │
│       {{run_id}}            → ULID run identifier               │
│       {{artifacts.plan.*}}  → All plan phase artifacts          │
│       {{worktree_path}}     → Worktree path (if enabled)        │
│                                                                 │
│     Include patterns:                                           │
│       {{shared:workflow.xml}}         → Workflow engine         │
│       {{include:dev-story/...}}       → Command-local files     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. Execute LLM                                                 │
│     ClaudeCodeExecutor spawns Claude CLI:                       │
│     claude --print --output-format stream-json "<prompt>"       │
│                                                                 │
│     Working Dir: worktree path or project root                  │
│     Timeout: 600s (configurable)                                │
│                                                                 │
│     LLM actions during execution:                               │
│       - Reads/writes source files                               │
│       - Runs tests                                              │
│       - Makes git commits (per-task)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. Run Post-Hook                                               │
│     File: src/adw/defaults/commands/build/post.sh               │
│     Action: Auto-commits any remaining changes                  │
│     Commit format: adw(build): <feature> [run_id]               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. Capture Artifacts                                           │
│     - build_output.md  → LLM response text                      │
│     - diff.txt         → Git diff since last commit             │
│     - diff_stats.json  → Files changed, insertions, deletions   │
└─────────────────────────────────────────────────────────────────┘
```

## Input: How Plan is Passed

The plan from the previous phase is passed via template variables:

**1. Artifact Loading** (`phase_runner.py:712-763`):
```python
def _build_artifacts_map(self, run_id, current_phase):
    previous_phases = PHASE_SEQUENCE[:current_idx]  # ["plan"] for build
    for phase in previous_phases:
        phase_map = self._load_phase_artifacts(run_id, phase)
        artifacts_map[phase] = phase_map
    return artifacts_map  # {"plan": {"plan_output": "<content>"}}
```

**2. Convenience Alias** (`phase_runner.py:373-377`):
```python
if "plan" in artifacts_map and "plan_output" in artifacts_map["plan"]:
    variables["plan"] = artifacts_map["plan"]["plan_output"]
```

**3. Template Rendering**:
```markdown
## Plan
{{plan}}
```
Becomes:
```markdown
## Plan
<entire content of plan_output.md>
```

## Output: How Artifacts are Created

### Primary Output: `build_output.md`

Whatever text the LLM writes in response to the prompt is captured as the artifact.

```python
# phase_runner.py:799-810
output_name = f"{phase}_output.md"  # "build_output.md"
self.artifact_manager.store(
    context.run_id,
    phase,
    output_name,
    llm_result.content,  # Raw LLM response text
)
```

### Git Diff Artifacts (Automatic)

After LLM execution, the PhaseRunner captures git changes:

```python
# phase_runner.py:1106-1199
def _capture_git_diff_artifacts(self, context):
    diff_content = capture_diff(since="HEAD~1")
    self.artifact_manager.store_text(run_id, "build", "diff.txt", diff_content)

    stats = get_diff_stats(stat_output, diff_content)
    self.artifact_manager.store_json(run_id, "build", "diff_stats.json", stats)
```

## Artifact Directory Structure

```
.adw/runs/<run_id>/artifacts/build/
├── build_output.md      # LLM response text
├── diff.txt             # Git diff (truncated if >100KB)
└── diff_stats.json      # Diff statistics
```

**diff_stats.json structure:**
```json
{
  "files_changed": 5,
  "insertions": 120,
  "deletions": 30,
  "files": ["src/foo.py", "tests/test_foo.py", ...],
  "binary_files": []
}
```

## How Downstream Phases Use Build Output

| Phase | Variable | Source |
|-------|----------|--------|
| verify | `{{implementation}}` | `build_output.md` |
| document | `{{implementation}}` | `build_output.md` |
| document | `{{artifacts.build.*}}` | Lists diff.txt, diff_stats.json |

Alias creation (`phase_runner.py:378-379`):
```python
if "build" in artifacts_map and "build_output" in artifacts_map["build"]:
    variables["implementation"] = artifacts_map["build"]["build_output"]
```

## Template Include Patterns

The build prompt uses special include syntax:

| Pattern | Resolution | Example |
|---------|------------|---------|
| `{{shared:file}}` | Relative to `commands/` | `{{shared:workflow.xml}}` |
| `{{include:file}}` | Relative to `commands/build/` | `{{include:dev-story/workflow.yaml}}` |
| `{{file:path}}` | Relative to project root | `{{file:docs/spec.md}}` |

## Default Build Command Structure

```
src/adw/defaults/commands/build/
├── prompt.md              # Main prompt template
├── config.yaml            # Phase configuration
├── post.sh                # Auto-commit hook
└── dev-story/             # Bundled workflow files
    ├── workflow.yaml      # Workflow config
    ├── instructions.xml   # Execution steps
    └── checklist.md       # Definition of done
```

## Post-Hook: Auto-Commit

The `post.sh` script runs after LLM execution:

1. Checks if `git.auto_commit` is enabled in `adw.yaml`
2. Stages all changes: `git add -A`
3. Creates commit with format: `adw(build): <feature> [run_id]`
4. Respects `git.skip_hooks` setting

## Key Source Files

| File | Role |
|------|------|
| `src/adw/core/phase_runner.py` | Phase execution, artifact loading/saving |
| `src/adw/core/orchestrator.py` | Phase sequencing |
| `src/adw/commands/template.py` | Template rendering with includes |
| `src/adw/defaults/commands/build/prompt.md` | Default build prompt |
| `src/adw/defaults/commands/build/post.sh` | Auto-commit hook |
| `src/adw/hooks/git_commit.py` | Git commit helper functions |
| `src/adw/hooks/git_diff.py` | Diff capture utilities |

## Configuration

In `adw.yaml`:
```yaml
git:
  enabled: true
  auto_commit: true
  skip_hooks: false
  commit_template: "adw({phase}): {feature}"

llm:
  timeout_seconds: 600
```
