---
name: "step-{{stepNumber}}-{{stepName}}"
description: "{{stepDescription}}"

# Path Definitions
workflow_path: "{project-root}/_bmad/{{targetModule}}/workflows/{{workflowName}}"

# File References
thisStepFile: "{workflow_path}/steps/step-{{stepNumber}}-{{stepName}}.md"
{{#hasNextStep}}
nextStepFile: "{workflow_path}/steps/step-{{nextStepNumber}}-{{nextStepName}}.md"
{{/hasNextStep}}
workflowFile: "{workflow_path}/workflow.md"

{{#hasConditionalRouting}}
# Conditional Routing
{{#conditionalRoutes}}
{{name}}: "{workflow_path}/steps/{{path}}"
{{/conditionalRoutes}}
{{/hasConditionalRouting}}

{{#hasConfigRef}}
# Config References
{{#configRefs}}
{{name}}: "{{path}}"
{{/configRefs}}
{{/hasConfigRef}}

{{#hasConstants}}
# Constants
{{#constants}}
{{name}}: {{value}}
{{/constants}}
{{/hasConstants}}
---

# Step {{stepNumber}}: {{stepTitle}}

## STEP GOAL:

{{stepGoal}}

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 📖 CRITICAL: Read the complete step file before taking any action
- 🎯 This is an action workflow - execute efficiently
{{#universalRules}}
- {{emoji}} {{rule}}
{{/universalRules}}

### Role Reinforcement:

- ✅ You are a {{aiRole}}
{{#roleRules}}
- ✅ {{.}}
{{/roleRules}}

### Step-Specific Rules:

{{#stepRules}}
- {{emoji}} {{rule}}
{{/stepRules}}

## EXECUTION PROTOCOLS:

{{#executionProtocols}}
- {{emoji}} {{protocol}}
{{/executionProtocols}}

## CONTEXT BOUNDARIES:

- Available context: {{availableContext}}
- Focus: {{contextFocus}}
- Limits: {{contextLimits}}
- Dependencies: {{contextDependencies}}

## {{sequenceName}}:

{{#instructions}}
### {{number}}. {{title}}

{{content}}

{{/instructions}}

{{#hasLinearRouting}}
### {{routingNumber}}. Auto-Proceed

Immediately load, read entire file, then execute `{nextStepFile}`.
{{/hasLinearRouting}}

{{#hasConditionalRouting}}
### {{routingNumber}}. Route Based on Results

{{#routingConditions}}
#### IF {{condition}}:
{{action}}
Load, read entire file, then execute `{{{stepFile}}}`

{{/routingConditions}}
{{/hasConditionalRouting}}

{{#isFinalStep}}
### {{routingNumber}}. End Workflow

This is the final step. Workflow ends here.

**Exit Status:**
- Return success (0) if {{successCondition}}
- Return failure (1) if {{failureCondition}}
{{/isFinalStep}}

---

## CRITICAL STEP COMPLETION NOTE

{{completionNote}}

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

{{#successCriteria}}
- {{.}}
{{/successCriteria}}

### ❌ SYSTEM FAILURE:

{{#failureModes}}
- {{.}}
{{/failureModes}}

**Master Rule:** {{masterRule}}
