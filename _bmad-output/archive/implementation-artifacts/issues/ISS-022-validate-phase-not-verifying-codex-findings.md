# Issue: Validate Phase Does Not Verify Codex Review Findings

**ID:** ISS-022
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-09
**Reporter:** Ivo

## Related

- **Epic:** 16
- **Story:** N/A
- **Component:** Validate Phase / code-review-loop workflow

## Description

During the validate phase, Claude runs the `codex-review` skill to get an adversarial code review. However, Claude does NOT verify whether Codex's findings are accurate before accepting them.

In a test run, Codex was given correct code (`"Hello, {name}!"`) but hallucinated that it contained invalid escape sequences (`"Hello, {name}\!"`). Claude accepted these false findings without:
1. Reading the actual files to compare against Codex's claims
2. Checking if the code snippets Codex cited match reality
3. Dismissing the issues as false positives
4. Attempting any fixes (because there was nothing to fix)

The workflow instructions say "validate findings, fix genuine issues" but Claude skipped the validation step entirely.

## Reproduction Steps

1. Run `adw run "Create hello world cli command"` on a test project
2. Let the run complete through validate phase
3. Examine `.adw/runs/{run_id}/llm/003_validate_response.json`
4. Observe that Codex found issues with escape sequences that don't exist in the code
5. Verify the actual files have correct code (no `\!` escapes)
6. Note that Claude's response ends immediately after displaying Codex output - no verification

## Expected Behavior

After receiving Codex review findings, Claude should:
1. Read each file mentioned in the findings
2. Compare the actual code against Codex's claimed code snippets
3. Verify whether each issue actually exists
4. Dismiss false positives with explanation
5. Only attempt to fix genuine issues
6. Output a validation summary showing which issues were real vs hallucinated

## Actual Behavior

Claude displays Codex's JSON output and stops. No verification occurs. Hallucinated issues are treated as real.

## Impact

- False positive issues are accepted as real problems
- No fixes are made (because there's nothing to fix), but the run appears to have found issues
- Users cannot trust the validate phase results
- The entire validation loop is compromised by not catching LLM hallucinations

## User Impact Score

- **Users Affected:** All users
- **Frequency:** Every run where Codex hallucinates (unknown frequency)

## Workaround

Manually review the validate phase output and compare against actual files.

## Environment

- **OS:** macOS/Linux
- **App Version:** 0.1.6
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

From `003_validate_response.json`:
```json
{
  "content": "...Codex review completed. Here's the JSON output:\n\n```json\n{\"issues\":[{\"id\":\"review-001\",\"severity\":\"warning\",\"description\":\"The `hello` command builds its greeting with `f\\\"Hello, {name}\\\\!\\\"`, which contains the invalid escape sequence..."
}
```

The response ends there - no verification of whether `\!` actually exists in the code.

### Screen Recording

N/A

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Root Cause Analysis

The `code-review-loop` workflow template instructs Claude to "validate findings, fix genuine issues" but:
1. The template doesn't provide explicit steps for how to validate
2. There's no mandate to read files after receiving Codex output
3. Claude interprets "validate" as just displaying the results, not verifying accuracy

## Suggested Fix

Update the validate phase prompt/workflow to include explicit instructions:
1. After receiving Codex findings, READ each file mentioned
2. Compare actual code against Codex's code_snippet claims
3. Mark each finding as VERIFIED or DISMISSED with reasoning
4. Only proceed to fix VERIFIED issues
5. Output validation summary before any fixes

## Notes

This is a fundamental issue with using one LLM (Codex) to review code and another (Claude) to act on findings without verification. The validate phase must include a "trust but verify" step.
