---
name: 'step-10-dev-ops'
description: 'Extract development and operational information'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-10-dev-ops.md'
nextStepFile: '{workflow_path}/steps/step-11-integration.md'
nextStepSinglePart: '{workflow_path}/steps/step-12-architecture.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 10: Development and Operations

## STEP GOAL:

Extract development setup instructions, deployment configuration, and contribution guidelines from the project.

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

- 🎯 Focus only on dev setup and deployment documentation
- 🚫 FORBIDDEN to skip existing CONTRIBUTING.md content
- 📊 Extract and organize operational information
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Scan for development setup patterns
- 💾 Extract deployment configuration
- 📖 Capture contribution guidelines if present
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Source tree, existing docs inventory
- Focus: Development and operational documentation
- Limits: Extract existing info, don't invent
- Dependencies: Source tree complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Extract Development Setup

Scan for development setup using key_file_patterns and existing docs:
- Prerequisites (Node version, Python version, etc.)
- Installation steps (npm install, etc.)
- Environment setup (.env files, config)
- Build commands (npm run build, make, etc.)
- Run commands (npm start, go run, etc.)
- Test commands using test_file_patterns

### 2. Extract Deployment Configuration

Look for deployment configuration using ci_cd_patterns:
- Dockerfile, docker-compose.yml
- Kubernetes configs (k8s/, helm/)
- CI/CD pipelines (.github/workflows/, .gitlab-ci.yml)
- Deployment scripts
- Infrastructure as Code (terraform/, pulumi/)

### 3. Extract Contribution Guidelines

If CONTRIBUTING.md or similar found:
- Code style rules
- PR process
- Commit conventions
- Testing requirements

### 4. Write Documentation Files

Write applicable files:
- `{output_folder}/development-guide.md`
- `{output_folder}/deployment-guide.md` (if deployment config found)
- `{output_folder}/contribution-guide.md` (if guidelines found)

### 5. Log Completion

Output to stdout:
```
[step-10] ✓ Dev/Ops documentation extracted
[step-10]   Development guide: {dev_guide_written ? "✓" : "skipped"}
[step-10]   Deployment guide: {deploy_guide_written ? "✓" : "skipped"}
[step-10]   Contribution guide: {contrib_guide_written ? "✓" : "skipped"}
```

### 6. Update State and Route

Update state file with:
- Add "step-10" to completed_steps
- Add written files to outputs_generated

**Determine next step based on project type:**

**If multi-part project:**
- Set current_step = "step-11"
- Output: `[step-10] ✓ Step 10 complete - proceeding to integration architecture`
- Load, read entire file, then execute {nextStepFile}

**If single-part project:**
- Set current_step = "step-12"
- Output: `[step-10] ✓ Step 10 complete - skipping integration, proceeding to architecture`
- Load, read entire file, then execute {nextStepSinglePart}

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Development setup extracted from manifests
- Deployment config captured if present
- Contribution guidelines extracted if present
- Appropriate files written
- Progress logged to stdout
- Auto-proceeded to correct next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write output files

### ⚠️ WARNING (Continue):

- Some config files unreadable
- Missing expected DevOps artifacts

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
