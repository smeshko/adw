---
name: 'step-03-step-validation'
description: 'Validate each step file against step-template.md standards'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmb/workflows/workflow-compliance-check'

# File References
thisStepFile: '{workflow_path}/steps/step-03-step-validation.md'
nextStepFile: '{workflow_path}/steps/step-04-file-validation.md'
workflowFile: '{workflow_path}/workflow.md'
complianceReportFile: '{output_folder}/workflow-compliance-report-{workflow_name}.md'
targetWorkflowStepsPath: '{target_workflow_steps_path}'

# Template References
complianceReportTemplate: '{workflow_path}/templates/compliance-report.md'

# Documentation References - Interactive (Standard) Templates
stepTemplate: '{project-root}/_bmad/bmb/docs/workflows/templates/step-template.md'
workflowTemplate: '{project-root}/_bmad/bmb/docs/workflows/templates/workflow-template.md'

# Documentation References - Action Workflow Templates
actionStepTemplate: '{project-root}/_bmad/bmb/docs/workflows/templates/action-step-template.md'
actionWorkflowTemplate: '{project-root}/_bmad/bmb/docs/workflows/templates/action-workflow-template.md'
---

# Step 3: Step-by-Step Validation

## STEP GOAL:

Perform systematic adversarial validation of each step file against step-template.md standards, documenting all violations with specific template references and severity rankings.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read this complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a compliance validator and quality assurance specialist
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring adversarial step-by-step validation expertise
- ✅ User brings their workflow steps and needs thorough validation

### Step-Specific Rules:

- 🎯 Focus only on step file validation against step-template.md
- 🚫 FORBIDDEN to skip any step files or validation checks
- 💬 Approach: Systematic file-by-file adversarial analysis
- 📋 Document every violation against each step file with template reference and specific proposed fixes

## EXECUTION PROTOCOLS:

- 🎯 Load and validate each step file individually against step-template.md
- 💾 Document violations by file with severity rankings
- 📖 Check for appropriate template usage based on workflow type
- 🚫 FORBIDDEN to overlook any step file or template requirement

## CONTEXT BOUNDARIES:

- Available context: Target workflow step files and step-template.md
- Focus: Systematic validation of all step files against template standards
- Limits: Only step file validation, holistic analysis comes next
- Dependencies: Completed workflow.md validation from previous phase

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Initialize Step Validation Phase

"Beginning **Phase 2: Step-by-Step Validation**
Target: `{target_workflow_name}` - [number] step files found

**Workflow Type:** `{workflowType}` (detected in Phase 1)"

**Select appropriate step template based on workflow type:**

**IF `workflowType` = "action":**

Set `activeStepTemplate` = `{actionStepTemplate}`
"**COMPLIANCE STANDARD:** All validation performed against `{actionStepTemplate}` - the authoritative standard for action workflow steps."

**IF `workflowType` = "interactive":**

Set `activeStepTemplate` = `{stepTemplate}`
"**COMPLIANCE STANDARD:** All validation performed against `{stepTemplate}` - the authoritative standard for interactive workflow steps."

"Loading appropriate step template and validating each step systematically..."
[Load activeStepTemplate, enumerate all step files]. Utilize sub processes if available but ensure all rules are passed in and all findings are returned from the sub process to collect and record the results.

### 2. Systematic Step File Analysis

For each step file in order:

"**Validating step:** `{step_filename}`"

**A. Frontmatter Structure Validation:**
Check each required field:

```yaml
---
name: 'step-[number]-[name]' # Single quotes, proper format
description: '[description]' # Single quotes
workflowFile: '{workflow_path}/workflow.md' # REQUIRED - often missing
outputFile: [if appropriate for workflow type]
# All other path references and variables
# Template References section (even if empty)
# Task References section
---
```

**Violations to document:**

- Missing `workflowFile` reference (Critical)
- Incorrect YAML format (missing quotes, etc.) (Major)
- Inappropriate `outputFile` for workflow type (Major)
- Missing `Template References` section (Major)

**B. MANDATORY EXECUTION RULES Validation:**
Check for complete sections based on workflow type:

**IF `workflowType` = "interactive":**

```markdown
## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

[Complete role reinforcement section with partnership language]

### Step-Specific Rules:

[Step-specific rules with proper emoji usage]
```

**IF `workflowType` = "action":**

```markdown
## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
- 🔄 Auto-proceed to next step when complete

### Role Reinforcement:

- ✅ You are a [specific executor role]
- ✅ Execute actions autonomously
- ✅ Track results for reporting
- ✅ Be efficient and clear in execution

### Step-Specific Rules:

[Step-specific rules with proper emoji usage]
```

**Violations to document:**

- Missing Universal Rules (Critical)
- Modified/skipped Universal Rules for detected workflow type (Critical)
- Missing Role Reinforcement (Major)
- Improper emoji usage in rules (Minor)

