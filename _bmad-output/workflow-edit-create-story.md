---
stepsCompleted: [1, 2]
target_workflow: _bmad/adw/workflows/create-story
target_workflow_name: create-story
date: 2026-01-06
---

## Workflow Analysis

### Target Workflow

- **Path**: _bmad/adw/workflows/create-story
- **Name**: create-story
- **Module**: adw
- **Format**: Legacy XML (workflow.yaml + instructions.xml)

### Structure Analysis

- **Type**: Document/Action workflow - generates implementation-ready stories
- **Total Steps**: 7 steps in instructions.xml
- **Step Flow**: Sequential with conditional branches
- **Files**: workflow.yaml, instructions.xml, template.md, validation-prompt.md

### Content Characteristics

- **Purpose**: Create comprehensive, implementation-ready story files with exhaustive context analysis to prevent LLM developer mistakes
- **Instruction Style**: Prescriptive XML with action directives
- **User Interaction**: Mixed - ADW environment detection, user prompts, auto-discovery
- **Complexity**: High - extensive conditional logic, external integrations

### Initial Assessment

#### Strengths

- Comprehensive "ultimate context engine" philosophy
- Thorough artifact analysis approach
- Developer guardrails extraction
- Previous story intelligence gathering
- Git history analysis for patterns
- Web research for latest tech specifics

#### Potential Issues

- Heavy coupling to ADW environment variables
- Linear integration adds complexity
- Sprint-status dependency for auto-discovery
- Document search/glob patterns won't work in CI
- Output writes to file instead of stdout
- Template assumes epic/story structure

#### Format-Specific Notes

- Legacy XML format requires careful editing
- workflow.yaml contains variable definitions
- instructions.xml contains all execution logic
- Template sections are referenced by name

### Best Practices Compliance

- **Step File Structure**: N/A (legacy XML format)
- **Frontmatter Usage**: workflow.yaml has variables
- **Menu Implementation**: Limited user interaction
- **Variable Consistency**: Good - centralized in workflow.yaml

---

## User Goals Summary

### Primary Goal: CI Pipeline Integration

Make the workflow usable in CI where:
- Context is injected via `{{context}}` and `{{feature_description}}`
- Final output must be story contents to stdout
- No interactive prompts or user intervention

### Items to Remove

| Category | Specific Items |
|----------|----------------|
| ADW Logic | ADW_STATE_FILE, ADW_ISSUE_BODY, jq state updates |
| Linear Integration | All Linear API calls, issue creation, status updates |
| Sprint Status | All sprint-status.yaml reads/updates, auto-discovery |
| Document Search | Glob patterns, file discovery, sharded document loading |

### Items to Keep/Adapt

| Component | Action |
|-----------|--------|
| Core artifact analysis (Step 3) | Adapt to use injected context |
| Previous story/implementation search | Keep - codebase search |
| Git intelligence | Keep - recent commits, patterns |
| Architecture analysis (Step 4) | Adapt to use injected context |
| Web research (Step 5) | Keep entirely |
| Story generation (Step 6) | Adapt template, output to stdout |

### Template Changes Required

- Remove epic/story number assumptions
- Generalize for any feature request
- Keep developer context sections
- Keep implementation task structure

---

## Improvement Goals (Step 2)

### Context Input Specification

The workflow receives full `{{context}}` object:

```python
{{context}} = {
    # Primary input - the user's request
    "feature_description": "Add user authentication with OAuth2",

    # Documents to analyze
    "input_files": ["docs/architecture.md", "docs/prd.md", ...],

    # Run metadata
    "run_id": "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    "current_phase": "plan",
    "phase_history": [...],
    "artifacts": {...},
    "platform": "cli",  # or web, mobile, backend
    # ... other RunContext fields
}
```

### Output Specification

- **Format:** Pure markdown
- **Destination:** stdout (final LLM message is the story content)
- **No wrapping:** Just the implementation plan content

### Missing Context Handling

- **Strategy:** Graceful degradation
- Skip sections silently when context unavailable
- Rely on codebase discovery to fill gaps
- No error messages or placeholders for missing docs

### Prioritized Improvements

| Priority | Goal | Details |
|----------|------|---------|
| CRITICAL | Full context parsing | Parse entire `{{context}}` object including feature_description, input_files, platform, etc. |
| CRITICAL | Read input_files | Load each file from input_files list |
| CRITICAL | CI output | Pure markdown to stdout as final message |
| CRITICAL | Remove ADW deps | ADW_STATE_FILE, ADW_ISSUE_BODY, jq state updates |
| CRITICAL | Remove Linear | All Linear API calls, issue creation, status updates |
| CRITICAL | Remove sprint-status | All reads/updates, auto-discovery logic |
| CRITICAL | Remove doc search | Glob patterns, file discovery - docs come via input_files |
| CRITICAL | Generalize template | Remove epic/story number assumptions |
| IMPORTANT | Keep codebase discovery | Previous implementations, git history analysis |
| IMPORTANT | Keep web research | Latest tech research capability |
| IMPORTANT | Graceful fallback | Skip missing context silently, discover what's needed |

---

_Goals documented on 2026-01-06_
