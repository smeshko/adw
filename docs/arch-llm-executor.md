# LLM Executor - Deep Dive

## Overview

The LLM Executor is the abstraction layer that interfaces with AI coding tools. It provides a unified interface for the Phase Runner to invoke LLMs, abstracting away the underlying tool implementation.

**Design Principles:**

- **Tool Agnostic** — Same interface regardless of underlying executor
- **Capability Detection** — Executors declare what they support; system adapts accordingly
- **Streaming First** — Real-time output for responsive UX and logging
- **Graceful Degradation** — Falls back when features aren't supported
- **Testable** — Mock executors for testing without API calls

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM EXECUTOR LAYER                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Executor Interface                                ││
│  │   execute(request) → Promise<ExecutionResult>                           ││
│  │   supportsStreaming() / supportsTools() / supportsStructuredOutput()    ││
│  └────────────────────────────────┬────────────────────────────────────────┘│
│                                   │                                         │
│                                   ▼                                         │
│                        ┌─────────────────┐                                  │
│                        │  Claude Code    │                                  │
│                        │    Executor     │                                  │
│                        │                 │                                  │
│                        │ • Full agentic  │                                  │
│                        │ • Tool use      │                                  │
│                        │ • Streaming     │                                  │
│                        └────────┬────────┘                                  │
│                                 │                                           │
│                                 ▼                                           │
│                          claude CLI                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Custom executors can be added by implementing the LLMExecutor interface ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Interfaces

### Executor Interface

```typescript
interface LLMExecutor {
  /** Unique identifier for this executor */
  readonly name: string
  
  /** Human-readable description */
  readonly description: string
  
  /**
   * Execute a prompt and return results.
   * This is the main entry point for all LLM operations.
   */
  execute(request: ExecutionRequest): Promise<ExecutionResult>
  
  /**
   * Validate that the executor is properly configured and available.
   * Called at startup and before first use.
   */
  validate(): Promise<ValidationResult>
  
  // Capability detection
  supportsStreaming(): boolean
  supportsStructuredOutput(): boolean
  supportsTools(): boolean
  supportsImages(): boolean
  supportsResume(): boolean  // Can continue from partial output
  
  /**
   * Estimate token count for a prompt.
   * Used for logging and rate limit management.
   */
  estimateTokens(prompt: string): number
  
  /**
   * Abort a running execution.
   * Returns true if abort was successful.
   */
  abort(executionId: string): Promise<boolean>
}
```

### Execution Request

```typescript
interface ExecutionRequest {
  /** Unique ID for this execution (for logging, abort, resume) */
  id: string
  
  /** The rendered prompt to send */
  prompt: string
  
  /** Working directory for file operations */
  workingDirectory: string
  
  /** LLM configuration */
  config: LLMConfig
  
  /** Optional: Expected output schema for structured output */
  outputSchema?: JSONSchema
  
  /** Optional: System prompt (if executor supports it) */
  systemPrompt?: string
  
  /** Optional: Tool definitions (if executor supports tools) */
  tools?: ToolDefinition[]
  
  /** Optional: Images to include (if executor supports vision) */
  images?: ImageInput[]
  
  /** Optional: Previous conversation for context */
  conversationHistory?: ConversationMessage[]
  
  /** Callbacks for streaming events */
  callbacks?: ExecutionCallbacks
  
  /** Environment variables to set for CLI executors */
  env?: Record<string, string>
  
  /** Files to make available (copied to working dir if needed) */
  inputFiles?: FileInput[]
}

interface LLMConfig {
  /** Model identifier (executor-specific) */
  model?: string
  
  /** Temperature (0 = deterministic) */
  temperature: number
  
  /** Maximum output tokens */
  maxTokens: number
  
  /** Timeout in seconds */
  timeoutSeconds: number
  
  /** Number of retries on transient failures */
  maxRetries: number
  
  /** Stop sequences */
  stopSequences?: string[]
  
  /** Top-p sampling */
  topP?: number
  
  /** Seed for reproducibility (if supported) */
  seed?: number
}

interface ExecutionCallbacks {
  /** Called for each token (if streaming) */
  onToken?: (token: string) => void
  
  /** Called when a tool is invoked */
  onToolCall?: (call: ToolCall) => void
  
  /** Called when a tool returns */
  onToolResult?: (result: ToolResult) => void
  
  /** Called for thinking/reasoning content (if exposed) */
  onThinking?: (content: string) => void
  
  /** Called periodically with progress info */
  onProgress?: (progress: ExecutionProgress) => void
  
  /** Called on recoverable errors (before retry) */
  onRetry?: (error: Error, attempt: number) => void
}
```

