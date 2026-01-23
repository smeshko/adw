# Documentation Standards Template

```markdown
---
title: Documentation Standards
description: Required standards for all project documentation
author: {Author}
date: {YYYY-MM-DD}
---

# Documentation Standards

All documentation in this project must follow these standards.

---

## File Structure

### Required Frontmatter

Every markdown file must include YAML frontmatter:

    ```yaml
    ---
    title: Document Title
    description: One-line description
    author: Author Name
    date: YYYY-MM-DD
    ---
    ```

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| General docs | kebab-case | `getting-started.md` |
| Templates | `{name}-template.md` | `service-template.md` |
| ADRs | `adr-NNN-{title}.md` | `adr-001-database-choice.md` |

---

## Markdown Standards

### CommonMark Compliance

- **Headers**: ATX-style only (`#`, `##`, `###`)
- **Header spacing**: Single space after `#`
- **No trailing `#`**: Use `# Title` not `# Title #`
- **Hierarchical headers**: Never skip levels (h1 → h2 → h3)

### Code Blocks

Always indent with a tab the full block and include language identifier:

    ```swift
    // Swift code
    ```

    ```bash
    # Shell commands
    ```

    ```json
    { "json": "data" }
    ```

### Tables

Use for structured data:

    ```markdown
    | Column 1 | Column 2 |
    |----------|----------|
    | Data | Data |
    ```

---

## Content Rules

### Prohibited Content

- **No time estimates**: Never include "this takes 2 hours" or similar
- **No secrets**: Never commit API keys, passwords, credentials
- **No absolute paths**: Use relative paths for internal links
- **No orphan docs**: Every document must be linked from a README

### Required Content

- **Context before detail**: Start with "when to use" or overview
- **Actionable checklists**: Templates must have completion checklists
- **Working links**: All links must resolve to existing files
- **Code examples**: Include copy-paste ready code where applicable

---

## Cross-Referencing

### Internal Links

Use relative paths:
    ```markdown
    [Getting Started](../development/getting-started.md)
    ```

### Section Links

Link to headers:
    ```markdown
    [Integrations Section](service-template.md#integrations)
    ```

### Codebase Links

Reference actual implementations:
    ```markdown
    [Example Implementation](../../src/Services/NetworkService.swift)
    ```

---

## Quality Checklist

Before committing documentation:

- [ ] Frontmatter is complete and accurate
- [ ] All links resolve correctly
- [ ] Code blocks have language identifiers
- [ ] Headers follow hierarchy
- [ ] No time estimates included
- [ ] Document is linked from parent README
- [ ] Spelling and grammar checked
```