---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/arch-high-level.md
  - docs/arch-entry-point.md
  - docs/arch-orchestrator.md
  - docs/arch-command-system.md
  - docs/arch-llm-executor.md
  - docs/arch-logging.md
workflowType: 'product-brief'
lastStep: 6
project_name: 'adw-sdk'
user_name: 'Ivo'
date: '2025-12-30'
status: 'complete'
---

# Product Brief: adw-sdk

**Date:** 2025-12-30
**Author:** Ivo

---

## Executive Summary

ADW-SDK is an agentic development system that transforms how developers build features with AI. While current approaches rely on ad-hoc prompting or non-deterministic prompt chains that compound errors, ADW-SDK introduces a deterministic, phased pipeline where scripts handle predictable operations and LLMs handle autonomous reasoning. The result: developers provide a small prompt and receive a fully implemented feature with a detailed PR, evidence, and validation.

The timing is ideal—AI coding tools are now capable enough to handle complex reasoning, but the ecosystem is young enough that no established system exists. ADW-SDK fills this gap with deep integrations (CLI, Linear, GitHub), comprehensive observability, and an architecture designed for reliability at any scale.

---

## Core Vision

### Problem Statement

Developers using AI coding assistants face a fundamental reliability problem. Current approaches fall into two categories:

1. **Ad-hoc prompting** — Manually guiding the AI through each step, hoping for coherent output
2. **Prompt chain systems** — Automated but non-deterministic pipelines that compound errors

Both approaches produce inconsistent results. When they fail—and they do—developers get wrong code with no clear path to diagnose or fix the issue.

### Problem Impact

- **Wasted development time** debugging AI-generated code that went off the rails
- **Lack of trust** in AI-assisted development, limiting adoption
- **No audit trail** when things go wrong, making it impossible to understand failures
- **Manual intervention required** at every step, negating the automation benefit

### Why Existing Solutions Fall Short

Current AI coding tools (Claude Code, Aider, Cursor) are powerful but operate as raw capabilities without workflow orchestration. They excel at the reasoning task but lack:

- **Deterministic scaffolding** — No separation between what should be scripted vs. prompted
- **Phase-based execution** — No structured pipeline with checkpoints and artifacts
- **Resumability** — No way to recover from failures without starting over
- **Integration hooks** — No native connection to issue trackers, CI/CD, or deployment systems

### Proposed Solution

ADW-SDK wraps AI coding capabilities in a deterministic, observable pipeline:

**Plan → Build → Validate → Document → Ship**

Each phase:
- Runs **pre-hooks** (scripts) to gather context and set up environment
- Invokes the **LLM** for autonomous reasoning and code generation
- Runs **post-hooks** (scripts) to validate, format, and capture artifacts
- Produces **artifacts** that feed into subsequent phases

The key architectural insight: *anything predictable should be handled by scripts, not prompts*. This creates a robust system where LLMs do what they're good at (reasoning) while deterministic code handles everything else.

### Key Differentiators

1. **Determinism by design** — Scripts handle git, tests, deploys, file operations; LLM handles planning and reasoning
2. **Multiple entry points** — CLI for developers, webhooks for Linear/GitHub, GitHub Actions for CI/CD
3. **Full observability** — State snapshots, LLM stream capture, structured logs enable "time travel" debugging
4. **Pluggable architecture** — Override any phase's prompts, hooks, or configuration at project or user level
5. **Artifact continuity** — Each phase produces artifacts that feed the next, creating an audit trail and enabling resumption

---

## Target Users

### Primary Users

#### 1. The Solo Developer ("Alex")

**Profile:** Mid-to-senior developer working on personal projects or as a solo founder. Uses AI coding tools daily but frustrated by inconsistent results.

**Context:**
- Works on multiple projects, often context-switching
- Values speed but can't afford to ship broken code
- Comfortable with CLI tools and automation
- Already using Claude Code, Aider, or similar tools

**Pain Points:**
- Spends too much time babysitting AI prompts
- Loses context between coding sessions
- No way to reproduce successful AI-assisted workflows
- Debugging AI-generated code takes longer than writing it manually

**Success Vision:** "I describe what I want, walk away, and come back to a working PR with tests passing."

#### 2. The Tech Lead ("Jordan")

**Profile:** Engineering lead at a startup or mid-size company. Responsible for team velocity and code quality. Exploring how to scale AI-assisted development across the team.

**Context:**
- Manages 3-8 developers with varying AI proficiency
- Needs consistent patterns and guardrails
- Cares about code review, testing, and documentation standards
- Looking for ways to multiply team output without sacrificing quality

**Pain Points:**
- Each developer uses AI differently, leading to inconsistent results
- No visibility into how AI is being used or what it's producing
- Hard to enforce standards when AI generates code
- Training team on effective AI usage is time-consuming

**Success Vision:** "The team has a standardized, reliable workflow for AI-assisted development that I can audit and improve over time."

#### 3. The Enterprise Architect ("Morgan")

**Profile:** Senior architect or platform engineer at a large organization. Responsible for developer experience, tooling standards, and governance.

**Context:**
- Operates in regulated environment or with strict compliance requirements
- Needs audit trails and reproducibility for all automated processes
- Integrates with enterprise tools (Jira, GitHub Enterprise, internal CI/CD)
- Evaluates tools for security, compliance, and scalability

