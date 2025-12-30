# Entry Point Adapters - Deep Dive

## Overview

Entry Point Adapters are the outermost layer of the system. They receive input from various sources and normalize it into a standard `RunRequest` that the Orchestrator Core can process.

**Design Principles:**

- **Single Responsibility** — Each adapter only knows about its source format
- **Fail-Fast Validation** — Reject malformed input at the edge
- **Preserve Raw Data** — Always keep original payload for debugging
- **Stateless** — Adapters don't maintain state between invocations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINT ADAPTERS                                 │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │     CLI     │  │   Linear    │  │   GitHub    │  │   GitHub Action     │ │
│  │   Adapter   │  │   Adapter   │  │   Adapter   │  │      Adapter        │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                    │            │
│         └────────────────┴────────────────┴────────────────────┘            │
│                                    │                                        │
│                                    ▼                                        │
│                          ┌─────────────────┐                                │
│                          │   RunRequest    │                                │
│                          │   (normalized)  │                                │
│                          └────────┬────────┘                                │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
                           Orchestrator Core
```

---

## Common Interface

All adapters implement a common interface:

```typescript
interface EntryPointAdapter<TInput> {
  readonly name: string
  readonly triggerSource: TriggerSource
  
  /**
   * Validate raw input before processing.
   * Throws AdapterValidationError if invalid.
   */
  validate(input: TInput): ValidationResult
  
  /**
   * Parse and normalize input into a RunRequest.
   * Assumes input has passed validation.
   */
  parse(input: TInput): RunRequest
  
  /**
   * Optional: Extract callback information for status updates.
   */
  getCallback?(input: TInput): CallbackConfig | null
}

interface ValidationResult {
  valid: boolean
  errors?: ValidationError[]
}

interface ValidationError {
  field: string
  message: string
  code: string  // Machine-readable error code
}

type TriggerSource = "cli" | "linear" | "github_webhook" | "github_action"
```

### RunRequest Schema

The normalized output all adapters produce:

```typescript
interface RunRequest {
  // Core request
  featureRequest: string          // What to build/do
  
  // Source tracking
  triggerSource: TriggerSource
  triggerPayload: unknown         // Raw input preserved
  triggerTimestamp: string        // ISO 8601
  
  // Execution options
  options: RunOptions
  
  // External system integration
  metadata: RunMetadata
}

interface RunOptions {
  // Phase control
  phases?: Phase[]                // Default: all phases
  startFromPhase?: Phase          // Skip earlier phases
  stopAfterPhase?: Phase          // Don't continue past this
  
  // Execution modes
  dryRun: boolean                 // Default: false
  interactive: boolean            // Can prompt for input?
  
  // Resumption
  resumeRunId?: string            // Continue a previous run
  
  // Overrides
  configOverrides?: Partial<PhaseConfig>
}

interface RunMetadata {
  // External references
  externalId?: string             // Issue ID, PR number, etc.
  externalUrl?: string            // Link back to source
  
  // Callbacks
  callbackUrl?: string            // POST status updates here
  callbackAuth?: CallbackAuth     // How to authenticate callbacks
  
  // Categorization
  labels?: string[]               // From source (Linear labels, GH labels)
  priority?: "low" | "normal" | "high" | "urgent"
  
  // Assignment
  requestedBy?: string            // Who triggered this
  assignedTo?: string             // Who should review
  
  // Repository context (for webhook sources)
  repository?: {
    owner: string
    name: string
    defaultBranch: string
    cloneUrl: string
  }
  
  // PR context (if triggered by PR)
  pullRequest?: {
    number: number
    baseBranch: string
    headBranch: string
    isDraft: boolean
  }
}

type Phase = "plan" | "build" | "validate" | "document" | "ship"
```

---

## CLI Adapter

The CLI adapter parses command-line arguments and flags.

### Input Format

```bash
# Basic usage
agent run "Add user authentication"

# With options
agent run "Add OAuth support" \
  --phase plan \
  --dry-run \
  --verbose

# Resume a failed run
agent resume run_abc123

# Run specific phases
agent run "Fix login bug" --phases validate,ship

# From stdin (for piping)
echo "Add dark mode" | agent run -

# With config overrides
agent run "Add feature" --timeout 600 --no-approval
```

### Adapter Implementation

```typescript
interface CLIInput {
  command: "run" | "resume" | "status"
  args: string[]
  flags: Record<string, string | boolean>
  stdin?: string
  env: Record<string, string>
  cwd: string
  isInteractive: boolean  // Is TTY attached?
}

class CLIAdapter implements EntryPointAdapter<CLIInput> {
  readonly name = "cli"
  readonly triggerSource: TriggerSource = "cli"
  
