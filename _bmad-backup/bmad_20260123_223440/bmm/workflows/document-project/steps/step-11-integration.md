---
name: 'step-11-integration'
description: 'Detect multi-part integration architecture'

# Path Definitions
workflow_path: '{project-root}/_bmad/bmm/workflows/document-project'

# File References
thisStepFile: '{workflow_path}/steps/step-11-integration.md'
nextStepFile: '{workflow_path}/steps/step-12-architecture.md'
workflowFile: '{workflow_path}/workflow.md'
stateFile: '{output_folder}/project-scan-report.json'
---

# Step 11: Integration Architecture

## STEP GOAL:

Analyze how multiple project parts communicate with each other, documenting API contracts, data flow, and integration points.

**Note:** This step only executes for multi-part projects. Single-part projects skip to step-12.

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

- 🎯 Focus only on inter-part communication
- 🚫 FORBIDDEN to skip for multi-part projects
- 📊 Map all integration points between parts
- ⚡ Auto-proceed when complete

## EXECUTION PROTOCOLS:

- 🎯 Analyze communication patterns between parts
- 💾 Document integration points
- 📖 Map data flow between parts
- 📊 Log progress to stdout
- ⚡ Auto-proceed to next step

## CONTEXT BOUNDARIES:

- Available context: Project parts, conditional scan results
- Focus: Inter-part integration only
- Limits: Integration documentation only
- Dependencies: Dev/Ops extraction complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Check Project Type

**If single-part project:**
- Output: `[step-11] Single-part project - skipping integration analysis`
- Immediately load, read entire file, then execute {nextStepFile}

**If multi-part project:**
- Output: `[step-11] Analyzing integration architecture for multi-part project...`
- Continue with integration analysis

### 2. Analyze Communication Patterns

Scan integration_scan_patterns across parts to identify:
- REST calls between parts
- GraphQL queries
- gRPC communication
- Message queues
- Shared databases

### 3. Document Integration Points

Create integration_points array with:
- from: source part
- to: target part
- type: REST API, GraphQL, gRPC, Event Bus, etc.
- details: Endpoints, protocols, data formats

### 4. Map Data Flow

Document:
- API contracts between parts
- Data transformation points
- Authentication flow across parts
- Shared state or database access

### 5. Write Integration Documentation

Write to: `{output_folder}/integration-architecture.md`

Validate document completeness.

### 6. Log Completion

Output to stdout:
```
[step-11] ✓ Integration architecture documented
[step-11]   Integration points: {integration_count}
[step-11]   File: integration-architecture.md
```

### 7. Update State

Update state file with:
- Add "step-11" to completed_steps
- Add integration-architecture.md to outputs_generated
- Set current_step = "step-12"

Output to stdout:
```
[step-11] ✓ Step 11 complete - proceeding to architecture documentation
```

### 8. Auto-Proceed to Next Step

Load, read entire file, then execute {nextStepFile}.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All integration points identified
- Communication patterns documented
- Data flow mapped
- File written and validated
- Progress logged to stdout
- Auto-proceeded to next step

### ❌ CRITICAL FAILURE (Exit 1):

- Cannot write output file

### ⚠️ WARNING (Continue):

- Some integration patterns unclear
- Limited evidence for communication methods

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
