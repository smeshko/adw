---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
---

# Workflow Creation Plan: structure-documentation

## Initial Project Context

- **Module:** bmm
- **Target Location:** `_bmad/bmm/workflows/structure-documentation`
- **Created:** 2026-01-23

## Workflow Overview

**Purpose:** Transform existing project documentation into a standardized structure based on the project-docs-pattern.

## Key Reference

- **Pattern Source:** `project-docs-pattern/project-docs-pattern.md`
- **Templates Location:** `project-docs-pattern/templates/`
- **Examples Location:** `project-docs-pattern/examples/`

---

## Detailed Requirements

### Workflow Type Classification

- **Primary Type:** Branching workflow with two distinct execution paths
- **Sub-types:**
  - Autonomous Mode = Action Workflow (performs reorganization)
  - Guided Mode = Interactive Workflow (collaborative document building)

### Workflow Flow Structure

**Entry Point:**
1. Superficial scan of project to assess current documentation state
2. Recommend mode (Autonomous vs Guided) based on findings
3. User confirms or overrides recommendation
4. Branch to selected mode

**Autonomous Mode Flow:**
- Scan → Categorize → Reorganize → Fill Major Gaps → Summary Report
- Major gaps = missing architecture overview, missing getting-started
- Silent execution with summary at end

**Guided Mode Flow:**
- Separate step file per section
- User can skip any section (creates empty folder with README placeholder)
- Each section follows pattern: "Do you have existing docs?" → Yes: reorganize / No: guided creation

### Guided Mode Sections (Step Files)

| Section | Key Question | Output |
|---------|--------------|--------|
| `/architecture` | Existing arch docs? Or create overview? | architecture/README.md, overview.md |
| `/development` | Existing setup/deploy docs? | getting-started.md, deployment.md |
| `/templates` | Code files to templatize? | service-template.md, etc. |
| `/reference` | Data models, APIs to document? | data-models.md, api-contracts.md |
| `/testing` | Testing approach docs? | testing-strategy.md |
| `/product` | Existing PRD? | prd.md |
| `/design` | (If UI) Design system? | design-system.md |

### Template Generation (Guided /templates Section)

- User provides link to code file (e.g., `src/http-service.py`)
- Agent loads corresponding template from `project-docs-pattern/templates/`
- Agent analyzes the code file
- Agent populates template with content based on real implementation
- Creates template document in `docs/templates/`

### Instruction Style

- **Intent-based** for Guided mode
- Flexible conversation, adapts to user context
- Guardrails to keep concise (couple questions per section, not comprehensive)

### Input Requirements

- **Prerequisites:** None
- **Access needed:** Project root filesystem access
- No config files required
- No existing `docs/` folder required (will create if missing)

### Output Specifications

- **Location:** Directly in project's `docs/` folder and subfolders
- **Format:** Markdown files following project-docs-pattern structure
- **Templates Source:** Copy from `project-docs-pattern/templates/` (source of truth)
- **Generated docs:** Must use templates when one exists for the document type

### Success Criteria

- All standard folders exist under `docs/`
- Each folder contains exactly one README.md
- For Guided mode: completed sections have their primary documents
- For Autonomous mode: existing docs reorganized + major gaps filled

---

## Tools Configuration

### Core BMAD Tools

- **Party-Mode**: Excluded - not needed for structured documentation workflow
- **Advanced Elicitation**: Included - Integration points: Architecture section (deeper questioning for system design) and Templates section (understanding code patterns for template generation)
- **Brainstorming**: Excluded - workflow is structured, not creative exploration

### LLM Features

- **Web-Browsing**: Excluded - workflow operates on local project files only
- **File I/O**: Included - core functionality for reading existing docs, writing new structure, copying templates
- **Sub-Agents**: Included - Autonomous mode uses sub-agents for parallel scanning of project directories (architecture, development, testing, etc. scanned concurrently)
- **Sub-Processes**: Excluded - sub-agents sufficient for parallelization needs

### Memory Systems

- **Sidecar File**: Excluded - keeping workflow simple, no session resume capability

### External Integrations

- None required - workflow operates entirely on local filesystem

### Installation Requirements

- No external tools requiring installation
- All functionality available through core LLM capabilities

---

## Output Format Design

**Format Type**: Structured

**Output Requirements**:
- Document type: Markdown documentation files
- File format: `.md` (Markdown)
- Frequency: Batch (creates multiple files per execution)

**Structure Specifications**:

All outputs follow templates from `project-docs-pattern/templates/`:

| Output Document | Template Source | Purpose |
|-----------------|-----------------|---------|
| `docs/README.md` | `readme-root.template.md` | Central documentation hub |
| `docs/*/README.md` | `readme-section.template.md` | Section indexes |
| `docs/CONDITIONAL_DOCS.md` | `conditional-docs.template.md` | Task-based navigation |
| `docs/DOCUMENTATION_STANDARDS.md` | `documentation-standards.template.md` | Writing rules |
| `docs/development/getting-started.md` | `getting-started.template.md` | Developer onboarding |
| `docs/templates/*.md` | `template-file.template.md` | Component creation guides |

**Template Information**:
- Template source: Imported from `project-docs-pattern/templates/`
- Template approach: Templates define section structure; workflow populates content based on project analysis
- Examples reference: `project-docs-pattern/examples/` for content guidance

**Special Considerations**:
- Templates are copied to workflow's resource folder for self-contained execution
- Generated content adapts to actual codebase structure and naming
- Frontmatter (title, description, author, date) added to all generated files

---

## Workflow Structure Design

### File Structure