### Execution Result

```typescript
interface ExecutionResult {
  /** Whether execution completed successfully */
  success: boolean
  
  /** The raw output from the LLM */
  output: string
  
  /** Parsed structured output (if schema was provided and parsing succeeded) */
  structuredOutput?: unknown
  
  /** Token usage statistics */
  usage: TokenUsage
  
  /** Total execution duration in milliseconds */
  durationMs: number
  
  /** Files that were created during execution */
  filesCreated: FileChange[]
  
  /** Files that were modified during execution */
  filesModified: FileChange[]
  
  /** Files that were deleted during execution */
  filesDeleted: string[]
  
  /** Tool calls made during execution */
  toolCalls: ToolCallRecord[]
  
  /** Error information (if success is false) */
  error?: ExecutionError
  
  /** Executor-specific metadata */
  metadata?: Record<string, unknown>
  
  /** Can this execution be resumed? */
  resumable: boolean
  
  /** Resume token (if resumable) */
  resumeToken?: string
}

interface TokenUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  
  /** Cost estimate in USD (if available) */
  estimatedCost?: number
}

interface FileChange {
  path: string           // Relative to working directory
  absolutePath: string   // Full path
  changeType: "created" | "modified" | "deleted"
  
  /** Lines added/removed (if available) */
  diff?: {
    additions: number
    deletions: number
  }
}

interface ExecutionError {
  type: ExecutionErrorType
  message: string
  code?: string
  
  /** Original error from underlying tool */
  cause?: Error
  
  /** Is this error potentially recoverable with retry? */
  recoverable: boolean
  
  /** Suggested action */
  suggestion?: string
}

type ExecutionErrorType =
  | "timeout"           // Execution exceeded timeout
  | "rate_limit"        // API rate limit hit
  | "auth"              // Authentication failure
  | "invalid_request"   // Bad request (prompt too long, etc.)
  | "model_error"       // Model returned error
  | "tool_error"        // A tool call failed
  | "parse_error"       // Failed to parse structured output
  | "abort"             // Execution was aborted
  | "network"           // Network connectivity issue
  | "unknown"           // Unknown error
```

---

## Claude Code Executor

The primary executor for agentic coding tasks. Wraps the `claude` CLI tool.

