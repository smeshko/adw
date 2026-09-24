# Document Phase Deep Dive

This document explains the complete execution flow of the Document phase in ADW.

## Overview

The Document phase is the fourth phase in the ADW pipeline (`plan → build → validate → document → ship`). It analyzes changes for documentation needs, creates feature docs for significant changes, and generates the PR description.

**Command:** `adw run "Feature description"` (runs full pipeline) or `adw run "Feature" --phase document --from-run <validate_run_id>`

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Orchestrator calls PhaseRunner.run("document", context)     │
│     - Loads artifacts from build and validate phases            │
│     - Prepares template variables                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Load Artifacts from Previous Phases                         │
│     From build:                                                 │
│       - artifacts.build.build_output  → Implementation summary  │
│       - artifacts.build.diff          → Git diff content        │
│       - artifacts.build.diff_stats    → Change statistics       │
│     From validate:                                              │
│       - artifacts.validate.*          → Validation evidence     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Render Prompt Template                                      │
│     Includes:                                                   │
│       - {{shared:workflow.xml}}       → Workflow engine         │
│       - {{include:document-feature/workflow.yaml}}              │
│       - {{include:document-feature/instructions.xml}}           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Execute LLM (5-Step Workflow)                               │
│     Step 1: Detect changes, load docs/CONDITIONAL_DOCS.md       │
│     Step 2: Analyze inline/external doc gaps, eval significance │
│     Step 3: Update docs, create feature doc if significant      │
│     Step 4: Generate documentation report                       │
│     Step 5: Generate PR description as final output             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. Capture Artifacts                                           │
│     - document_output.md  → Full LLM response                   │
│     - pr_description.md   → Via DocumentExtension               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. Run Post-Hook (post.sh)                                     │
│     Extracts from LLM output:                                   │
│       - feature_doc.md (between # FEATURE DOC OUTPUT markers)   │
│       - document_output.md (full LLM output)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. Auto-Commit Changes                                         │
│     Commits doc updates made by LLM                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  8. DocumentExtension.on_complete()                             │
│     core.pr.create_pr(context, body, base=git.base_branch):     │
│       - Push branch to remote                                   │
│       - Create PR via gh CLI                                    │
│       - Update context with pr_url or the failure reason        │
└─────────────────────────────────────────────────────────────────┘
```

## Input: How Previous Phase Artifacts Are Passed

```python
# PhaseRunner._build_artifacts_map()
artifacts_map = {
    "plan": {"plan_output": "<plan content>"},
    "build": {
        "build_output": "<implementation summary>",
        "diff": "<git diff content>",
        "diff_stats": "<json stats>"
    },
    "validate": {"validate_output": "<validation evidence>"}
}
```

**Template Access:**
```markdown
{{artifacts.build.build_output}}   → Implementation from build phase
{{artifacts.build.diff}}           → Git diff of changes
{{artifacts.build.diff_stats}}     → Files changed, insertions, deletions
{{artifacts.validate.*}}           → All validate phase artifacts
```

## The 5-Step LLM Workflow

| Step | Goal | Key Actions |
|------|------|-------------|
| 1 | Initialize | Detect changed files, load CONDITIONAL_DOCS.md |
| 2 | Analyze | Check inline docs, external docs, evaluate significance |
| 3 | Update | Add missing docs, create feature doc if significant |
| 4 | Report | Generate documentation summary |
| 5 | PR Description | Generate final PR description output |

### Significance Criteria (Triggers Feature Doc)

- New architectural pattern
- New feature area
- Complex integration
- Non-obvious decisions
- Reusable pattern
- Configuration system
- Breaking changes
- Security/performance patterns

## Output: Artifacts Created

### Primary Output: `document_output.md`

Full LLM response including documentation report and PR description.

### PR Description: `pr_description.md`

Created by DocumentExtension from LLM's final output:

```python
# DocumentExtension.extra_artifacts()
def extra_artifacts(self, context, llm_result):
    content = llm_result.final_output or llm_result.content
    return [("pr_description.md", content)]
```

### Feature Documentation (Conditional)

If changes are significant, LLM creates:
- `docs/features/<feature-name>.md` - Feature documentation
- Updates `docs/CONDITIONAL_DOCS.md` - Discoverability guide

## Artifact Directory Structure

```
.adw/runs/<run_id>/artifacts/document/
├── document_output.md    # Full LLM response
├── pr_description.md     # Extracted PR description
└── feature_doc.md        # Feature doc (if significant changes)
```

## DocumentExtension: PR Creation

**File:** `src/adw/core/extensions/document.py`

The extension opens the run's PR after phase completion through
`adw.core.pr.create_pr`, the same function `adw pr` calls:

```python
# DocumentExtension.on_complete()
def on_complete(self, context, result):
    context = context.model_copy(update={"pr_creation_attempted": True})
    try:
        body = load_pr_description(self._runs_dir / context.run_id)
        pr_url = create_pr(context, body, base=self._git_config.base_branch)
    except ADWError as e:
        return context.model_copy(update={
            "pr_creation_failed": True,
            "pr_failure_reason": str(e),  # "[GH_AUTH_ERROR] ...\nSuggestion: ..."
        })
    return context.model_copy(update={"pr_url": pr_url})
```

`create_pr` pushes the branch, adds the title and the Linear link, runs
`gh pr create`, and maps `gh` failures to `ADWError` codes. When `gh` reports
that the PR already exists, it returns the existing PR's URL. The completion
comment and the pipeline summary read `context.pr_url` and
`context.pr_failure_reason`; after a failure the summary suggests
`adw pr <run-id>` to retry.

## How Downstream Phases Use Document Output

| Phase | Variable | Source |
|-------|----------|--------|
| ship | `context.pr_url` | PR URL from DocumentExtension |
| ship | `{{artifacts.document.pr_description}}` | PR description artifact |

## Post-Hook: Artifact Extraction

The `post.sh` script extracts structured content from LLM output:

1. **Feature Doc** - Content between `# FEATURE DOC OUTPUT` markers
2. **Full Output** - Saved as `document_output.md`

It leaves `pr_description.md` alone: `DocumentExtension` is its only writer.

## Default Document Command Structure

```
src/adw/defaults/commands/document/
├── prompt.md                    # Main prompt template
├── config.yaml                  # Phase configuration
├── post.sh                      # Artifact extraction hook
└── document-feature/            # Workflow files
    ├── workflow.yaml            # Workflow config & persona
    └── instructions.xml         # 5-step workflow instructions
```

## Key Source Files

| File | Role |
|------|------|
| `src/adw/core/phase_runner.py` | Phase execution, artifact loading |
| `src/adw/core/extensions/document.py` | PR creation extension |
| `src/adw/core/pr.py` | PR creation via gh CLI (`create_pr`) |
| `src/adw/cli/pr.py` | `adw pr` command |
| `src/adw/defaults/commands/document/prompt.md` | Default prompt |
| `src/adw/defaults/commands/document/post.sh` | Artifact extraction |
| `src/adw/defaults/commands/document/document-feature/instructions.xml` | Workflow steps |

## Configuration

In `config.yaml`:
```yaml
timeout_seconds: 600

artifacts:
  - name: document_output
    required: true
  - name: pr_description
    required: true
  - name: feature_doc
    required: false  # Only if significant
```

In `adw.yaml` (project config):
```yaml
git:
  base_branch: main      # Target branch for PRs (default: main)
```

## Context Fields Updated

| Field | When Set |
|-------|----------|
| `pr_creation_attempted` | PR creation was attempted |
| `pr_url` | PR created successfully |
| `pr_creation_failed` | PR creation failed |
| `pr_failure_reason` | `str(ADWError)` on failure: code, message, suggestion |
