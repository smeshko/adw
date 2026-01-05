# Tech Debt: PhaseRunner Template Aliases

## Hardcoded Convenience Aliases

**Location:** `src/adw/core/phase_runner.py:331-339`

**Issue:** Template aliases are hardcoded with inconsistent naming, providing shortcuts like `{{plan}}` instead of explicit paths like `{{artifacts.plan.plan_output}}`.

**Current pattern:**
```python
# Add convenience aliases for common artifact references
# e.g., {{plan}} instead of {{artifacts.plan.plan_output}}

if "plan" in artifacts_map and "plan_output" in artifacts_map["plan"]:
    variables["plan"] = artifacts_map["plan"]["plan_output"]
if "build" in artifacts_map and "build_output" in artifacts_map["build"]:
    variables["implementation"] = artifacts_map["build"]["build_output"]
if "verify" in artifacts_map and "verify_output" in artifacts_map["verify"]:
    variables["output"] = artifacts_map["verify"]["output"]
```

**Problems:**

| Alias | Maps To | Issue |
|-------|---------|-------|
| `{{plan}}` | `artifacts.plan.plan_output` | Identity mapping - redundant |
| `{{implementation}}` | `artifacts.build.build_output` | Semantic rename - inconsistent |
| `{{output}}` | `artifacts.verify.verify_output` | Generic name - ambiguous |

- **Inconsistent naming:** `plan` stays `plan`, `build` becomes `implementation`, `verify` becomes `output`
- **Incomplete coverage:** No aliases for `document` or `validate` phases
- **Hardcoded:** Adding new aliases requires modifying PhaseRunner
- **Ambiguous:** `{{output}}` could mean any phase's output

## Proposed Fix

**Remove aliases entirely** - use explicit paths for clarity.

### Changes Required

1. **Delete alias block** in `phase_runner.py:331-339`

2. **Update default prompts:**

| File | Change |
|------|--------|
| `commands/build/prompt.md` | `{{plan}}` → `{{artifacts.plan.plan_output}}` |
| `commands/verify/prompt.md` | `{{implementation}}` → `{{artifacts.build.build_output}}` |
| `commands/document/prompt.md` | `{{implementation}}` → `{{artifacts.build.build_output}}` |
| `commands/validate/prompt.md` | `{{output}}` → `{{artifacts.verify.verify_output}}` |

3. **Update tests:** Search for alias usage in template assertions

**Effort:** Low (~15 lines across 4 files)