**C. Task References Validation:**

**IF `workflowType` = "interactive":**

Check for proper references:

```yaml
# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
```

**Violations to document:**

- Missing Task References section (Major)
- Incorrect paths in task references (Major)
- Missing standard task references (Minor)

**IF `workflowType` = "action":**

Task References are optional for action workflows since they execute autonomously without Advanced Elicitation or Party Mode options.

Check for:
- Config file references if workflow is config-driven
- Any conditional step file references (successStepFile, failureStepFile)

**Violations to document:**

- Incorrect paths in any references (Major)
- advancedElicitationTask/partyModeWorkflow present but unused (Minor - cleanup)

**D. Menu Pattern / Progression Validation:**

**IF `workflowType` = "interactive":**

Check menu structure:

```markdown
Display: "**Select an Option:** [A] Advanced Elicitation [P] Party Mode [C] Continue"

#### Menu Handling Logic:

- IF A: Execute {advancedElicitationTask}
- IF P: Execute {partyModeWorkflow}
- IF C: Save content to {outputFile}, update frontmatter, then only then load, read entire file, then execute {nextStepFile}
```

**Violations to document:**

- Non-standard menu format (Major)
- Missing Menu Handling Logic section (Major)
- Incorrect "load, read entire file, then execute" pattern (Major)
- Improper continuation logic (Critical)

**IF `workflowType` = "action":**

Check auto-proceed pattern:

```markdown
### N. Proceed to Next Step

Immediately load, read entire file, then execute `{nextStepFile}`.

# OR for conditional routing:

**IF [success condition]:**
Load, read entire file, then execute `{successStepFile}`

**IF [failure condition]:**
Load, read entire file, then execute `{failureStepFile}`
```

**Violations to document:**

- Missing auto-proceed instruction (Major)
- Incorrect "load, read entire file, then execute" pattern (Major)
- Menu patterns present in action workflow (Major - should be auto-proceed)
- Missing conditional routing when branching logic exists (Major)

### 3. Workflow Type Appropriateness Check

"**Template Usage Analysis:**"

- **Document Creation Workflows:** Should have outputFile references, templates
- **Editing Workflows:** Should NOT create unnecessary outputs, direct action focus
- **Validation/Analysis Workflows:** Should emphasize systematic checking

For each step:

- **Type Match:** Does step content match workflow type expectations?
- **Template Appropriate:** Are templates/outputs appropriate for this workflow type?
- **Alternative Suggestion:** What would be more appropriate?

### 4. Path Variable Consistency Check

"**Path Variable Validation:**"

- Check format: `{project-root}/_bmad/bmb/...` vs `{project-root}/bmb/...`
- Ensure consistent variable usage across all step files
- Validate relative vs absolute path usage

Document inconsistencies and standard format requirements.

### 5. Document Step Validation Results

For each step file with violations:

```markdown
### Step Validation: step-[number]-[name].md

**Critical Violations:**

- [Violation] - Template Reference: [section] - Fix: [specific action]

**Major Violations:**

- [Violation] - Template Reference: [section] - Fix: [specific action]

**Minor Violations:**

- [Violation] - Template Reference: [section] - Fix: [specific action]

**Workflow Type Assessment:**

- Appropriate: [Yes/No] - Reason: [analysis]
- Recommended Changes: [specific suggestions]
```

### 6. Phase Summary and Continuation

"**Phase 2 Complete:** Step-by-step validation finished

- **Total Steps Analyzed:** [number]
- **Critical Violations:** [number] across [number] steps
- **Major Violations:** [number] across [number] steps
- **Minor Violations:** [number] across [number] steps

**Most Common Violations:**

1. [Most frequent violation type]
2. [Second most frequent]
3. [Third most frequent]

**Ready for Phase 4:** File Validation workflow analysis

- Flow optimization assessment
- Goal alignment verification
- Meta-workflow failure analysis

**Select an Option:** [C] Continue to File Validation [X] Exit"

## Menu Handling Logic:

- IF C: Save step validation findings to report, update frontmatter, then load, read entire file, then execute {nextStepFile}
- IF X: Save current findings and end with guidance for resuming
- IF Any other comments or queries: respond and redisplay menu

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [C continue option] is selected and [all step files validated with violations documented], will you then load and read fully `{nextStepFile}` to execute and begin holistic analysis phase.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All step files systematically validated against step-template.md
- Every violation documented with specific template reference and severity
- Workflow type appropriateness assessed for each step
- Path variable consistency checked across all files
- Common violation patterns identified and prioritized
- Compliance report updated with complete Phase 2 findings

### ❌ SYSTEM FAILURE:

- Skipping step files or validation sections
- Not documenting violations with specific template references
- Failing to assess workflow type appropriateness
- Missing path variable consistency analysis
- Providing incomplete or vague fix recommendations

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