```typescript
class ClaudeCodeExecutor implements LLMExecutor {
  readonly name = "claude-code"
  readonly description = "Anthropic's Claude Code CLI for agentic coding"
  
  constructor(private config: ClaudeCodeConfig) {}
  
  // Full capability support
  supportsStreaming(): boolean { return true }
  supportsStructuredOutput(): boolean { return true }
  supportsTools(): boolean { return true }
  supportsImages(): boolean { return true }
  supportsResume(): boolean { return true }
  
  async validate(): Promise<ValidationResult> {
    // Check claude CLI is installed and authenticated
    const result = await this.runCommand(["--version"])
    if (!result.success) {
      return {
        valid: false,
        errors: [{
          code: "CLI_NOT_FOUND",
          message: "claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        }]
      }
    }
    
    // Check authentication
    const authCheck = await this.runCommand(["auth", "status"])
    if (!authCheck.success) {
      return {
        valid: false,
        errors: [{
          code: "NOT_AUTHENTICATED",
          message: "Claude Code not authenticated. Run: claude auth login"
        }]
      }
    }
    
    return { valid: true }
  }
  
  async execute(request: ExecutionRequest): Promise<ExecutionResult> {
    const args = this.buildArgs(request)
    const env = this.buildEnv(request)
    
    const startTime = Date.now()
    const toolCalls: ToolCallRecord[] = []
    const filesCreated: FileChange[] = []
    const filesModified: FileChange[] = []
    
    // Create a temporary file for the prompt if it's large
    const promptFile = await this.writePromptFile(request)
    
    try {
      const process = spawn("claude", args, {
        cwd: request.workingDirectory,
        env: { ...process.env, ...env },
      })
      
      let output = ""
      let currentToolCall: ToolCall | null = null
      
      // Stream handling
      const parser = new ClaudeOutputParser()
      
      process.stdout.on("data", (chunk) => {
        const text = chunk.toString()
        const events = parser.parse(text)
        
        for (const event of events) {
          switch (event.type) {
            case "text":
              output += event.content
              request.callbacks?.onToken?.(event.content)
              break
              
            case "tool_call_start":
              currentToolCall = event.toolCall
              request.callbacks?.onToolCall?.(event.toolCall)
              break
              
            case "tool_call_end":
              toolCalls.push({
                ...currentToolCall!,
                result: event.result,
                durationMs: event.durationMs
              })
              request.callbacks?.onToolResult?.(event.result)
              currentToolCall = null
              break
              
            case "file_created":
              filesCreated.push(event.file)
              break
              
            case "file_modified":
              filesModified.push(event.file)
              break
              
            case "thinking":
              request.callbacks?.onThinking?.(event.content)
              break
          }
        }
      })
      
      // Wait for completion with timeout
      const exitCode = await this.waitWithTimeout(
        process,
        request.config.timeoutSeconds * 1000
      )
      
      const durationMs = Date.now() - startTime
      
      if (exitCode !== 0) {
        return this.buildErrorResult(exitCode, output, durationMs)
      }
      
      // Parse structured output if schema provided
      let structuredOutput: unknown | undefined
      if (request.outputSchema) {
        try {
          structuredOutput = this.parseStructuredOutput(output, request.outputSchema)
        } catch (e) {
          return {
            success: false,
            output,
            usage: this.extractUsage(output),
            durationMs,
            filesCreated,
            filesModified,
            filesDeleted: [],
            toolCalls,
            error: {
              type: "parse_error",
              message: `Failed to parse output as JSON: ${e.message}`,
              recoverable: false
            },
            resumable: false
          }
        }
      }
      
      return {
        success: true,
        output,
        structuredOutput,
        usage: this.extractUsage(output),
        durationMs,
        filesCreated,
        filesModified,
        filesDeleted: this.detectDeletedFiles(toolCalls),
        toolCalls,
        resumable: true,
        metadata: {
          executor: "claude-code",
          model: request.config.model || "default"
        }
      }
      
    } finally {
      // Cleanup prompt file
      await this.cleanupPromptFile(promptFile)
    }
  }
  
  private buildArgs(request: ExecutionRequest): string[] {
    const args: string[] = [
      "--print",              // Output to stdout
      "--output-format", "stream-json",  // Structured streaming
    ]
    
    // Model selection
    if (request.config.model) {
      args.push("--model", request.config.model)
    }
    
    // Temperature
    if (request.config.temperature !== undefined) {
      args.push("--temperature", String(request.config.temperature))
    }
    
    // Max tokens
    if (request.config.maxTokens) {
      args.push("--max-tokens", String(request.config.maxTokens))
    }
    
    // System prompt
    if (request.systemPrompt) {
      args.push("--system-prompt", request.systemPrompt)
    }
    
    // Allowed tools (if restricted)
    if (request.tools) {
      const toolNames = request.tools.map(t => t.name).join(",")
      args.push("--allowed-tools", toolNames)
    }
    
    // The prompt itself
    args.push("--prompt", request.prompt)
    
    return args
  }
  
  async abort(executionId: string): Promise<boolean> {
    // Claude Code supports graceful abort via signal
    const process = this.activeProcesses.get(executionId)
    if (process) {
      process.kill("SIGTERM")
      return true
    }
    return false
  }
}

interface ClaudeCodeConfig {
  /** Path to claude CLI (default: finds in PATH) */
  cliPath?: string
  
  /** Default model to use */
  defaultModel?: string
  
  /** Additional CLI flags to always include */
  additionalFlags?: string[]
  
  /** Working directory mode */
  workingDirectoryMode: "inherit" | "temp" | "specified"
}
```

