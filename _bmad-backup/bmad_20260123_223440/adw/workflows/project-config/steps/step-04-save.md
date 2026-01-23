---
name: 'step-04-save'
description: 'Final review and save configuration to file'

# Path Definitions
workflow_path: '{project-root}/_bmad/adw/workflows/project-config'

# File References
thisStepFile: '{workflow_path}/steps/step-04-save.md'
workflowFile: '{workflow_path}/workflow.md'
configFile: '{project-root}/project-config.yaml'
---

# Step 4: Review & Save

## STEP GOAL:

To present the final configuration for review, allow last-minute edits, and save the configuration file.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement:

- ✅ You are a project configuration specialist
- ✅ If you already have been given a name, communication_style and identity, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring configuration validation expertise, user brings their project knowledge
- ✅ Maintain helpful, concise wizard tone throughout

### Step-Specific Rules:

- 🎯 Focus on final review and saving
- 🚫 FORBIDDEN to save without user confirmation
- 💬 Present complete config clearly
- ✅ Ensure YAML is valid before saving

## EXECUTION PROTOCOLS:

- 🎯 Display complete configuration for review
- 💾 Save to `project-config.yaml` in the project root only after confirmation
- 📖 Validate YAML syntax before writing
- 🚫 FORBIDDEN to save without explicit user approval

## CONTEXT BOUNDARIES:

- Configuration object from step 3 is complete
- This is the final step
- Focus on review and save only

## SAVE SEQUENCE:

### 1. Generate Final YAML

Build the complete YAML from configured sections:

```yaml
project:
  name: "[configured name]"
  type: [configured type]

# Only include sections that were configured (not skipped)
test:
  pre_commands: []
  unit:
    command: "[configured]"
    enabled: true
  e2e:
    command: "[configured]"
    enabled: true
  lint:
    command: "[configured]"
    enabled: true
  typecheck:
    command: "[configured]"
    enabled: true
  custom: []

document:
  standards_file: "[configured]"
  check_inline: true
  check_external: true
  doc_locations:
    - "[configured]"
  patterns: []

ship:
  pre_checks: []
  type: [configured type]
  commands:
    version_bump: "[configured]"
    build: "[configured]"
    publish: "[configured]"
    post_publish: []
  environments:
    staging: {}
    production: {}
```

### 2. Present Final Configuration

Display:

"**Final Configuration Review**

Here's your complete project configuration:

```yaml
[display the complete YAML]
```

**Configured Sections:**
- project: [name], [type]
- test: [X commands configured / skipped]
- document: [configured / skipped]
- ship: [type / skipped]

Please review carefully. This will be saved to:
`project-config.yaml` (in your project root)"

### 3. Present Options

Display menu:

"**Ready to save?**

[S] **Save** - Write configuration to file
[E] **Edit** - Make changes to a section
[C] **Cancel** - Discard and exit without saving"

### 4. Handle User Choice

#### IF S (Save):
1. Validate YAML syntax
2. Write configuration to `{configFile}`
3. Confirm: "Configuration saved successfully to `project-config.yaml`"
4. Display completion message

#### IF E (Edit):
- Ask: "Which section would you like to edit? [project/test/document/ship]"
- Allow inline editing of that section
- Regenerate YAML and redisplay for review
- Return to menu

#### IF C (Cancel):
- Confirm: "Are you sure you want to discard this configuration? [Y/N]"
- If Y: "Configuration discarded. No changes were saved."
- If N: Return to menu

### 5. Completion Message

After successful save:

"**Project Configuration Complete!**

Your configuration has been saved to `project-config.yaml`.

**Next Steps:**
You can now use the following workflows with your configured settings:
- `/run-tests` - Run all configured test commands
- `/document-feature` - Verify and update documentation
- `/ship` - Deploy using your configured settings

To modify this configuration later, run `/project-config` again.

Happy coding!"

### 6. End Workflow

This is the final step. Workflow ends after save or cancel.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Complete configuration displayed for review
- User explicitly approved before saving
- Valid YAML written to correct location
- Completion message with next steps displayed

### ❌ SYSTEM FAILURE:

- Saving without user confirmation
- Writing invalid YAML
- Saving to wrong location
- Not handling edit requests
- Not offering cancel option

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.

## CRITICAL STEP COMPLETION NOTE

This is the FINAL step of the workflow. After save or cancel, the workflow ends. There is no next step to load.
