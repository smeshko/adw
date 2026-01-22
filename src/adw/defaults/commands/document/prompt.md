# Document Phase

Analyze code changes for documentation needs, create feature documentation for significant changes, update the conditional docs guide, and generate a PR description.

## Context

Run Context: {{context}}
Feature: {{feature_description}}

## Build Artifacts

**Implementation Summary:**
{{artifacts.build.build_output}}

**Git Diff Stats:**
{{artifacts.build.diff_stats}}

**Git Diff:**
{{artifacts.build.diff}}

## Validation Artifacts

**Evidence:**
{{artifacts.validate.*}}

## Additional Inputs

{{inputs.*}}

## Doc Mappings Configuration

{{doc_mappings}}

## Instructions

### Workflow Engine
{{shared:workflow.xml}}

### Workflow Config
{{include:document-feature/workflow.yaml}}

### Instructions
{{include:document-feature/instructions.xml}}

IT IS CRITICAL THAT YOU FOLLOW THESE STEPS - while staying in character as the documentation specialist persona:

<steps CRITICAL="TRUE">
1. The workflow execution engine (workflow.xml) is included above
2. The workflow config (workflow.yaml) is included above
3. Follow workflow.xml instructions EXACTLY as written to process and follow the specific workflow config and its instructions
4. Execute ALL 5 steps in order:
   - Step 1: Detect changes and load context
   - Step 2: Analyze documentation gaps and evaluate significance
   - Step 3: Update documentation (if needed)
   - Step 4: Generate documentation report
   - Step 5: Generate PR description as final output
5. The final output MUST include the PR description
</steps>

## Output Requirements

Your response must include:

1. **Documentation Report** - Summary of analysis and updates made
2. **PR Description** - The final PR description in markdown format

If feature documentation was created, output it between markers:
```
# FEATURE DOC OUTPUT
[feature doc content]
# END FEATURE DOC OUTPUT
```

The PR description should be the final section of your response.