  validate(input: CLIInput): ValidationResult {
    const errors: ValidationError[] = []
    
    // Command validation
    if (!["run", "resume", "status"].includes(input.command)) {
      errors.push({
        field: "command",
        message: `Unknown command: ${input.command}`,
        code: "UNKNOWN_COMMAND"
      })
    }
    
    // Run command requires feature request
    if (input.command === "run") {
      const featureRequest = this.extractFeatureRequest(input)
      if (!featureRequest) {
        errors.push({
          field: "args[0]",
          message: "Feature request is required",
          code: "MISSING_FEATURE_REQUEST"
        })
      }
    }
    
    // Resume command requires run ID
    if (input.command === "resume" && !input.args[0]) {
      errors.push({
        field: "args[0]",
        message: "Run ID is required for resume",
        code: "MISSING_RUN_ID"
      })
    }
    
    // Validate phase names if provided
    if (input.flags.phases) {
      const phases = String(input.flags.phases).split(",")
      const validPhases = ["plan", "build", "validate", "document", "ship"]
      for (const phase of phases) {
        if (!validPhases.includes(phase.trim())) {
          errors.push({
            field: "flags.phases",
            message: `Invalid phase: ${phase}`,
            code: "INVALID_PHASE"
          })
        }
      }
    }
    
    return { valid: errors.length === 0, errors }
  }
  
  parse(input: CLIInput): RunRequest {
    const featureRequest = this.extractFeatureRequest(input)
    
    return {
      featureRequest,
      triggerSource: "cli",
      triggerPayload: {
        command: input.command,
        args: input.args,
        flags: input.flags,
        cwd: input.cwd
      },
      triggerTimestamp: new Date().toISOString(),
      
      options: {
        phases: this.parsePhases(input.flags),
        startFromPhase: input.flags["start-from"] as Phase,
        stopAfterPhase: input.flags["stop-after"] as Phase,
        dryRun: Boolean(input.flags["dry-run"]),
        interactive: input.isInteractive && !input.flags["no-interactive"],
        resumeRunId: input.command === "resume" ? input.args[0] : undefined,
        configOverrides: this.parseConfigOverrides(input.flags)
      },
      
      metadata: {
        requestedBy: input.env.USER || input.env.USERNAME,
        labels: this.parseLabels(input.flags)
      }
    }
  }
  
  private extractFeatureRequest(input: CLIInput): string {
    // From positional arg
    if (input.args[0] && input.args[0] !== "-") {
      return input.args[0]
    }
    // From stdin
    if (input.stdin) {
      return input.stdin.trim()
    }
    return ""
  }
  
  private parsePhases(flags: Record<string, string | boolean>): Phase[] | undefined {
    if (!flags.phases && !flags.phase) return undefined
    
    const phaseStr = String(flags.phases || flags.phase)
    return phaseStr.split(",").map(p => p.trim() as Phase)
  }
  
  private parseConfigOverrides(flags: Record<string, string | boolean>): Partial<PhaseConfig> {
    const overrides: Partial<PhaseConfig> = {}
    
    if (flags.timeout) {
      overrides.timeout_seconds = Number(flags.timeout)
    }
    if (flags["no-approval"]) {
      overrides.require_approval = false
    }
    if (flags.temperature !== undefined) {
      overrides.llm = { temperature: Number(flags.temperature) }
    }
    
    return Object.keys(overrides).length > 0 ? overrides : undefined
  }
  
  private parseLabels(flags: Record<string, string | boolean>): string[] | undefined {
    if (!flags.labels) return undefined
    return String(flags.labels).split(",").map(l => l.trim())
  }
}
```

### CLI Argument Specification

```
USAGE:
  agent <command> [options] [arguments]

COMMANDS:
  run <request>       Run the agent pipeline with a feature request
  resume <run_id>     Resume a previously failed or paused run
  status <run_id>     Check the status of a run

RUN OPTIONS:
  --phase <phase>         Run only a single phase
  --phases <p1,p2,...>    Run only specified phases (comma-separated)
  --start-from <phase>    Start from this phase (skip earlier)
  --stop-after <phase>    Stop after this phase (skip later)
  
  --dry-run               Show what would happen without executing
  --no-interactive        Disable interactive prompts
  
  --timeout <seconds>     Override timeout for LLM calls
  --no-approval           Skip approval gates
  --temperature <float>   Override LLM temperature
  
  --labels <l1,l2,...>    Add labels to this run

GLOBAL OPTIONS:
  -v, --verbose           Increase verbosity
  -q, --quiet             Decrease verbosity
  --trace                 Maximum verbosity (debug)
  --help                  Show help
  --version               Show version

EXAMPLES:
  agent run "Add user authentication with OAuth"
  agent run "Fix bug in payment flow" --phase validate
  agent run "Refactor database layer" --dry-run --verbose
  agent resume run_abc123
  echo "Add dark mode" | agent run -
