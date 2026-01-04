# Epic 2: Command Resolution & Templates

**Goal:** Enable command and prompt resolution using the three-tier hierarchy (project → user → bundled) with template variable substitution. This epic provides the foundation for loading and rendering phase prompts.

## Story 2.1: Implement Three-Tier Command Resolution

As a developer,
I want commands resolved from project, then user, then bundled defaults,
So that users can override any command at the appropriate level.

**Acceptance Criteria:**

**Given** a command name "plan"
**When** the resolver searches for it
**Then** it checks in order:
  1. `.adw/commands/plan/` (project level)
  2. `~/.adw/commands/plan/` (user level)
  3. Bundled defaults in package

**Given** a command exists at project level
**When** the same command exists at user and bundled level
**Then** the project-level command is used

**Given** a command exists only at bundled level
**When** project and user levels are empty
**Then** the bundled command is used

**Given** a command name that doesn't exist anywhere
**When** resolution is attempted
**Then** ConfigError is raised with code "COMMAND_NOT_FOUND" and helpful suggestion

**Given** a resolved command directory
**When** I inspect its contents
**Then** it contains: prompt.md, optionally schema.json, optionally pre-hook.sh, post-hook.sh

---

## Story 2.2: Create Template Engine with Variable Substitution

As a developer,
I want templates rendered with {{variable}} substitution,
So that prompts can include dynamic content from the run context.

**Acceptance Criteria:**

**Given** a template string with `{{feature_description}}`
**When** rendered with context containing feature_description="Add login"
**Then** the output contains "Add login"

**Given** a template with `{{file:path/to/file.txt}}`
**When** the file exists and contains "file content"
**Then** the output contains "file content"

**Given** a template with `{{file:nonexistent.txt}}`
**When** rendering is attempted
**Then** ConfigError is raised with code "TEMPLATE_FILE_NOT_FOUND"

**Given** a template with nested variables `{{phase_{{index}}}}`
**When** rendering is attempted
**Then** only single-level substitution occurs (no recursive expansion)

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with strict mode
**Then** ConfigError is raised with code "UNKNOWN_VARIABLE"

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with lenient mode
**Then** the variable is left as-is in output

---

## Story 2.3: Load and Render Phase Prompts

As a developer,
I want to load a phase prompt from the resolved command directory and render it,
So that each phase has its complete, rendered prompt ready for LLM execution.

**Acceptance Criteria:**

**Given** a phase "plan" with resolved command directory
**When** I call `load_prompt("plan", context)`
**Then** it reads `prompt.md` from the command directory
**And** renders all template variables using the context

**Given** a prompt that references artifacts from previous phases
**When** the template contains `{{artifacts.build.diff}}`
**Then** the artifact content is included in the rendered prompt

**Given** a command directory with pre-hook output
**When** pre-hook stdout is available as `{{pre_hook_output}}`
**Then** it's included in the template context for rendering

**Given** the rendered prompt
**When** I inspect it
**Then** no unresolved `{{...}}` patterns remain (in strict mode)

---

## Story 2.4: Validate LLM Output Against Schema

As a developer,
I want LLM output validated against an optional JSON schema,
So that I can ensure structured output meets expectations.

**Acceptance Criteria:**

**Given** a command directory with `schema.json`
**When** LLM output matches the schema
**Then** validation passes and returns parsed data

**Given** a command directory with `schema.json`
**When** LLM output doesn't match the schema
**Then** ValidationError is raised with specific field errors

**Given** a command directory without `schema.json`
**When** LLM output is received
**Then** no validation is performed and raw content is returned

**Given** LLM output as markdown with JSON code block
**When** schema validation is enabled
**Then** JSON is extracted from the code block before validation

**Given** multiple JSON code blocks in output
**When** extraction is attempted
**Then** the first valid JSON block matching the schema is used

---

## Epic 2: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately (PARALLEL x2)                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [2.1] Three-Tier Command      ║    [2.2] Template Engine         ║
║        Resolution              ║          Variable Substitution   ║
║                                ║                                  ║
║  - Depends On: None            ║    - Depends On: None            ║
║  - Blocks: 2.3, 2.4            ║    - Blocks: 2.3                 ║
║                                ║                                  ║
╚═══════════════════════════════════════════════════════════════════╝
                │                              │
                │                              │
                ▼                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 2.1 + 2.2 (PARALLEL x2)                            ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [2.3] Load and Render         ║    [2.4] Validate LLM Output     ║
║        Phase Prompts           ║          Against Schema          ║
║                                ║                                  ║
║  - Depends On: 2.1, 2.2        ║    - Depends On: 2.1             ║
║  - Blocks: None                ║    - Blocks: None                ║
║                                ║                                  ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Execution Summary

| Wave | Stories | Parallelization |
|------|---------|-----------------|
| Wave 1 | 2.1, 2.2 | Can run in parallel (no dependencies) |
| Wave 2 | 2.3, 2.4 | Can run in parallel (after Wave 1) |

**Critical Path:** 2.1 → 2.3 or 2.1 → 2.4 (either path completes the epic)

**Note:** Story 2.4 only requires 2.1, so it could theoretically start before 2.2 completes. However, 2.3 requires both 2.1 AND 2.2.

---