---

## Executor Selection & Registry

```typescript
class ExecutorRegistry {
  private executors: Map<string, LLMExecutor> = new Map()
  private defaultExecutor: string = "claude-code"
  
  /**
   * Register an executor.
   */
  register(executor: LLMExecutor): void {
    this.executors.set(executor.name, executor)
  }
  
  /**
   * Get executor by name, or default if not specified.
   */
  get(name?: string): LLMExecutor {
    const executorName = name || this.defaultExecutor
    const executor = this.executors.get(executorName)
    
    if (!executor) {
      throw new Error(
        `Unknown executor: ${executorName}. ` +
        `Available: ${Array.from(this.executors.keys()).join(", ")}`
      )
    }
    
    return executor
  }
  
  /**
   * Validate all registered executors.
   */
  async validateAll(): Promise<Map<string, ValidationResult>> {
    const results = new Map<string, ValidationResult>()
    
    for (const [name, executor] of this.executors) {
      results.set(name, await executor.validate())
    }
    
    return results
  }
  
  /**
   * Get executor that supports specific capabilities.
   */
  findWithCapabilities(requirements: {
    streaming?: boolean
    structuredOutput?: boolean
    tools?: boolean
    images?: boolean
  }): LLMExecutor | null {
    for (const executor of this.executors.values()) {
      let matches = true
      
      if (requirements.streaming && !executor.supportsStreaming()) {
        matches = false
      }
      if (requirements.structuredOutput && !executor.supportsStructuredOutput()) {
        matches = false
      }
      if (requirements.tools && !executor.supportsTools()) {
        matches = false
      }
      if (requirements.images && !executor.supportsImages()) {
        matches = false
      }
      
      if (matches) return executor
    }
    
    return null
  }
  
  /**
   * List all available executors with their capabilities.
   */
  list(): ExecutorInfo[] {
    return Array.from(this.executors.values()).map(e => ({
      name: e.name,
      description: e.description,
      capabilities: {
        streaming: e.supportsStreaming(),
        structuredOutput: e.supportsStructuredOutput(),
        tools: e.supportsTools(),
        images: e.supportsImages(),
        resume: e.supportsResume()
      }
    }))
  }
}

interface ExecutorInfo {
  name: string
  description: string
  capabilities: {
    streaming: boolean
    structuredOutput: boolean
    tools: boolean
    images: boolean
    resume: boolean
  }
}
```

---

## Retry & Error Handling