```

---

## Linear Webhook Adapter

The Linear adapter handles webhooks from Linear when issues are created or updated.

### Linear Webhook Payload

Linear sends webhooks with this structure:

```typescript
interface LinearWebhookPayload {
  action: "create" | "update" | "remove"
  type: "Issue" | "Comment" | "Project" | ...
  createdAt: string
  data: LinearIssue | LinearComment | ...
  url: string
  organizationId: string
  webhookTimestamp: number
  webhookId: string
}

interface LinearIssue {
  id: string
  identifier: string          // e.g., "ENG-123"
  title: string
  description?: string        // Markdown
  priority: number            // 0=none, 1=urgent, 2=high, 3=normal, 4=low
  state: {
    id: string
    name: string              // e.g., "Backlog", "In Progress"
    type: string              // "backlog" | "unstarted" | "started" | "completed" | "canceled"
  }
  labels: {
    nodes: Array<{
      id: string
      name: string
      color: string
    }>
  }
  assignee?: {
    id: string
    name: string
    email: string
  }
  creator: {
    id: string
    name: string
    email: string
  }
  team: {
    id: string
    name: string
    key: string               // e.g., "ENG"
  }
  project?: {
    id: string
    name: string
  }
  url: string
  createdAt: string
  updatedAt: string
}
```

### Adapter Implementation

```typescript
interface LinearWebhookInput {
  headers: Record<string, string>
  body: LinearWebhookPayload
  rawBody: string  // For signature verification
}

class LinearAdapter implements EntryPointAdapter<LinearWebhookInput> {
  readonly name = "linear"
  readonly triggerSource: TriggerSource = "linear"
  
  constructor(
    private config: {
      webhookSecret: string
      triggerLabels?: string[]      // Only process issues with these labels
      triggerStates?: string[]      // Only process issues in these states
      teamFilter?: string[]         // Only process issues from these teams
    }
  ) {}
  
  validate(input: LinearWebhookInput): ValidationResult {
    const errors: ValidationError[] = []
    
    // Verify webhook signature
    if (!this.verifySignature(input)) {
      errors.push({
        field: "headers.linear-signature",
        message: "Invalid webhook signature",
        code: "INVALID_SIGNATURE"
      })
      return { valid: false, errors }  // Fail fast on auth
    }
    
    // Must be an Issue event
    if (input.body.type !== "Issue") {
      errors.push({
        field: "body.type",
        message: `Unsupported event type: ${input.body.type}`,
        code: "UNSUPPORTED_EVENT_TYPE"
      })
    }
    
    // Must be create or specific update
    if (!["create", "update"].includes(input.body.action)) {
      errors.push({
        field: "body.action",
        message: `Unsupported action: ${input.body.action}`,
        code: "UNSUPPORTED_ACTION"
      })
    }
    
    // Check team filter
    if (this.config.teamFilter?.length) {
      const issue = input.body.data as LinearIssue
      if (!this.config.teamFilter.includes(issue.team.key)) {
        errors.push({
          field: "body.data.team",
          message: `Team ${issue.team.key} not in allowed teams`,
          code: "TEAM_FILTERED"
        })
      }
    }
    
    return { valid: errors.length === 0, errors }
  }
  
  parse(input: LinearWebhookInput): RunRequest {
    const issue = input.body.data as LinearIssue
    
    // Build feature request from title + description
    const featureRequest = this.buildFeatureRequest(issue)
    
    // Determine phases based on labels or state
    const phases = this.determinePhasesFromLabels(issue)
    
    // Map Linear priority to our priority
    const priority = this.mapPriority(issue.priority)
    
    return {
      featureRequest,
      triggerSource: "linear",
      triggerPayload: input.body,
      triggerTimestamp: input.body.createdAt,
      
      options: {
        phases,
        dryRun: this.hasDryRunLabel(issue),
        interactive: false,  // Webhooks are never interactive
      },
      
      metadata: {
        externalId: issue.id,
        externalUrl: issue.url,
        callbackUrl: this.buildCallbackUrl(issue),
        labels: issue.labels.nodes.map(l => l.name),
        priority,
        requestedBy: issue.creator.email,
        assignedTo: issue.assignee?.email,
      }
    }
  }
  
  getCallback(input: LinearWebhookInput): CallbackConfig | null {
    const issue = input.body.data as LinearIssue
    
    return {
      type: "linear",
      issueId: issue.id,
      // We'll update issue state and add comments
      actions: {
        onStart: { setState: "started", addComment: true },
        onPhaseComplete: { addComment: true },
        onSuccess: { setState: "completed", addComment: true },
        onFailure: { setState: "backlog", addComment: true, addLabel: "agent-failed" }
      }
    }
  }
  
