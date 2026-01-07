# Build Phase

Implement the feature according to the plan.

## Context

{{context}}

## Plan

{{plan}}

## Instructions

### Workflow Engine
{{shared:workflow.xml}}

### Workflow Config
{{include:dev-story/workflow.yaml}}

### Instructions
{{include:dev-story/instructions.xml}}

### Instructions

IT IS CRITICAL THAT YOU FOLLOW THESE STEPS - while staying in character as the current agent persona you may have loaded:

<steps CRITICAL="TRUE">
1. Always LOAD the FULL @{{shared:workflow.xml}}
2. READ its entire contents - this is the CORE OS for EXECUTING the specific workflow-config @{{include:dev-story/workflow.yaml}}
3. Pass the yaml path {{include:dev-story/workflow.yaml}} as 'workflow-config' parameter to the workflow.xml instructions
4. Follow workflow.xml instructions EXACTLY as written to process and follow the specific workflow config and its instructions
5. Save outputs after EACH section when generating any documents from templates
</steps>