```typescript
class ExecutionManager {
  constructor(
    private registry: ExecutorRegistry,
    private logger: Logger
  ) {}
  
  /**
   * Execute with retry logic and error handling.
   */
  async execute(
    executorName: string,
    request: ExecutionRequest
  ): Promise<ExecutionResult> {
    const executor = this.registry.get(executorName)
    const maxRetries = request.config.maxRetries
    
    let lastError: ExecutionError | undefined
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      if (attempt > 0) {
        this.logger.info(`Retry attempt ${attempt}/${maxRetries}`, {
          executionId: request.id,
          lastError: lastError?.message
        })
        
        request.callbacks?.onRetry?.(
          new Error(lastError?.message || "Unknown error"),
          attempt
        )
        
        // Exponential backoff
        await this.delay(Math.pow(2, attempt) * 1000)
      }
      
      try {
        const result = await executor.execute(request)
        
        if (result.success) {
          return result
        }
        
        // Check if error is recoverable
        if (result.error && !result.error.recoverable) {
          return result  // Don't retry non-recoverable errors
        }
        
        lastError = result.error
        
      } catch (e) {
        // Unexpected error - wrap it
        lastError = {
          type: "unknown",
          message: e.message,
          cause: e,
          recoverable: this.isRecoverableError(e)
        }
        
        if (!lastError.recoverable) {
          return {
            success: false,
            output: "",
            usage: { inputTokens: 0, outputTokens: 0, totalTokens: 0 },
            durationMs: 0,
            filesCreated: [],
            filesModified: [],
            filesDeleted: [],
            toolCalls: [],
            error: lastError,
            resumable: false
          }
        }
      }
    }
    
    // All retries exhausted
    return {
      success: false,
      output: "",
      usage: { inputTokens: 0, outputTokens: 0, totalTokens: 0 },
      durationMs: 0,
      filesCreated: [],
      filesModified: [],
      filesDeleted: [],
      toolCalls: [],
      error: {
        type: lastError?.type || "unknown",
        message: `Failed after ${maxRetries + 1} attempts: ${lastError?.message}`,
        recoverable: false
      },
      resumable: false
    }
  }
  
  private isRecoverableError(error: Error): boolean {
    const message = error.message.toLowerCase()
    
    // Rate limits are recoverable
    if (message.includes("rate_limit") || message.includes("429")) {
      return true
    }
    
    // Timeouts are recoverable
    if (message.includes("timeout") || message.includes("timed out")) {
      return true
    }
    
    // Network errors are recoverable
    if (message.includes("econnreset") || message.includes("enotfound")) {
      return true
    }
    
    // Server errors (5xx) are recoverable
    if (message.includes("500") || message.includes("502") || 
        message.includes("503") || message.includes("504")) {
      return true
    }
    
    return false
  }
  
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}
```

---

## Custom Executor Support

Users can create custom executors by implementing the interface:

```typescript
// Example: Custom executor that wraps a local model

class OllamaExecutor implements LLMExecutor {
  readonly name = "ollama"
  readonly description = "Local Ollama models"
  
  constructor(private config: {
    model: string
    baseUrl: string
  }) {}
  
  supportsStreaming(): boolean { return true }
  supportsStructuredOutput(): boolean { return true }
  supportsTools(): boolean { return false }  // Ollama tool support varies
  supportsImages(): boolean { return true }   // Some models support it
  supportsResume(): boolean { return false }
  
  async validate(): Promise<ValidationResult> {
    try {
      const response = await fetch(`${this.config.baseUrl}/api/tags`)
      const data = await response.json()
      
      const hasModel = data.models?.some(
        (m: any) => m.name === this.config.model
      )
      
      if (!hasModel) {
        return {
          valid: false,
          errors: [{
            code: "MODEL_NOT_FOUND",
            message: `Model ${this.config.model} not found. Run: ollama pull ${this.config.model}`
          }]
        }
      }
      
      return { valid: true }
    } catch (e) {
      return {
        valid: false,
        errors: [{
          code: "CONNECTION_FAILED",
          message: `Cannot connect to Ollama at ${this.config.baseUrl}`
        }]
      }
    }
  }
  
  async execute(request: ExecutionRequest): Promise<ExecutionResult> {
    const startTime = Date.now()
    
    const response = await fetch(`${this.config.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: this.config.model,
        prompt: request.prompt,
        stream: !!request.callbacks?.onToken,
        options: {
          temperature: request.config.temperature,
          num_predict: request.config.maxTokens
        }
      })
    })
    
    let output = ""
    
    if (request.callbacks?.onToken) {
      // Handle streaming response
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split("\n").filter(Boolean)
        
        for (const line of lines) {
          const data = JSON.parse(line)
          if (data.response) {
            output += data.response
            request.callbacks.onToken(data.response)
          }
        }
      }
    } else {
      const data = await response.json()
      output = data.response
    }
    
    return {
      success: true,
      output,
      usage: {
        inputTokens: this.estimateTokens(request.prompt),
        outputTokens: this.estimateTokens(output),
        totalTokens: this.estimateTokens(request.prompt) + this.estimateTokens(output)
      },
      durationMs: Date.now() - startTime,
      filesCreated: [],
      filesModified: [],
      filesDeleted: [],
      toolCalls: [],
      resumable: false,
      metadata: {
        executor: "ollama",
        model: this.config.model
      }
    }
  }
  
  estimateTokens(text: string): number {
    // Rough estimate: ~4 chars per token
    return Math.ceil(text.length / 4)
  }
  
  async abort(): Promise<boolean> {
    // Ollama doesn't support abort
    return false
  }
}
```

---

## Configuration

```yaml
# .agent/project.yaml