  private verifySignature(input: LinearWebhookInput): boolean {
    const signature = input.headers["linear-signature"]
    if (!signature) return false
    
    const hmac = crypto.createHmac("sha256", this.config.webhookSecret)
    hmac.update(input.rawBody)
    const expected = hmac.digest("hex")
    
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expected)
    )
  }
  
  private buildFeatureRequest(issue: LinearIssue): string {
    let request = issue.title
    
    if (issue.description) {
      // Include description but truncate if too long
      const desc = issue.description.length > 2000
        ? issue.description.slice(0, 2000) + "..."
        : issue.description
      request += `\n\n${desc}`
    }
    
    return request
  }
  
  private determinePhasesFromLabels(issue: LinearIssue): Phase[] | undefined {
    const labelNames = issue.labels.nodes.map(l => l.name.toLowerCase())
    
    // Label-based phase selection
    if (labelNames.includes("plan-only")) return ["plan"]
    if (labelNames.includes("validate-only")) return ["validate"]
    if (labelNames.includes("no-ship")) return ["plan", "build", "validate", "document"]
    
    // Default: all phases
    return undefined
  }
  
  private hasDryRunLabel(issue: LinearIssue): boolean {
    return issue.labels.nodes.some(l => 
      l.name.toLowerCase() === "dry-run" || 
      l.name.toLowerCase() === "dryrun"
    )
  }
  
  private mapPriority(linearPriority: number): RunMetadata["priority"] {
    switch (linearPriority) {
      case 1: return "urgent"
      case 2: return "high"
      case 3: return "normal"
      case 4: return "low"
      default: return "normal"
    }
  }
  
  private buildCallbackUrl(issue: LinearIssue): string {
    // Linear API endpoint for updating issues
    return `https://api.linear.app/issues/${issue.id}`
  }
}
```

### Linear Event-to-Phase Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LINEAR EVENT → PHASE MAPPING                             │
│                                                                             │
│  Trigger Conditions:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Issue created with label "agent" or "automate"                          ││
│  │            OR                                                           ││
│  │ Issue moved to state "Ready for Agent"                                  ││
│  │            OR                                                           ││
│  │ Comment "@agent run" on any issue                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Phase Selection (via labels):                                              │
│  ┌───────────────────────┬─────────────────────────────────────────────────┐│
│  │ Label                 │ Phases                                          ││
│  ├───────────────────────┼─────────────────────────────────────────────────┤│
│  │ (no special label)    │ plan → build → validate → document → ship      ││
│  │ plan-only             │ plan                                            ││
│  │ no-ship               │ plan → build → validate → document              ││
│  │ validate-only         │ validate (assumes code already exists)          ││
│  │ ship-only             │ ship (assumes validation passed)                ││
│  │ dry-run               │ All phases in dry-run mode                      ││
│  └───────────────────────┴─────────────────────────────────────────────────┘│
│                                                                             │
│  Status Updates (back to Linear):                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Run started    → Move to "In Progress", comment with run ID            ││
│  │ Phase complete → Comment with summary                                   ││
│  │ Run succeeded  → Move to "Done", comment with results                  ││
│  │ Run failed     → Move to "Backlog", comment with error, add label      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GitHub Webhook Adapter

The GitHub adapter handles webhooks for issues, PRs, and comments.

### GitHub Webhook Payloads

```typescript
// Common webhook structure
interface GitHubWebhookPayload {
  action: string
  sender: GitHubUser
  repository: GitHubRepository
  organization?: GitHubOrganization
  installation?: { id: number }
}

// Issue event
interface GitHubIssueEvent extends GitHubWebhookPayload {
  action: "opened" | "edited" | "labeled" | "assigned" | ...
  issue: GitHubIssue
  label?: GitHubLabel          // For "labeled" action
}

// PR event
interface GitHubPullRequestEvent extends GitHubWebhookPayload {
  action: "opened" | "synchronize" | "ready_for_review" | ...
  number: number
  pull_request: GitHubPullRequest
}

// Issue/PR comment event
interface GitHubCommentEvent extends GitHubWebhookPayload {
  action: "created" | "edited" | "deleted"
  comment: GitHubComment
  issue?: GitHubIssue
  pull_request?: GitHubPullRequest
}

interface GitHubPullRequest {
  number: number
  title: string
  body: string | null
  state: "open" | "closed"
  draft: boolean
  head: {
    ref: string               // Branch name
    sha: string
    repo: GitHubRepository
  }
  base: {
    ref: string               // Target branch
    sha: string
    repo: GitHubRepository
  }
  user: GitHubUser
  labels: GitHubLabel[]
  html_url: string
  diff_url: string
  created_at: string
  updated_at: string
}
```

### Adapter Implementation

```typescript
interface GitHubWebhookInput {
  headers: Record<string, string>
  body: GitHubWebhookPayload
  rawBody: string
}

class GitHubWebhookAdapter implements EntryPointAdapter<GitHubWebhookInput> {
  readonly name = "github_webhook"
  readonly triggerSource: TriggerSource = "github_webhook"
  
