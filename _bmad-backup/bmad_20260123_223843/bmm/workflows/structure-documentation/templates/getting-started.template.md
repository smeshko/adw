# Getting Started Template

```markdown
---
title: Getting Started
description: Environment setup and first run guide
author: {Author}
date: {YYYY-MM-DD}
---

# Getting Started

Get your development environment set up and run the project.

## Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| {Language} | {version}+ | [Download]({url}) |
| {Tool} | {version}+ | `{install command}` |
| {Database} | {version}+ | [Instructions]({url}) |

## Quick Start

    ```bash
    # 1. Clone the repository
    git clone {repo-url}
    cd {project}

    # 2. Install dependencies
    {install command}

    # 3. Configure environment
    cp .env.example .env
    # Edit .env with your settings

    # 4. Start the application
    {start command}
    ```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `postgres://localhost/mydb` |
| `API_KEY` | External API key | `sk-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `info` |
| `PORT` | Server port | `8080` |

## Verification

Confirm your setup is working:

    ```bash
    # Run tests
    {test command}

    # Check health endpoint (if applicable)
    curl http://localhost:{port}/health

    # check build command succeeds (if applicable)
    swift build
    ```

Expected output:
    ```json
    { "status": "ok" }
    ```

## Common Setup Issues

### Issue: {Common Problem 1}

**Symptom**: {What you see}

**Solution**:
    ```bash
    {fix command}
    ```

### Issue: {Common Problem 2}

**Symptom**: {What you see}

**Solution**: {Explanation of fix}

## Next Steps

1. [Architecture Overview](../architecture/overview.md) - Understand the system
2. [Templates](../templates/) - Start building features
3. [Troubleshooting](troubleshooting.md) - If you encounter issues
```