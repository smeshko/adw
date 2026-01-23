---
name: 'step-02-scan'
description: 'Deep scan project structure to detect type and existing tooling configurations'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/setup/project-config'

# File References
thisStepFile: '{workflow_path}/steps/step-02-scan.md'
nextStepFile: '{workflow_path}/steps/step-03-configure.md'
workflowFile: '{workflow_path}/workflow.md'
detectionPatterns: '{workflow_path}/data/detection-patterns.yaml'

# Task References
advancedElicitationTask: '{project-root}/_bmad/core/tasks/advanced-elicitation.xml'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 2: Project Scan & Detection

## STEP GOAL:

To perform a deep scan of the project structure using sub-agents to detect the project type and existing tooling configurations, then present findings for user confirmation.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a project configuration specialist with detection expertise
- ✅ If you already have been given a name, communication_style and identity, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring project structure detection expertise, user brings their project knowledge
- ✅ Maintain helpful, concise wizard tone throughout

### Step-Specific Rules:

- 🎯 Focus ONLY on scanning and detecting project structure
- 🚫 FORBIDDEN to configure anything in this step
- 💬 Present findings clearly for user review
- 🔍 Use sub-agents for parallel scanning when possible

## EXECUTION PROTOCOLS:

- 🎯 Scan project root for type indicators and tooling configs
- 💾 Store detection results for use in configuration step
- 📖 Present all findings before proceeding
- 🚫 FORBIDDEN to proceed without user confirmation of detected type

## CONTEXT BOUNDARIES:

- Fresh scan of project structure
- No assumptions about project type
- Focus on detection, not configuration
- If unrecognizable structure, trigger Advanced Elicitation

## SCANNING SEQUENCE:

### 1. Initialize Scan

Display: "Scanning your project structure..."

### 2. Parallel Detection Scan

Use sub-agents to scan in parallel for:

**Project Type Files:**
- `package.json` → Node.js/Web project
- `Podfile` or `*.xcodeproj` → iOS project
- `build.gradle` or `settings.gradle` → Android/Java project
- `pom.xml` → Maven/Java project
- `requirements.txt` or `pyproject.toml` or `setup.py` → Python project
- `go.mod` → Go project
- `Cargo.toml` → Rust project
- `composer.json` → PHP project
- `Gemfile` → Ruby project

**Tooling Config Files:**
- `.eslintrc*` or `eslint.config.*` → ESLint
- `jest.config.*` or `jest.setup.*` → Jest
- `vitest.config.*` → Vitest
- `playwright.config.*` → Playwright
- `cypress.config.*` or `cypress.json` → Cypress
- `tsconfig.json` → TypeScript
- `.prettierrc*` or `prettier.config.*` → Prettier
- `webpack.config.*` → Webpack
- `vite.config.*` → Vite
- `.github/workflows/*.yml` → GitHub Actions
- `Makefile` → Make
- `Dockerfile` or `docker-compose.*` → Docker

**Package Scripts (if package.json exists):**
- Extract all scripts from `package.json`
- Identify test, lint, build, and other relevant scripts

### 3. Analyze Detection Results

Based on scan results, determine:

**Project Type:**
- Primary type (web, backend, mobile, monorepo, other)
- Framework/stack if identifiable

**Available Commands:**
- Test commands found
- Lint commands found
- Build commands found
- Type check commands found

**Configuration Files:**
- List all tooling configs detected

### 4. Handle Unrecognizable Structure

If no project type files are detected:

Display: "I couldn't automatically detect your project type."

**Trigger Advanced Elicitation:**
- Ask user to describe their project structure
- Ask what type of project this is
- Ask what commands they use for testing, linting, building

### 5. Present Findings

Display scan results:

"**Project Scan Complete**

**Detected Project Type:** [type]
**Primary Stack:** [framework/language]

**Project Type Indicators Found:**
- [list of project type files found]

**Tooling Configurations Detected:**
| Tool | Config File | Detected Command |
|------|-------------|------------------|
| [tool] | [file] | [command if found] |
| ... | ... | ... |

**Package Scripts Found:** (if applicable)
- test: [command]
- lint: [command]
- build: [command]
- [other relevant scripts]

**Is this detection correct?**"

### 6. Confirm or Adjust

Allow user to:
- Confirm the detected type is correct
- Correct the project type if detection was wrong
- Add information that wasn't detected

### 7. Store Detection Context

After confirmation, store in memory for step 3:
- Confirmed project type
- All detected tooling
- Suggested commands for each category
- Any user corrections

### 8. Present MENU OPTIONS

Display: **Select an Option:** [A] Advanced Elicitation [P] Party Mode [C] Continue to Configuration

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'C'
- After other menu items execution, return to this menu
- User can chat or ask questions - always respond and then redisplay menu

#### Menu Handling Logic:

- IF A: Execute `{advancedElicitationTask}` to explore detection further
- IF P: Execute `{partyModeWorkflow}` for multi-agent discussion
- IF C: Store confirmed detection results, then load, read entire file, then execute `{nextStepFile}`
- IF Any other comments or queries: help user respond then redisplay menu

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Comprehensive scan of project structure completed
- Project type correctly identified (or user provided info)
- All relevant tooling configs detected
- User confirmed detection results
- Detection context stored for configuration step

### ❌ SYSTEM FAILURE:

- Incomplete scanning of project structure
- Not using sub-agents for parallel scanning
- Proceeding without user confirmation
- Guessing when structure is unrecognizable
- Not triggering Advanced Elicitation when needed

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN C is selected and detection results are confirmed, will you then store the context and load, read entire file, then execute `{nextStepFile}` to begin configuration.
