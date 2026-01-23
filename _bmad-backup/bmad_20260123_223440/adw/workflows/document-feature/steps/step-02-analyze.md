---
name: 'step-02-analyze'
description: 'Analyze changed files for documentation gaps and determine if changes are significant'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/4-implementation/document'

# File References
thisStepFile: '{workflow_path}/steps/step-02-analyze.md'
nextStepFile: '{workflow_path}/steps/step-03-update.md'
reportStepFile: '{workflow_path}/steps/step-04-report.md'
workflowFile: '{workflow_path}/workflow.md'
---

# Step 2: Analyze Documentation

## STEP GOAL:

To analyze changed files for documentation completeness, check both inline and external documentation needs, and determine if the changes are SIGNIFICANT enough to warrant feature documentation.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - analyze efficiently
- 🔄 Auto-proceed to next step when complete

### Role Reinforcement:

- ✅ You are a documentation analyst and knowledge architect
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

- 🎯 Analyze only - no updates in this step
- ✅ Check both inline and external docs
- ✅ Determine if changes are SIGNIFICANT
- ✅ Identify specific gaps with locations

## EXECUTION PROTOCOLS:

- 🎯 Analyze all changed files systematically
- 💾 Track all issues found with file, line, and severity
- 📖 Evaluate significance criteria for feature doc decision
- 🚫 Do not modify any files in this analysis step

## CONTEXT BOUNDARIES:

- Available context: Configuration from step 1, list of changed files, conditional docs guide
- Focus: Documentation gap analysis and significance evaluation
- Limits: Analysis only, no file modifications
- Dependencies: Completed initialization step with change list

## ANALYSIS SEQUENCE:

### 1. Initialize Analysis Results

```
analysis = {
  inlineIssues: [],
  externalIssues: [],
  isSignificant: false,
  significanceReasons: [],
  suggestedFeatureDoc: null,
  suggestedConditions: [],
  allGood: true
}
```

### 2. Analyze Inline Documentation

If `check_inline` is enabled:

For each changed file, check for:

**Functions/Methods**: Do they have doc comments?
**Classes/Types**: Are they documented?
**Complex logic**: Are there explanatory comments?
**Public APIs**: Are exports documented?

**Identify issues:**
```
{
  file: "path/to/file",
  line: 42,
  type: "missing_jsdoc",
  element: "function processData",
  severity: "required" | "recommended"
}
```

### 3. Analyze External Documentation

If `check_external` is enabled:

**Check if changes require external doc updates:**
- New features → Should be in README or docs/
- API changes → Should be in API documentation
- Config changes → Should be in setup/config docs
- Breaking changes → Should be prominently documented

**Check configured doc_locations:**
For each location, check if updates are needed.

### 4. Determine Significance (KEY STEP)

Evaluate if changes warrant a **feature doc**:

**SIGNIFICANT changes (create feature doc):**

- [ ] **New architectural pattern** - A way of doing things that will be repeated
- [ ] **New feature area** - A cohesive set of functionality
- [ ] **Complex integration** - External service, API, or system integration
- [ ] **Non-obvious decisions** - Why something was done a certain way
- [ ] **Reusable pattern** - Code pattern others should follow
- [ ] **Configuration system** - New config options or environment setup
- [ ] **Breaking changes** - Changes that affect how others use the code
- [ ] **Security implementation** - Auth, permissions, encryption patterns
- [ ] **Performance optimization** - Non-obvious performance patterns
- [ ] **Testing patterns** - New testing approaches or fixtures

**NOT significant (just inline/external docs):**
- Bug fixes
- Minor refactoring
- Typo fixes
- Dependency updates
- Style changes
- Single-file changes with no broader implications

### 5. Generate Feature Doc Proposal (if significant)

If changes are significant:

**Generate suggested feature doc:**
```
suggestedFeatureDoc = {
  filename: "feature-{descriptive-name}.md",
  title: "[Feature Title]",
  overview: "[2-3 sentence summary]",
  sections: [
    "What Was Built",
    "Technical Implementation",
    "How to Use",
    "Configuration",
    "Notes"
  ]
}
```

**Generate suggested conditions for conditional docs:**
```
suggestedConditions = [
  "When working with [feature area]",
  "When implementing [related functionality]",
  "When troubleshooting [specific issues]"
]
```

### 6. Display Analysis Results

"**Documentation Analysis Complete**

**Inline Documentation:**

| File | Issue | Element | Severity |
|------|-------|---------|----------|
| [file] | [issue type] | [element] | Required/Recommended |

**External Documentation:**

| Doc File | Section | Issue |
|----------|---------|-------|
| [file] | [section] | [issue] |

**Significance Assessment:**

| Criteria | Met? | Details |
|----------|------|---------|
| New pattern | ✅/❌ | [details] |
| New feature area | ✅/❌ | [details] |
| Complex integration | ✅/❌ | [details] |
| ... | ... | ... |

**Recommendation:** [Create feature doc / Standard docs only]

**Suggested Feature Doc:** (if significant)
- Filename: `docs/features/[name].md`
- Conditions for guide:
  - [condition 1]
  - [condition 2]
  - [condition 3]"

### 7. Route Based on Results

#### IF no issues AND not significant:
Display: "All documentation is up to date!"
Load, read entire file, then execute `{reportStepFile}`

#### IF issues found OR significant:
Display: "Documentation updates needed. Proceeding..."
Store analysis results in context
Load, read entire file, then execute `{nextStepFile}`

---

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN all changed files are analyzed and significance is evaluated, will you then:
- Route to `{reportStepFile}` if no issues found AND not significant
- Route to `{nextStepFile}` if issues found OR significant changes detected

---

## SIGNIFICANCE EXAMPLES:

### SIGNIFICANT - Create feature doc:

**Example 1: New Authentication System**
- Files: `auth/*.ts`, `middleware/auth.ts`
- Why: New pattern that will be referenced when adding protected routes
- Feature doc: `authentication-patterns.md`
- Conditions: "When adding protected routes", "When implementing auth flows"

**Example 2: CSV Export Utility**
- Files: `utils/export.ts`, `api/export.ts`
- Why: Reusable pattern for exporting data
- Feature doc: `data-export-patterns.md`
- Conditions: "When implementing export functionality", "When working with file downloads"

### NOT SIGNIFICANT - Standard docs only:

**Example 1: Bug fix**
- Files: `utils/format.ts` (fix null check)
- Why: Single fix, no new pattern
- Action: Just ensure function has JSDoc

**Example 2: Dependency update**
- Files: `package.json`, `package-lock.json`
- Why: No code pattern changes
- Action: Update README if major version change

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All changed files analyzed
- Both inline and external docs checked
- Significance properly evaluated
- Feature doc proposed if warranted
- Conditions generated for guide
- Correct routing based on results

### ❌ SYSTEM FAILURE:

- Skipping significance evaluation
- Not proposing feature docs for significant changes
- Not generating conditions
- Missing obvious patterns

**Master Rule:** Don't just check for gaps - identify reusable knowledge worth capturing.