```
structure-documentation/
├── workflow.md                         # Entry point & config
├── steps/
│   ├── step-01-init.md                 # Scan → Recommend → Branch
│   ├── step-auto-execute.md            # Autonomous mode (single step, sub-agents)
│   ├── step-guide-01-architecture.md   # Architecture section
│   ├── step-guide-02-development.md    # Development section
│   ├── step-guide-03-templates.md      # Templates section (+ Adv. Elicitation)
│   ├── step-guide-04-reference.md      # Reference section
│   ├── step-guide-05-testing.md        # Testing section
│   ├── step-guide-06-product.md        # Product section
│   ├── step-guide-07-design.md         # Design section (asks if UI project)
│   └── step-guide-08-finalize.md       # Root docs, summary
│
└── templates/                          # Copied from project-docs-pattern/templates/
    ├── readme-root.template.md
    ├── readme-section.template.md
    ├── conditional-docs.template.md
    ├── documentation-standards.template.md
    ├── getting-started.template.md
    └── template-file.template.md
```

### Step Sequence & Flow

```
                    ┌─────────────────┐
                    │  step-01-init   │
                    │ Scan & Recommend│
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ [A] Autonomous  │          │  [G] Guided     │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          guide-01 → guide-02 → guide-03 →
    │step-auto-execute│          guide-04 → guide-05 → guide-06 →
    │ (sub-agents)    │          guide-07 → guide-08 → [DONE]
    └────────┬────────┘
             │
             ▼
         [DONE]
```

### Step Details

| Step | Purpose | Menu Options |
|------|---------|--------------|
| `step-01-init` | Scan project, assess docs, recommend mode | `[A] Autonomous` `[G] Guided` |
| `step-auto-execute` | Sub-agents scan, reorganize, fill gaps, report | Auto-proceed |
| `step-guide-01-architecture` | Architecture section | `[S] Skip` `[C] Continue` |
| `step-guide-02-development` | Development section | `[S] Skip` `[C] Continue` |
| `step-guide-03-templates` | Templates section (code analysis) | `[A] Adv. Elicit` `[S] Skip` `[C] Continue` |
| `step-guide-04-reference` | Reference section | `[S] Skip` `[C] Continue` |
| `step-guide-05-testing` | Testing section | `[S] Skip` `[C] Continue` |
| `step-guide-06-product` | Product section | `[S] Skip` `[C] Continue` |
| `step-guide-07-design` | Design section (asks "UI project?") | `[S] Skip` `[C] Continue` |
| `step-guide-08-finalize` | Root README, CONDITIONAL_DOCS, STANDARDS | `[C] Complete` |

### Interaction Patterns

**Skip Behavior:**
- When user selects `[S] Skip`, create empty folder with placeholder README
- README contains: section name, "This section intentionally left empty", link back to docs root

**Guided Section Pattern:**
1. "Do you have existing documentation for [section]?"
2. If yes → "Please provide the path" → Reorganize into standard structure
3. If no → Ask 1-2 guiding questions → Generate concise document from template

**Templates Section Special Behavior:**
1. "Do you want to create component templates?"
2. If yes → "Provide path to a code file (e.g., `src/services/EmailService.ts`)"
3. Load `template-file.template.md` + analyze code file
4. Generate populated template in `docs/templates/`
5. Repeat until user says done

### Role & Persona

- **Role:** Documentation architect and technical writer
- **Expertise:** Project structure patterns, documentation best practices, code analysis
- **Tone:** Collaborative, concise, pragmatic
- **Behavior:** Intent-based conversation, adapts to user context, keeps it brief

### Data Flow

| Step | Input | Output |
|------|-------|--------|
| Init | Project root access | Scan results, mode recommendation |
| Auto-execute | Entire project | Reorganized `docs/` structure |
| Guide steps | User input, existing files | Section folder + README + primary doc |
| Finalize | All completed sections | Root README, CONDITIONAL_DOCS, STANDARDS |

### No Continuation Support

- Workflow designed for single-session completion
- No `step-01b-continue.md`
- No state persistence between sessions

---

## Build Summary

### Files Generated

**Location:** `_bmad-output/bmb-creations/workflows/structure-documentation/`

**Main Workflow:**
- `workflow.md` - Entry point and configuration

**Step Files (10 total):**
- `steps/step-01-init.md` - Initialization and mode selection
- `steps/step-auto-execute.md` - Autonomous mode execution
- `steps/step-guide-01-architecture.md` - Architecture section
- `steps/step-guide-02-development.md` - Development section
- `steps/step-guide-03-templates.md` - Templates section (with Advanced Elicitation)
- `steps/step-guide-04-reference.md` - Reference section
- `steps/step-guide-05-testing.md` - Testing section
- `steps/step-guide-06-product.md` - Product section
- `steps/step-guide-07-design.md` - Design section
- `steps/step-guide-08-finalize.md` - Finalization

**Template Files (6 total):**
- `templates/readme-root.template.md`
- `templates/readme-section.template.md`
- `templates/conditional-docs.template.md`
- `templates/documentation-standards.template.md`
- `templates/getting-started.template.md`
- `templates/template-file.template.md`

### Build Notes

- All step files follow the BMAD step-template structure
- Templates copied from `project-docs-pattern/templates/` (source of truth)
- Workflow configured for bmm module
- No continuation support (single-session design)

### Next Steps

1. **Review:** Review generated files for accuracy
2. **Install:** Copy to `_bmad/bmm/workflows/structure-documentation/`
3. **Test:** Run the workflow on a test project
4. **Iterate:** Refine based on testing feedback
