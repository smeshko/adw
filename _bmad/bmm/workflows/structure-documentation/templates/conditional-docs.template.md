# Conditional Docs Template

```markdown
---
title: Conditional Documentation Guide
description: Find documentation based on your current task
author: {Author}
date: {YYYY-MM-DD}
---

# Conditional Documentation Guide

Find the right documentation based on what you're trying to accomplish.

---

## Creating New Components

### Adding a New Feature/Module
1. [Feature Template](templates/feature-template.md) - Structure and scaffolding
2. [Architecture Overview](architecture/overview.md) - Understand system patterns
3. [Testing Strategy](testing/testing-strategy.md) - Required test coverage

### Adding a New Service
1. [Service Template](templates/service-template.md) - Interface + implementation
2. [Services Catalog](reference/services-catalog.md) - Existing patterns
3. [Dependency Registration](templates/service-template.md#integrations)

### Adding a New API Endpoint
1. [Controller Template](templates/controller-template.md) - Request handling
2. [API Contracts](reference/api-contracts.md) - Existing endpoints
3. [Error Template](templates/error-template.md) - Error responses

---

## Working with Data

### Creating Database Models
1. [Model Template](templates/model-template.md) - Entity definitions
2. [Data Models Reference](reference/data-models.md) - Existing models
3. [Migration Template](templates/migration-template.md) - Schema changes

### Working with APIs
1. [API Contracts](reference/api-contracts.md) - Endpoint specifications
2. [Service Template](templates/service-template.md) - Network layer

---

## Understanding the System

### New to the Project
1. [Getting Started](development/getting-started.md) - Environment setup
2. [Architecture Overview](architecture/overview.md) - System design
3. [Source Tree](reference/source-tree.md) - Code organization

### Understanding Decisions
1. [ADRs](architecture/adrs/) - Why decisions were made
2. [Technical Architecture](architecture/technical-architecture.md) - How it works

---

## Debugging & Operations

### Fixing Issues
1. [Troubleshooting](development/troubleshooting.md) - Common problems
2. [Services Catalog](reference/services-catalog.md) - Service details

### Deploying Changes
1. [Deployment Guide](development/deployment.md) - Deployment procedures
2. [Testing Strategy](testing/testing-strategy.md) - Pre-deployment checks

---

## Testing

### Writing Tests
1. [Testing Strategy](testing/testing-strategy.md) - Approach and priorities
2. [Template Tests](templates/) - Test patterns in each template

### Running Tests
1. [Testing README](testing/README.md) - Commands and scripts
```