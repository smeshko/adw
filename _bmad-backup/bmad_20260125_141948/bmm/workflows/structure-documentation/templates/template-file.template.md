# Component template

```markdown
---
title: {Component} Template
description: Step-by-step guide for creating {component}
author: {Author}
date: {YYYY-MM-DD}
---

# {Component} Template

## When to Use

- Bullet point describing use case 1
- Bullet point describing use case 2
- Bullet point describing use case 3

## Quick Reference

| Aspect | Value |
|--------|-------|
| Location | `path/to/{Component}/` |
| Pattern | Pattern name or approach |
| Naming | `{Name}{Component}.{ext}` |
| Dependencies | List any required dependencies |

## Directory Structure

    ```text
    {Component}/
    ├── file1.{ext}           # Purpose of file
    ├── file2.{ext}           # Purpose of file
    └── subdir/
        └── file3.{ext}       # Purpose of file
    ```

## Code Templates

### {First File/Component}

    ```{language}
    // {Component} - {purpose}
    // Location: path/to/file.{ext}

    {code with {Placeholder} tokens}
    ```

### {Second File/Component}

    ```{language}
    // Additional code template
    {code}
    ```

## Existing Patterns

### {ExampleName}
Location: `path/to/existing/Example.{ext}`

    ```{language}
    // Relevant excerpt from actual codebase
    ```

## Integrations

### {Registry/Config} Registration

    ```{language}
    // Code needed to integrate the component
    ```

### Package/Dependency Setup

    ```{language}
    // Any package manager configuration
    ```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| Bad practice | Explanation | Correct approach |

{## Custom sections}

Any heading-level-2 custom sections specific to this component that should be in the template file

## Checklist

- [ ] Created {component} file at correct location
- [ ] Followed naming conventions
- [ ] Implemented required patterns
- [ ] Added to registry/configuration
- [ ] Tests added
- [ ] Documentation updated

## References

- [Related Template](related-template.md)
- [Architecture Doc](../architecture/relevant.md)
- [Example Implementation](../../src/path/to/Example.{ext})
```