---
name: 'step-03-configure'
description: 'Walk through configuration sections with validation of commands'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/project-config'

# File References
thisStepFile: '{workflow_path}/steps/step-03-configure.md'
nextStepFile: '{workflow_path}/steps/step-04-save.md'
workflowFile: '{workflow_path}/workflow.md'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 3: Configuration Wizard

## STEP GOAL:

To walk the user through configuring each section of the project config, proposing defaults based on detection, validating commands work, and allowing sections to be skipped.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a project configuration specialist
- ✅ If you already have been given a name, communication_style and identity, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring configuration and validation expertise, user brings their project knowledge
- ✅ Maintain helpful, concise wizard tone throughout

### Step-Specific Rules:

- 🎯 Focus on configuring sections based on user choices
- 🚫 FORBIDDEN to force any section (except project basics)
- 💬 Propose defaults, let user confirm/adjust
- ✅ Validate commands as they are configured
- 🔧 Use Advanced Elicitation when validation fails

## EXECUTION PROTOCOLS:

- 🎯 Walk through sections sequentially
- 💾 Build config object as user confirms each section
- 📖 Validate commands using sub-processes
- 🚫 FORBIDDEN to skip validation step
- 🔧 Suggest fixes when validation fails

## CONTEXT BOUNDARIES:

- Detection results from step 2 inform defaults
- Context may indicate: add missing sections only, modify specific section, or full config
- Build config object incrementally
- Each section is independent

## CONFIGURATION SEQUENCE:

### 1. Initialize Configuration

Check context from previous step:
- **Full config**: Configure all sections
- **Add missing**: Only configure sections not already in config
- **Modify section**: Only configure the specified section

Display: "Let's configure your project. I'll walk you through each section."

### 2. Configure Project Section (Required)

"**Project Basics** (required)"

Based on detection, propose:
```yaml
project:
  name: "[detected or folder name]"
  type: [web|backend|mobile|monorepo|other]
```

Ask user to confirm or adjust:
- Project name
- Project type

### 3. Configure Test Section (Skippable)

"**Test Configuration**

Would you like to configure test commands? [Y/N/S to skip]"

If Y or yes:

Based on detection, propose defaults for each:

**Unit Tests:**
```yaml
unit:
  command: "[detected command or suggest based on type]"
  enabled: true
```
- Validate: Run the command with a quick test (timeout after 10s)
- If fails: Trigger Advanced Elicitation to help troubleshoot
- User confirms or adjusts

**E2E Tests:**
```yaml
e2e:
  command: "[detected command]"
  enabled: true
```
- Same validation flow

**Linting:**
```yaml
lint:
  command: "[detected command]"
  enabled: true
```
- Same validation flow

**Type Checking:**
```yaml
typecheck:
  command: "[detected command]"
  enabled: true
```
- Same validation flow

**Custom Commands:**
Ask: "Any additional test commands to add?"

If S or skip: Mark test section as skipped, continue

### 4. Configure Document Section (Skippable)

"**Documentation Configuration**

Would you like to configure documentation settings? [Y/N/S to skip]"

If Y or yes:

```yaml
document:
  standards_file: "[suggest docs/DOCUMENTATION_STANDARDS.md]"
  check_inline: true
  check_external: true
  doc_locations:
    - "README.md"
    - "docs/"
  patterns: []
```

Ask user to:
- Confirm or specify documentation standards file location
- Confirm which locations to check
- Add any specific patterns to follow

If S or skip: Mark document section as skipped, continue

### 5. Configure Ship Section (Skippable)

"**Deployment Configuration**

Would you like to configure deployment/shipping settings? [Y/N/S to skip]"

If Y or yes:

First, determine deployment type:
"What type of deployment do you use?
- npm (publish to npm registry)
- docker (container deployment)
- github-release (GitHub releases)
- custom (custom deployment scripts)"

Based on type, propose:

**For npm:**
```yaml
ship:
  type: npm
  commands:
    version_bump: "npm version patch"
    build: "npm run build"
    publish: "npm publish"
```

**For docker:**
```yaml
ship:
  type: docker
  commands:
    build: "docker build -t [name] ."
    push: "docker push [registry/name]"
```

**For github-release:**
```yaml
ship:
  type: github-release
  commands:
    build: "[build command]"
    release: "gh release create"
```

**For custom:**
Ask user to specify their deployment commands

Validate key commands exist and are executable.

Ask about environments:
"Do you deploy to multiple environments (staging, production)? [Y/N]"

If S or skip: Mark ship section as skipped, continue

### 6. Validation Summary

After all sections configured, display:

"**Configuration Summary**

| Section | Status | Commands/Settings |
|---------|--------|-------------------|
| project | Configured | name: X, type: Y |
| test | [Configured/Skipped] | [count] commands |
| document | [Configured/Skipped] | [settings summary] |
| ship | [Configured/Skipped] | type: [type] |

**Validation Results:**
- [list of commands validated and their status]"

### 7. Handle Validation Failures

If any commands failed validation:

"Some commands didn't validate successfully:

| Command | Error |
|---------|-------|
| [command] | [error summary] |

Would you like to:
[F] Fix these commands now
[I] Ignore and continue (commands may not work)
[A] Advanced Elicitation to troubleshoot"

### 8. Present MENU OPTIONS

Display: **Select an Option:** [A] Advanced Elicitation [P] Party Mode [C] Continue to Save

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'C'
- After other menu items execution, return to this menu
- User can chat or ask questions - always respond and then redisplay menu

#### Menu Handling Logic:

- IF A: Execute `{advancedElicitationTask}` to explore configuration issues
- IF P: Execute `{partyModeWorkflow}` for multi-agent discussion
- IF C: Finalize config object, then load, read entire file, then execute `{nextStepFile}`
- IF Any other comments or queries: help user respond then redisplay menu

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Project section configured (required)
- User offered choice to configure or skip each optional section
- Defaults proposed based on detection
- Commands validated using sub-processes
- Validation failures handled with Advanced Elicitation option
- Complete config object ready for saving

### ❌ SYSTEM FAILURE:

- Forcing user to configure optional sections
- Not validating commands
- Guessing commands without detection basis
- Not offering Advanced Elicitation on failures
- Proceeding without user confirmation of each section

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN C is selected and configuration is complete, will you then store the config object and load, read entire file, then execute `{nextStepFile}` to save the configuration.
