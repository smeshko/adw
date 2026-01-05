# Tech Debt: Orchestrator & PhaseRunner

## Hardcoded Artifact Capture Per Phase

**Location:** `src/adw/core/phase_runner.py:652-719`

**Issue:** Phase-specific artifact capture is hardcoded with `if phase == "..."` checks instead of a generic, config-driven approach.

**Current pattern:**
```python
def _capture_artifacts(self, phase, context, llm_result):
    # Generic artifacts for all phases
    artifacts.append(f"{phase}_output.md")

    # Hardcoded special cases
    if phase == "document":
        artifacts.append("pr_description.md")
    if phase == "verify":
        self._capture_evidence_manifest(context)
    if phase == "build":
        self._capture_git_diff_artifacts(context)
```

**Problems:**
- Violates Open/Closed Principle
- Adding new artifact types requires modifying PhaseRunner
- Custom commands can't define their own artifact capture

**Proposed alternatives:**

| Approach | Implementation |
|----------|----------------|
| Config-driven | `command.yaml` declares `artifacts: [git_diff, evidence_manifest]` |
| Post-hook based | Hooks already receive `artifacts_dir` — they could write directly |
| Plugin system | Register artifact captors per phase type |

**Effort:** Medium
