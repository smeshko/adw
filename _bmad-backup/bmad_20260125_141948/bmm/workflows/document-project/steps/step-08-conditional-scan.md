---
name: 'step-08-conditional-scan'
description: 'Perform conditional analysis based on project type requirements'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-08-conditional-scan.md'
nextStepFile: '{workflow_path}/steps/step-09-source-tree.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 8: Conditional Analysis

## STEP GOAL:

Perform conditional analysis based on the boolean flags in documentation requirements (requires_api_scan, requires_data_models, etc.), generating appropriate documentation files for each applicable area.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Auto-proceed to next step upon completion
- 🤖 YOU ARE AN EXECUTOR, running autonomously

### Role Reinforcement:

- ✅ You are a technical documentarian executing codebase analysis
- ✅ Work autonomously without waiting for user input
- ✅ Log progress to stdout for CI visibility
- ✅ Only stop on critical errors

### Step-Specific Rules:

- 🎯 Focus only on requirements-driven conditional scanning
- 🚫 FORBIDDEN to skip applicable scans based on requirements
- 📊 Apply scan_level strategy to each scan type
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Check each boolean flag from documentation_requirements
- 💾 Generate documentation files for applicable areas
- 📖 Apply scan_level (quick/deep/exhaustive) appropriately
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Technology stack, project type requirements
- Focus: Conditional scanning based on project type
- Limits: Only scan what requirements indicate
- Dependencies: Technology analysis complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Review Scan Level Strategy

**For quick scan:** Use pattern matching only - do NOT read source files. Use glob/grep for locations.

**For deep/exhaustive scan:** Read files in batches (one subfolder at a time), write findings immediately, purge from context.

### 2. Check and Execute Conditional Scans

For each part, check documentation_requirements boolean flags:

**If requires_api_scan == true:**
- Scan for API routes using integration_scan_patterns
- Look for: controllers/, routes/, api/, handlers/, endpoints/
- Build API contracts catalog
- Write to: `{output_folder}/api-contracts-{part_id}.md`

**If requires_data_models == true:**
- Scan for data models using schema_migration_patterns
- Look for: models/, schemas/, entities/, migrations/, prisma/
- Build database schema documentation
- Write to: `{output_folder}/data-models-{part_id}.md`

**If requires_state_management == true:**
- Analyze state management patterns
- Look for: Redux, Context API, MobX, Vuex, stores/
- Document state architecture

**If requires_ui_components == true:**
- Inventory UI component library
- Scan: components/, ui/, widgets/, views/
- Categorize: Layout, Form, Display, Navigation

**If requires_hardware_docs == true:**
- Ask user for hardware documentation paths
- Document hardware interfaces

**If requires_asset_inventory == true:**
- Scan and catalog assets
- Categorize by type

### 3. Additional Pattern Scans

Scan for additional patterns based on doc requirements:
- config_patterns → Configuration management
- auth_security_patterns → Authentication approach
- entry_point_patterns → Application entry points
- shared_code_patterns → Shared libraries
- async_event_patterns → Event-driven architecture
- ci_cd_patterns → CI/CD pipeline
- localization_patterns → i18n support

### 4. Update State with Progress

After each scan type, update state file with:
- Files generated
- Summary counts
- Batch completion tracking

### 5. Log Summary

Output to stdout:
```
[step-08] ✓ Conditional analysis complete
[step-08]   APIs: {api_count} endpoints documented
[step-08]   Data: {table_count} tables/models documented
[step-08]   Components: {component_count} components inventoried
[step-08]   Files generated: {files_count}
```

### 6. Update State

Update state file with:
- Add "step-08" to completed_steps
- outputs_generated list
- Set current_step = "step-09"

Output to stdout:
```
[step-08] ✓ Step 8 complete - proceeding to source tree analysis
```

### 7. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All applicable requirement flags checked
- Appropriate scans executed per project type
- Scan level strategy applied correctly
- Documentation files written for each scan
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write documentation files
- Required scan directories inaccessible

### ⚠️ WARNING (Continue):

- Some scans returned empty results
- Partial file access issues

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
