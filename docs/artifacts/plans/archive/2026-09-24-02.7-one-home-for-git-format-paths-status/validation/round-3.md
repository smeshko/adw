# Adversarial Validation — Round 3

**Run:** 2026-09-24 07:45 UTC
**Plan:** 02.7-one-home-for-git-format-paths-status
**Status at start:** draft
**Prior rounds in scope:** validation/round-1.md, validation/round-2.md
**Reviewer:** subagent. Codex was still usage-limited, so a clean `general-purpose` subagent ran the round-3 focus text verbatim, against the tree at `7b61e72a`.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

**Verdict: needs-attention (minor).**

The round-2 design holds up:
- Nothing refers to process groups, `killpg`, `start_new_session` or `communicate()` after a kill any more.
- The timeout tiers are consistent everywhere except one stale RESEARCH line.
- There are no dependency cycles.
- I simulated the planned `_run`/`_stop` and the three fake-git scripts in a scratch copy on macOS (bash 3.2 as sh). They behave as the plan claims.

One real problem is new. Round 2 made `branch_exists` return `False` on a timeout, which treats "unknown" as "absent". That opens a path to force-deleting an existing branch.

**Findings**

1. **`branch_exists` returning `False` on `GIT_TIMEOUT` treats "unknown" as "absent" (introduced by round-2 #4).** Severity: med (unlikely, but destructive).
   - **Evidence:** TASK-002:27-28 makes `branch_exists` return `False` on a timeout, and `delete_branch` return `True` "when the branch doesn't exist". Today's code at `worktree/branch.py:117-118` does the same ("Already gone"). Two consequences:
     - A timed-out `git branch --list` makes `delete_branch` return `True`. `adw cleanup` prints "Branch deleted" when nothing was deleted. TASK-003:35's claim that it "never raises a timeout" is true, but the result reports a success that didn't happen.
     - If the pre-check at `manager.py:438` times out, `worktree add -b <existing>` fails. `_cleanup_partial_worktree` (`:473`, `:712`) then runs `branch -D` on the branch that already existed, possibly a user's feature branch.
   - **Verdict: apply.**
   - **Edits:**
     - TASK-002: `branch_exists` lets `GIT_TIMEOUT` propagate; only `FileNotFoundError` still gives `False`, as today. `delete_branch` wraps its whole body in `except ADWError: warn; return False`. Add a test: `delete_branch` returns `False` when `branch --list` raises `GIT_TIMEOUT`.
     - TASK-003 `manager.py:438`: catch `ADWError` and raise `WorktreeError("WORKTREE_CREATE_FAILED", …, recoverable=True) from exc`, with no cleanup, because nothing has been created yet.
     - TASK-003 `manager.py:487`: map the error the same way after cleanup.

2. **The fetch and push timeout mappings drop the credentials hint, so the reasoning behind the round-1 #6 defer fails for exactly the commands that prompt.** Severity: low-med.
   - **Evidence:**
     - PLAN.md:81 defers #6 because "the timeout suggestion names credentials and ssh-agent".
     - TASK-003:15 keeps fetch's existing suggestion, which mentions only the network and the remote (`run_lifecycle.py:595-598`). The push suggestion (`pr.py:234`) doesn't mention credentials either.
     - Git writes prompts to `/dev/tty`, not stderr, so the suggestion is the only hint the user gets.
   - **Verdict: apply.**
   - **Edit:** in TASK-003, the fetch timeout branch uses `suggestion=exc.suggestion`, and `_push_branch` keeps `exc.suggestion` on a timeout. Both new timeout tests assert that "credential" appears in the suggestion.

3. **The round-2 AC2 edit claims more than its tests show.** Severity: low-med.
   - **Evidence:**
     - PLAN.md:243 says "SIGKILL only after the grace period, on a timeout and on an interrupt".
     - The escalation test (TASK-001:49-51) only checks that it finishes in under 3 s. An implementation that sends SIGKILL immediately (the round-1 #4 bug) passes at about 0.3 s.
     - The interrupt test uses the fake that exits on SIGTERM, so it never reaches SIGKILL.
   - **Verdict: apply.**
   - **Edits:**
     - TASK-001: the escalation test also asserts `elapsed >= timeout + KILL_GRACE`. `_stop` must read `KILL_GRACE` at call time, not as a default argument, or the monkeypatch does nothing.
     - TASK-001: run the escalation test with both triggers, a timeout and SIGALRM→KeyboardInterrupt, each against the fake that ignores TERM (`trap '' TERM; exec sleep 30`). In the simulation the interrupt case took about 0.87 s.
     - Make the same change in TASK-009:32.

4. **The SIGALRM test never cancels its timer.** Severity: low, but it can kill the whole pytest run.
   - **Evidence:**
     - TASK-001:54 restores the old handler in `finally` but never calls `setitimer(ITIMER_REAL, 0)`.
     - Reproduced: if `git()` returns before the alarm fires (a fake git that exits at once), the pending SIGALRM hits the restored default action, and the process dies with exit 142.
     - During GREEN a PATH slip would do exactly that, and hide the real assertion.
   - **Verdict: apply.**
   - **Edits:**
     - TASK-001:54: `finally: signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)`.
     - Fire the alarm at 1.0 s, and raise the TERM-trap tests' 0.3/0.5 s timeouts to 1 s. That leaves margin for fork, exec and trap installation under coverage, and the under-5 s and under-3 s bounds still hold.
     - pyproject has no pytest-timeout or xdist, so nothing else in pytest uses SIGALRM.

5. **`_stop` isn't safe against a second interrupt.** Severity: low.
   - **Evidence:**
     - ADW's `_handle_signal` raises KeyboardInterrupt every time (`interruption.py:254-290`), and `init.py:30-40` raises SystemExit.
     - A second signal during `wait(KILL_GRACE)` aborts `_stop` before the SIGKILL.
     - `Popen.__exit__` skips its wait on KeyboardInterrupt, so a git that survived SIGTERM keeps running.
     - Round-2 #1 proposed this escalation explicitly, and its triage dropped it without saying why.
   - **Verdict: apply** (a one-line change).
   - **Edit:** TASK-001:27-29 becomes `try: proc.wait(timeout=KILL_GRACE) except TimeoutExpired: pass finally: if proc.poll() is None: proc.kill(); proc.wait()`.

6. **Housekeeping.** Severity: low. **Verdict: apply.**
   - **a.** TASK-002:86 says `rg 'subprocess\.' src/adw/git.py` shows "only `_run`'s code". That can't hold now that `_stop` is a separate function (its `Popen[str]` parameter and `except subprocess.TimeoutExpired`), and `git()`/`gh()` carry `CompletedProcess[str]` return types. Replace it with: `rg -n 'subprocess\.(run|Popen)\(' src/adw/git.py` prints exactly one line.
   - **b.** RESEARCH.md:133 is stale after round-2 #8. It still gives `worktree add` 300 s and leaves push out of the 600 s tier. Rewrite it to match PLAN.md:128-131.
   - **c.** TASK-009 does cover every PLAN.md criterion. But three goal items have no PLAN criterion and no TASK-009 check. Add these three greps to PLAN.md's criteria and to TASK-009:
     - The single runs-path helper: `rg -n '/ "runs"' src`.
     - The `atomic_write` callers, checked with the `atomic_write\(` call-site grep. The in-place writers, such as `run_directory` and the wizard, never used fsync, `.tmp` or rename, so criterion 6's grep can't see them.
     - The phase lists, checked with the `VALID_STATUSES|AVAILABLE_PHASES|canonical_phases` grep.
   - **d.** Nits:
     - TASK-004:63's `rg -U` output also lists `test_resume_manager.py:284` and `:344`. The acceptance grep catches them anyway.
     - TASK-008's AGENTS.md bullet ("every git/gh call") is only true after TASK-003, so the dependency should be TASK-003, not TASK-001. This is harmless while the tasks run in order.

**Earlier defers and rejects:**
- Round-1 #6 defer: agree, provided finding 2 is applied.
- Round-1 #11 and #12 rejects: agree.
- Round-1 #19 defer: agree.
- Round-2 #9e reject: agree (the behaviour predates this phase).

**Checks with no findings:**
- **(a)** The only mentions of process groups, new sessions or grandchildren are the intended "why not" notes (PLAN.md:138-142, TASK-001:23 and :83-87, RESEARCH.md:135-137).
- **(b)** No caller uses a timed-out command's output. `pr.py` uses fixed messages, and the wizard returns `False`.
- **(c)** Apart from findings 3 and 4, the scripts work unchanged under macOS sh and dash. Nothing can hang, because `_stop` only waits and never reads the pipes.
- **(d)** The tiers are consistent across PLAN.md Decisions and TASK-001, TASK-002 and TASK-003.
- **(e)** "Wrap only the `git()` call" fits the code:
  - The fetch has no existing `try`.
  - `pr.py`'s `try` blocks already wrap only the call.
  - In `manager.py` the new `try` goes inside the existing `FileNotFoundError` one, so the `WorktreeError`s raised in that block keep their codes.
- **(f)** The positive control works:
  - Under the filter, the pydantic warning becomes a `UserWarning` (verified).
  - `test_abort_integration.py` uses a real `ContextManager`, and `save` catches only `OSError`, so the warning isn't swallowed.

No repo files or git state changed. The simulation script is in the scratchpad, at `…/scratchpad/r3/run.py`.

## Triage

<!--
Verdict values:
  apply   — real plan defect; edit PLAN.md / tasks / DECISIONS.md now
  defer   — has merit but out of scope for this plan; capture as a known limitation or follow-up
  reject  — contradicts an explicit Decision in PLAN.md/DECISIONS.md, or is taste/speculation/incorrect
-->

**Round 3 still produced `apply` rows.** The shared protocol says to stop and ask the user at this point. The user asked for a fully autonomous run ("do not stop to ask me questions, use your best judgement"), so this round takes **act-and-stop**:
- Every finding here is a precision fix inside a task, not a structural defect. That is why the plan doesn't go back to `create-plan`.
- The fixes are applied, and no fourth round runs.
- VALIDATION.md records the decision.

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | `branch_exists` → `False` on `GIT_TIMEOUT` reads "unknown" as "absent": `delete_branch` falsely reports success, and a partial-cleanup path can force-delete an existing branch | med | apply | Verified against `manager.py:438`/`:473`. Destructive, so it must not stand. The timeout propagates from `branch_exists`, `delete_branch` catches it, and the pre-check maps it to `WORKTREE_CREATE_FAILED` with no cleanup. | TASK-002, TASK-003 |
| 2 | The fetch/push timeout mappings drop the credentials hint that the #6 defer relies on | low | apply | Keep `exc.suggestion` on the timeout path and assert it | TASK-003 |
| 3 | The AC2 tests don't prove SIGKILL comes *after* the grace period, or that the interrupt path escalates | low | apply | Assert `elapsed >= timeout + KILL_GRACE`, read `KILL_GRACE` at call time, and run escalation for both triggers | TASK-001, TASK-009 |
| 4 | The SIGALRM test never cancels its timer, which can kill pytest (exit 142) | low | apply | Reproduced by the reviewer. `setitimer(0)` in `finally`, with wider timing margins | TASK-001 |
| 5 | A second interrupt during `_stop`'s grace wait skips the SIGKILL | low | apply | One-line `finally` | TASK-001 |
| 6a | TASK-002's `subprocess` grep can't hold with `_stop` split out | low | apply | Use `rg -n 'subprocess\.(run|Popen)\(' src/adw/git.py` (exactly one line) | TASK-002 |
| 6b | RESEARCH.md still gives `worktree add` the old tier and leaves push out | low | apply | Stale after round-2 #8 | RESEARCH.md |
| 6c | No PLAN criterion or TASK-009 check covers the runs path, the `atomic_write` callers or the phase lists | low | apply | Add the three greps | PLAN.md:Acceptance, TASK-009 |
| 6d | Nits: TASK-004's `rg -U` also lists `test_resume_manager.py:284`/`:344`; TASK-008's AGENTS.md bullet needs TASK-003, not TASK-001 | low | apply | Trivial | TASK-004, TASK-008, PLAN.md:Tasks |