  constructor(
    private config: {
      webhookSecret: string
      appId?: number
      triggerEvents: GitHubTriggerConfig
    }
  ) {}
  
  validate(input: GitHubWebhookInput): ValidationResult {
    const errors: ValidationError[] = []
    
    // Verify webhook signature
    if (!this.verifySignature(input)) {
      errors.push({
        field: "headers.x-hub-signature-256",
        message: "Invalid webhook signature",
        code: "INVALID_SIGNATURE"
      })
      return { valid: false, errors }
    }
    
    // Check if this is a supported event type
    const eventType = input.headers["x-github-event"]
    if (!this.isSupportedEvent(eventType, input.body)) {
      errors.push({
        field: "headers.x-github-event",
        message: `Event not configured as trigger: ${eventType}/${input.body.action}`,
        code: "EVENT_NOT_TRIGGER"
      })
    }
    
    return { valid: errors.length === 0, errors }
  }
  
  parse(input: GitHubWebhookInput): RunRequest {
    const eventType = input.headers["x-github-event"]
    
    switch (eventType) {
      case "issues":
        return this.parseIssueEvent(input.body as GitHubIssueEvent)
      case "pull_request":
        return this.parsePullRequestEvent(input.body as GitHubPullRequestEvent)
      case "issue_comment":
      case "pull_request_review_comment":
        return this.parseCommentEvent(input.body as GitHubCommentEvent)
      default:
        throw new Error(`Unhandled event type: ${eventType}`)
    }
  }
  
  private parseIssueEvent(event: GitHubIssueEvent): RunRequest {
    const featureRequest = this.buildFeatureRequestFromIssue(event.issue)
    
    return {
      featureRequest,
      triggerSource: "github_webhook",
      triggerPayload: event,
      triggerTimestamp: new Date().toISOString(),
      
      options: {
        phases: this.determinePhasesFromLabels(event.issue.labels),
        dryRun: this.hasDryRunLabel(event.issue.labels),
        interactive: false,
      },
      
      metadata: {
        externalId: `issue-${event.issue.number}`,
        externalUrl: event.issue.html_url,
        labels: event.issue.labels.map(l => l.name),
        requestedBy: event.issue.user.login,
        assignedTo: event.issue.assignee?.login,
        repository: {
          owner: event.repository.owner.login,
          name: event.repository.name,
          defaultBranch: event.repository.default_branch,
          cloneUrl: event.repository.clone_url,
        }
      }
    }
  }
  
  private parsePullRequestEvent(event: GitHubPullRequestEvent): RunRequest {
    const pr = event.pull_request
    
    // For PRs, we typically only validate (not plan/build)
    const featureRequest = this.buildFeatureRequestFromPR(pr)
    
    return {
      featureRequest,
      triggerSource: "github_webhook",
      triggerPayload: event,
      triggerTimestamp: new Date().toISOString(),
      
      options: {
        // PRs default to validate phase only
        phases: this.determinePhasesfromPREvent(event),
        dryRun: this.hasDryRunLabel(pr.labels),
        interactive: false,
      },
      
      metadata: {
        externalId: `pr-${pr.number}`,
        externalUrl: pr.html_url,
        labels: pr.labels.map(l => l.name),
        requestedBy: pr.user.login,
        repository: {
          owner: event.repository.owner.login,
          name: event.repository.name,
          defaultBranch: event.repository.default_branch,
          cloneUrl: event.repository.clone_url,
        },
        pullRequest: {
          number: pr.number,
          baseBranch: pr.base.ref,
          headBranch: pr.head.ref,
          isDraft: pr.draft,
        }
      }
    }
  }
  
  private parseCommentEvent(event: GitHubCommentEvent): RunRequest {
    // Parse command from comment body
    const command = this.parseAgentCommand(event.comment.body)
    
    // Get context (issue or PR)
    const context = event.pull_request || event.issue
    const featureRequest = command.request || context.title
    
    return {
      featureRequest,
      triggerSource: "github_webhook",
      triggerPayload: event,
      triggerTimestamp: new Date().toISOString(),
      
      options: {
        phases: command.phases,
        dryRun: command.dryRun,
        interactive: false,
      },
      
      metadata: {
        externalId: event.pull_request 
          ? `pr-${event.pull_request.number}`
          : `issue-${event.issue.number}`,
        externalUrl: event.comment.html_url,
        requestedBy: event.comment.user.login,
        repository: {
          owner: event.repository.owner.login,
          name: event.repository.name,
          defaultBranch: event.repository.default_branch,
          cloneUrl: event.repository.clone_url,
        },
        pullRequest: event.pull_request ? {
          number: event.pull_request.number,
          baseBranch: event.pull_request.base.ref,
          headBranch: event.pull_request.head.ref,
          isDraft: event.pull_request.draft,
        } : undefined
      }
    }
  }
  