**Pain Points:**
- AI coding tools are black boxes with no audit trail
- Can't enforce organizational standards or policies
- No integration with existing enterprise workflows
- Security and compliance teams block adoption without proper controls

**Success Vision:** "AI-assisted development that fits our governance model, integrates with our tools, and provides the audit trail we need."

### Secondary Users

#### DevOps/Platform Engineers
- Set up and maintain ADW-SDK infrastructure
- Configure integrations with CI/CD, issue trackers
- Monitor system health and usage patterns

#### Engineering Managers
- Review metrics on AI-assisted development effectiveness
- Make decisions about tooling investments
- Track team productivity improvements

---

## Success Metrics

### User Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Feature completion rate** | >80% of runs complete successfully | Runs ending in "ship" phase / total runs |
| **Time to feature** | 50% reduction vs. manual | Time from prompt to merged PR |
| **Resume success rate** | >90% of failed runs recoverable | Successful resumes / failed runs |
| **First-run success** | >60% complete without intervention | Runs with no human gates triggered |

### Business Objectives

**3-Month Goals:**
- Functional MVP with CLI entry point and core phases
- 10+ early adopter developers actively using the system
- Validated core value proposition (determinism + observability)

**12-Month Goals:**
- Full integration suite (Linear, GitHub, GitHub Actions)
- Enterprise-ready with audit logging and compliance features
- Community of users contributing custom commands and configurations

### Key Performance Indicators

**Adoption:**
- Weekly active users (CLI invocations)
- Projects with `.agent/` configuration
- GitHub stars / community engagement

**Reliability:**
- Phase success rate by phase type
- Mean time to recovery (resume success)
- Error rate by error type (LLM vs. script vs. validation)

**Value Creation:**
- Features shipped per user per week
- Time saved vs. baseline (self-reported or measured)
- Code quality metrics (test coverage, lint errors) post-ADW vs. pre-ADW

---

## MVP Scope

### Core Features (Must Have)

1. **CLI Entry Point**
   - `agent run "feature description"` — Full pipeline execution
   - `agent run --phase plan` — Single phase execution
   - `agent resume <run_id>` — Resume from failure
   - `agent status <run_id>` — Check run status

2. **Core Phases: Plan → Build → Validate → Document**
   - **Plan:** Generate implementation plan from feature request
   - **Build:** Execute plan with LLM-driven code generation
   - **Validate:** Run tests and linters, capture results
   - **Document:** Generate PR description, changelog, and documentation updates

3. **Command System**
   - Default commands for plan/build/validate phases
   - Project-level overrides via `.agent/commands/`
   - Prompt templates with variable substitution
   - Pre/post hooks for deterministic operations

4. **Claude Code Executor**
   - Primary LLM executor wrapping Claude Code CLI
   - Streaming output with tool call capture
   - Retry logic for transient failures

5. **Context & Artifact Management**
   - Run context persistence (`.agent/runs/<id>/`)
   - Artifact storage per phase
   - State snapshots for debugging

6. **Basic Observability**
   - Console output with phase progress
   - Raw logs for debugging
   - Context.json for run state

### Out of Scope for MVP

- **Webhook entry points** (Linear, GitHub) — Post-MVP
- **GitHub Action adapter** — Post-MVP
- **Ship phase** (deployment automation) — Post-MVP
- **Custom LLM executors** (Aider, Ollama) — Post-MVP
- **Enterprise features** (SSO, advanced audit logging) — Future
- **Team collaboration features** — Future
- **Command marketplace** — Future

### MVP Success Criteria

The MVP is successful when:

1. **Core loop works reliably** — User can go from prompt to validated code in a single run
2. **Failures are recoverable** — User can resume from any failed phase
3. **Observability enables debugging** — User can diagnose issues from logs and artifacts
4. **Customization is possible** — User can override prompts and hooks for their project

**Go/No-Go Decision Point:**
- 10+ developers complete 50+ successful runs
- >70% of runs complete without manual intervention
- Resume success rate >80%
- Qualitative feedback confirms value proposition

### Future Vision

**Phase 2: Integration & Scale**
- Linear webhook integration (issue → automatic implementation)
- GitHub webhook integration (PR events → validation)
- GitHub Actions for CI/CD integration
- Document and Ship phases

**Phase 3: Enterprise & Teams**
- Team workspaces with shared configurations
- Role-based access and approval workflows
- Advanced audit logging and compliance reports
- SSO and enterprise identity integration

**Phase 4: Ecosystem**
- Custom executor support (bring your own LLM)
- Command marketplace (share and discover configurations)
- Plugin system for custom phases
- Analytics dashboard for productivity insights

---

## Strategic Decisions

### Target Market & Business Model
- **Initial Focus:** Solo developers — optimize for quick iteration, community building, and word-of-mouth growth
- **Pricing Model:** Freemium — free tier for individual developers, paid tiers for teams/enterprise features
- **Go-to-Market:** Developer-first, bottom-up adoption

### Technical Decisions
- **Language:** Python
- **LLM Executor:** Claude Code only for MVP
- **Distribution:** TBD during architecture session

---

*Product Brief completed on 2025-12-30*