# Executor selection
llm_executor: claude-code  # Default executor for all phases

# Per-phase executor override
phases:
  plan:
    executor: claude-code
    config:
      model: claude-sonnet-4-20250514
      temperature: 0.2  # Slightly creative for planning
      
  build:
    executor: claude-code
    config:
      model: claude-sonnet-4-20250514
      temperature: 0    # Deterministic for code
      max_tokens: 32000
      
  validate:
    executor: claude-code
    config:
      model: claude-sonnet-4-20250514
      temperature: 0

# Executor-specific configuration
executors:
  claude-code:
    additional_flags:
      - "--no-auto-compact"
```

---

## Integration with Phase Runner

```typescript
class PhaseRunner {
  constructor(
    private executorRegistry: ExecutorRegistry,
    private executionManager: ExecutionManager,
    private logger: Logger
  ) {}
  
  async runLLMStep(
    phase: string,
    command: ResolvedCommand,
    context: RunContext,
    renderedPrompt: string
  ): Promise<PhaseResult> {
    // Get executor for this phase
    const executorName = command.config.executor || 
                         context.project.llm_executor ||
                         "claude-code"
    
    const executor = this.executorRegistry.get(executorName)
    
    // Validate executor supports requirements
    if (command.outputSchema && !executor.supportsStructuredOutput()) {
      this.logger.warn(
        `Executor ${executorName} doesn't support structured output, ` +
        `but phase ${phase} has schema. Output validation will be skipped.`
      )
    }
    
    // Build execution request
    const request: ExecutionRequest = {
      id: `${context.run.id}-${phase}-llm`,
      prompt: renderedPrompt,
      workingDirectory: context.project.repo_root,
      config: {
        model: command.config.llm?.model,
        temperature: command.config.llm?.temperature ?? 0,
        maxTokens: command.config.llm?.max_tokens ?? 16000,
        timeoutSeconds: command.config.timeout_seconds ?? 300,
        maxRetries: command.config.max_retries ?? 2,
      },
      outputSchema: command.outputSchema,
      systemPrompt: this.buildSystemPrompt(phase, context),
      callbacks: {
        onToken: (token) => this.streamLogger.token(token),
        onToolCall: (call) => {
          this.streamLogger.toolCall(call)
          this.logger.debug("Tool call", { call })
        },
        onToolResult: (result) => {
          this.streamLogger.toolResult(result)
          this.logger.debug("Tool result", { result })
        },
        onRetry: (error, attempt) => {
          this.logger.warn(`LLM retry ${attempt}`, { error: error.message })
        }
      },
      env: this.buildEnv(context)
    }
    
    // Execute with retry handling
    const result = await this.executionManager.execute(executorName, request)
    
    // Log execution stats
    this.logger.info("LLM execution complete", {
      phase,
      executor: executorName,
      success: result.success,
      tokens: result.usage,
      duration: result.durationMs,
      filesModified: result.filesModified.length,
      toolCalls: result.toolCalls.length
    })
    
    return this.buildPhaseResult(phase, result)
  }
}
```

---

## Summary

| Executor | Best For | Capabilities | Trade-offs |
|----------|----------|--------------|------------|
| Claude Code | Full agentic coding | All | Requires CLI install |
| Custom | Specific needs | Varies | Must implement interface |

The LLM Executor layer ensures the orchestrator can work with any underlying AI tool while maintaining a consistent interface for logging, error handling, and capability detection.