  /**
   * Parse commands like:
   *   @agent run
   *   @agent plan "Add feature X"
   *   @agent validate --dry-run
   */
  private parseAgentCommand(body: string): AgentCommand {
    const match = body.match(/@agent\s+(\w+)(?:\s+"([^"]+)")?(?:\s+(.*))?/i)
    
    if (!match) {
      return { action: "run" }
    }
    
    const [, action, request, flagsStr] = match
    const flags = this.parseFlags(flagsStr || "")
    
    return {
      action: action.toLowerCase(),
      request,
      phases: this.actionToPhases(action),
      dryRun: flags.includes("dry-run"),
    }
  }
  
  private actionToPhases(action: string): Phase[] | undefined {
    switch (action.toLowerCase()) {
      case "plan": return ["plan"]
      case "build": return ["plan", "build"]
      case "validate": return ["validate"]
      case "ship": return ["ship"]
      case "run": return undefined  // All phases
      default: return undefined
    }
  }
  
  private determinePhasesfromPREvent(event: GitHubPullRequestEvent): Phase[] {
    // New PR or push to PR → validate
    if (["opened", "synchronize", "ready_for_review"].includes(event.action)) {
      return ["validate"]
    }
    
    // PR merged → could trigger ship
    if (event.action === "closed" && event.pull_request.merged) {
      return ["ship"]
    }
    
    return ["validate"]
  }
  
  private verifySignature(input: GitHubWebhookInput): boolean {
    const signature = input.headers["x-hub-signature-256"]
    if (!signature) return false
    
    const hmac = crypto.createHmac("sha256", this.config.webhookSecret)
    hmac.update(input.rawBody)
    const expected = `sha256=${hmac.digest("hex")}`
    
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expected)
    )
  }
  
  private buildFeatureRequestFromIssue(issue: GitHubIssue): string {
    let request = issue.title
    if (issue.body) {
      const body = issue.body.length > 2000
        ? issue.body.slice(0, 2000) + "..."
        : issue.body
      request += `\n\n${body}`
    }
    return request
  }
  
  private buildFeatureRequestFromPR(pr: GitHubPullRequest): string {
    return `Review and validate PR #${pr.number}: ${pr.title}\n\n${pr.body || ""}`
  }
  
  getCallback(input: GitHubWebhookInput): CallbackConfig | null {
    const eventType = input.headers["x-github-event"]
    
    return {
      type: "github",
      repository: {
        owner: input.body.repository.owner.login,
        name: input.body.repository.name,
      },
      // Report status via commit status API and/or comments
      actions: {
        onStart: { 
          createCommitStatus: "pending",
          addComment: true 
        },
        onPhaseComplete: { 
          addComment: true 
        },
        onSuccess: { 
          createCommitStatus: "success",
          addComment: true 
        },
        onFailure: { 
          createCommitStatus: "failure",
          addComment: true,
          addLabel: "agent-failed"
        }
      }
    }
  }
}
```

### GitHub Event-to-Phase Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GITHUB EVENT → PHASE MAPPING                              │
│                                                                             │
│  Issue Events:                                                              │
│  ┌────────────────────────────┬────────────────────────────────────────────┐│
│  │ Event                      │ Default Phases                             ││
│  ├────────────────────────────┼────────────────────────────────────────────┤│
│  │ Issue opened + label:agent │ plan → build → validate → document → ship ││
│  │ Issue labeled with "agent" │ plan → build → validate → document → ship ││
│  │ Comment: @agent run        │ plan → build → validate → document → ship ││
│  │ Comment: @agent plan       │ plan                                       ││
│  │ Comment: @agent validate   │ validate                                   ││
│  └────────────────────────────┴────────────────────────────────────────────┘│
│                                                                             │
│  Pull Request Events:                                                       │
│  ┌────────────────────────────┬────────────────────────────────────────────┐│
│  │ Event                      │ Default Phases                             ││
│  ├────────────────────────────┼────────────────────────────────────────────┤│
│  │ PR opened                  │ validate                                   ││
│  │ PR synchronized (push)     │ validate                                   ││
│  │ PR ready_for_review        │ validate                                   ││
│  │ PR merged                  │ ship (if configured)                       ││
│  │ Comment: @agent run        │ validate → document                        ││
│  │ Comment: @agent ship       │ ship                                       ││
│  └────────────────────────────┴────────────────────────────────────────────┘│
│                                                                             │
│  Status Updates (back to GitHub):                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ • Commit status: pending/success/failure                                ││
│  │ • PR comment with run progress and results                              ││
│  │ • Check run (if GitHub App) with detailed annotations                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GitHub Action Adapter

The GitHub Action adapter runs inside GitHub Actions and receives input via action inputs.

### Action Inputs (action.yml)

```yaml
name: 'Agent Run'
description: 'Run the agentic development pipeline'
inputs:
  feature-request:
    description: 'What to build (defaults to issue/PR title)'
    required: false
  phases:
    description: 'Comma-separated list of phases to run'
    required: false
  dry-run:
    description: 'Run in dry-run mode'
    required: false
    default: 'false'
  config-path:
    description: 'Path to agent config file'
    required: false
    default: '.agent/project.yaml'
outputs:
  run-id:
    description: 'The ID of the agent run'
  status:
    description: 'Final status: success, failure, or skipped'
  artifact-path:
    description: 'Path to run artifacts'
```

### Adapter Implementation

```typescript
interface GitHubActionInput {
  // Action inputs
  inputs: {
    "feature-request"?: string
    phases?: string
    "dry-run"?: string
    "config-path"?: string
  }
  
  // GitHub context (from @actions/github)
  context: {
    eventName: string           // "push", "pull_request", "issues", etc.
    sha: string
    ref: string
    workflow: string
    action: string
    actor: string
    job: string
    runNumber: number
    runId: number
    payload: WebhookPayload     // Full event payload
    repo: {
      owner: string
      repo: string
    }
  }
  
  // Environment
  env: {
    GITHUB_TOKEN: string
    GITHUB_WORKSPACE: string
    GITHUB_REPOSITORY: string
    GITHUB_RUN_ID: string
    GITHUB_RUN_NUMBER: string
    GITHUB_ACTOR: string
    GITHUB_SHA: string
    GITHUB_REF: string
  }
}

class GitHubActionAdapter implements EntryPointAdapter<GitHubActionInput> {
  readonly name = "github_action"
  readonly triggerSource: TriggerSource = "github_action"
  
  validate(input: GitHubActionInput): ValidationResult {
    const errors: ValidationError[] = []
    
    // Feature request must be determinable
    const featureRequest = this.extractFeatureRequest(input)
    if (!featureRequest) {
      errors.push({
        field: "inputs.feature-request",
        message: "Could not determine feature request from inputs or event context",
        code: "MISSING_FEATURE_REQUEST"
      })
    }
    
    // Validate phases if provided
    if (input.inputs.phases) {
      const phases = input.inputs.phases.split(",")
      const validPhases = ["plan", "build", "validate", "document", "ship"]
      for (const phase of phases) {
        if (!validPhases.includes(phase.trim())) {
          errors.push({
            field: "inputs.phases",
            message: `Invalid phase: ${phase}`,
            code: "INVALID_PHASE"
          })
        }
      }
    }
    
    return { valid: errors.length === 0, errors }
  }
  
  parse(input: GitHubActionInput): RunRequest {
    const featureRequest = this.extractFeatureRequest(input)
    const phases = this.determinePhases(input)
    
    return {
      featureRequest,
      triggerSource: "github_action",
      triggerPayload: {
        inputs: input.inputs,
        context: input.context,
      },
      triggerTimestamp: new Date().toISOString(),
      
      options: {
        phases,
        dryRun: input.inputs["dry-run"] === "true",
        interactive: false,  // Actions are never interactive
      },
      
      metadata: {
        externalId: `action-${input.context.runId}`,
        externalUrl: this.buildActionUrl(input),
        requestedBy: input.context.actor,
        repository: {
          owner: input.context.repo.owner,
          name: input.context.repo.repo,
          defaultBranch: this.getDefaultBranch(input),
          cloneUrl: `https://github.com/${input.context.repo.owner}/${input.context.repo.repo}.git`,
        },
        pullRequest: this.extractPRContext(input),
      }
    }
  }
  
  private extractFeatureRequest(input: GitHubActionInput): string {
    // Explicit input takes precedence
    if (input.inputs["feature-request"]) {
      return input.inputs["feature-request"]
    }
    
    // Extract from event context
    const payload = input.context.payload
    
    switch (input.context.eventName) {
      case "issues":
        return payload.issue?.title || ""
      case "pull_request":
        return `Validate PR: ${payload.pull_request?.title || ""}`
      case "push":
        return `Validate push to ${input.context.ref}`
      case "workflow_dispatch":
        // Manual trigger - check workflow inputs
        return payload.inputs?.["feature-request"] || ""
      default:
        return ""
    }
  }
  
  private determinePhases(input: GitHubActionInput): Phase[] | undefined {
    // Explicit phases input
    if (input.inputs.phases) {
      return input.inputs.phases.split(",").map(p => p.trim() as Phase)
    }
    
    // Infer from event
    switch (input.context.eventName) {
      case "pull_request":
        return ["validate"]
      case "push":
        // Push to main could trigger ship
        if (input.context.ref === "refs/heads/main") {
          return ["validate", "ship"]
        }
        return ["validate"]
      case "issues":
        return undefined  // All phases
      default:
        return undefined
    }
  }
  
  private extractPRContext(input: GitHubActionInput): RunMetadata["pullRequest"] | undefined {
    if (input.context.eventName !== "pull_request") {
      return undefined
    }
    
    const pr = input.context.payload.pull_request
    return {
      number: pr.number,
      baseBranch: pr.base.ref,
      headBranch: pr.head.ref,
      isDraft: pr.draft,
    }
  }
  
  private buildActionUrl(input: GitHubActionInput): string {
    const { owner, repo } = input.context.repo
    return `https://github.com/${owner}/${repo}/actions/runs/${input.context.runId}`
  }
  
  private getDefaultBranch(input: GitHubActionInput): string {
    return input.context.payload.repository?.default_branch || "main"
  }
  
  getCallback(input: GitHubActionInput): CallbackConfig | null {
    return {
      type: "github_action",
      // Actions report status via:
      // 1. Action outputs
      // 2. Commit status API
      // 3. workflow annotations
      actions: {
        onStart: { 
          setOutput: { status: "running" },
          createCommitStatus: "pending"
        },
        onSuccess: { 
          setOutput: { status: "success" },
          createCommitStatus: "success"
        },
        onFailure: { 
          setOutput: { status: "failure" },
          createCommitStatus: "failure",
          annotation: "error"
        }
      }
    }
  }
}
```

### Example Workflow

```yaml
# .github/workflows/agent.yml
name: Agent Pipeline

on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, synchronize, ready_for_review]
  workflow_dispatch:
    inputs:
      feature-request:
        description: 'Feature to implement'
        required: true
      phases:
        description: 'Phases to run'
        required: false

jobs:
  agent:
    runs-on: ubuntu-latest
    # Only run on issues with 'agent' label
    if: |
      github.event_name == 'workflow_dispatch' ||
      github.event_name == 'pull_request' ||
      (github.event_name == 'issues' && contains(github.event.issue.labels.*.name, 'agent'))
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Agent
        id: agent
        uses: your-org/agent-action@v1
        with:
          feature-request: ${{ github.event.inputs.feature-request }}
          phases: ${{ github.event.inputs.phases }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: agent-run-${{ steps.agent.outputs.run-id }}
          path: .agent/runs/${{ steps.agent.outputs.run-id }}/
      
      - name: Comment on Issue/PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const status = '${{ steps.agent.outputs.status }}';
            const runId = '${{ steps.agent.outputs.run-id }}';
            const body = status === 'success'
              ? `✅ Agent run \`${runId}\` completed successfully!`
              : `❌ Agent run \`${runId}\` failed. Check the workflow logs.`;
            
            // Comment on PR or Issue
            const context = github.context;
            if (context.payload.pull_request) {
              github.rest.issues.createComment({
                ...context.repo,
                issue_number: context.payload.pull_request.number,
                body
              });
            } else if (context.payload.issue) {
              github.rest.issues.createComment({
                ...context.repo,
                issue_number: context.payload.issue.number,
                body
              });
            }
```

---

## Adapter Registry

The system uses a registry to route incoming requests to the appropriate adapter.

```typescript
class AdapterRegistry {
  private adapters: Map<string, EntryPointAdapter<unknown>> = new Map()
  
  register<T>(name: string, adapter: EntryPointAdapter<T>): void {
    this.adapters.set(name, adapter)
  }
  
  get(name: string): EntryPointAdapter<unknown> | undefined {
    return this.adapters.get(name)
  }
  
  /**
   * Detect adapter from HTTP request headers/path
   */
  detectFromRequest(req: HTTPRequest): EntryPointAdapter<unknown> | null {
    // Linear webhook
    if (req.headers["linear-signature"]) {
      return this.adapters.get("linear")
    }
    
    // GitHub webhook
    if (req.headers["x-github-event"]) {
      return this.adapters.get("github_webhook")
    }
    
    // Generic webhook (check path)
    if (req.path.startsWith("/webhook/")) {
      const source = req.path.split("/")[2]
      return this.adapters.get(source)
    }
    
    return null
  }
}

// Setup
const registry = new AdapterRegistry()
registry.register("cli", new CLIAdapter())
registry.register("linear", new LinearAdapter(config.linear))
registry.register("github_webhook", new GitHubWebhookAdapter(config.github))
registry.register("github_action", new GitHubActionAdapter())
```

---

## Summary

| Adapter | Input Source | Auth Method | Default Phases | Interactive |
|---------|-------------|-------------|----------------|-------------|
| CLI | Command line args | N/A (local) | All | Yes (if TTY) |
| Linear | HTTP webhook | HMAC signature | All (configurable) | No |
| GitHub Webhook | HTTP webhook | HMAC signature | Event-dependent | No |
| GitHub Action | Action inputs + context | GITHUB_TOKEN | Event-dependent | No |

All adapters produce a normalized `RunRequest` that the Orchestrator Core processes identically, regardless of source.
