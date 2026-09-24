# Adversarial Validation — Round 2

**Run:** 2026-09-24 07:00 UTC
**Plan:** 02.7-one-home-for-git-format-paths-status
**Status at start:** draft
**Prior rounds in scope:** validation/round-1.md
**Reviewer:** subagent. Codex was still usage-limited ("try again at 11:57 AM"), so a clean `general-purpose` subagent ran the round-2 focus text verbatim, against the tree at `7b61e72a`.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

**Verdict: needs-attention.** Most round-1 edits landed and hold against the code at `7b61e72a`. Every line reference I spot-checked is current. Both TASK-004 status greps can be satisfied: after the listed edits, the only hits left are `progress.py:309-313`, which TASK-006 removes.

The main problem is new. The round-1 fix for #4, a new session plus a group kill, introduces two regressions the plan doesn't record:
- Ctrl+C now always leaves git's lockfiles behind.
- Git loses its terminal, which also voids the defer rationale for #6.

There are also two implementation traps (in TASK-003 and TASK-001) and some stale or incomplete instructions.

**Round-1 defer and reject verdicts:**
- **#6 defer (`GIT_TERMINAL_PROMPT=0`): disagree.** `start_new_session` already removes the terminal, so the stated rationale is gone (finding 2).
- **#11 reject: agree.** mypy strict doesn't flag string-vs-member comparisons, and one grep is the checkable rule. I confirmed it's satisfiable.
- **#12 reject: agree,** given the user's single-PR request. The 8 task commits keep the change reviewable piece by piece.
- **#19 defer: agree.** Both issues predate this phase, and `atomic_write` doesn't make lost updates materially worse.

## Findings

**1. Ctrl+C now always leaves git's lockfiles behind, a regression from the #4 edit.** Severity: high.
- **Evidence:**
  - TASK-001:22 starts git with `start_new_session=True`, so the terminal's SIGINT reaches only ADW.
  - ADW's handlers (`interruption.py:255-285`, `init.py:30-40`) turn that SIGINT into KeyboardInterrupt/SystemExit inside `communicate()`, which then waits 0.25 s for a child that never got the signal.
  - TASK-001:71 then sends SIGKILL to the group, so git never gets to clean up its locks.
  - Today git sits in the terminal's foreground group. It receives SIGINT itself and removes `index.lock` before `subprocess.run` kills it.
- **Worst case:** Ctrl+C during a slow pre-commit hook in `_auto_commit`, or during ship's `checkout`/`pull` (`ship.py:192,198`). The index lock held during the hook is left in the user's main checkout. After `adw resume`, every `git add -A` fails, and `phase_runner.py:1217` swallows the failure.
- **Don't copy `hooks/runner.py:205-209`.** It handles only `TimeoutError`, so on Ctrl+C its hook grandchildren are orphaned. That is pre-existing and worth a follow-up ticket.
- **Verdict: apply.**
- **Edit** (TASK-001 Files/Notes, PLAN.md Decisions:135):
  - Add one helper, `_stop_group(proc, first_signal)`. On timeout it sends SIGTERM. On any other BaseException it forwards SIGINT to the group.
  - Then call `proc.wait(timeout=KILL_GRACE)`. A second interrupt, or the grace running out, escalates to SIGKILL.
  - Always finish with a SIGKILL to the group (ignoring `ProcessLookupError`) to catch stragglers, then re-raise.
  - Add `test_interrupt_forwards_sigint_to_the_group`:
    - The fake git traps INT: `trap 'echo cleaned > "$MARK"; exit 130' INT; while :; do sleep 1; done`. A backgrounded `sleep 30 &` won't work here, because a background job in non-interactive sh ignores SIGINT.
    - Raise KeyboardInterrupt from a SIGALRM handler scheduled with `signal.setitimer(ITIMER_REAL, 0.3)`.
    - Assert the KeyboardInterrupt propagates and the marker exists.
  - Add the test to PLAN AC2 and the TASK-009 matrix.

**2. `start_new_session` takes away git's controlling terminal, which voids the #6 defer.** Severity: med.
- **Evidence:**
  - After `setsid`, opening `/dev/tty` fails, and git's credential prompt uses `/dev/tty` with no stdin fallback. It now fails with `could not read Username … Device not configured`.
  - ssh's passphrase and host-key prompts also read `/dev/tty`, so they fail unless an askpass helper is set.
  - Hooks that `exec < /dev/tty` break the same way.
- **What the plan says instead:**
  - PLAN.md:81 still defers #6 because "a user at a terminal can answer a prompt".
  - TASK-001:32's suggestion says a prompt "can stall git". A prompt now fails at once, as a plain `GIT_FETCH_FAILED`/`GIT_PUSH_FAILED`.
  - The Risks visible-changes list (PLAN.md:207-218) doesn't mention it.
- Dashboard-triggered runs already have no terminal (`run_trigger.py:100`).
- **Verdict: apply** (re-triage #6).
- **Edit:** PLAN Decisions should say that git runs without a controlling terminal, so terminal prompts fail immediately instead of blocking. Then:
  - Either set `GIT_TERMINAL_PROMPT=0` in `_run`'s env for a clear message, or record the decision not to.
  - Replace PLAN.md:81's out-of-scope bullet.
  - Add a Risks entry for the visible change: a fetch or push that used to prompt for credentials, an ssh passphrase or a host key now fails.
  - Drop "prompt can stall" from TASK-001:32.
- **Alternative:** if prompts must keep working, drop the new session and SIGTERM only git's pid, giving up the hook-grandchild cleanup. Pick one explicitly.

**3. The post-SIGKILL `communicate()` can block forever, and two stale statements remain.** Severity: med.
- **Evidence:**
  - TASK-001:28 calls `communicate()` without a timeout after SIGKILL, and that reads the pipes to EOF.
  - A descendant that left the group (a daemonizing hook, `setsid foo &`) keeps the inherited pipe open, so this path, the one that is meant to be bounded, blocks forever.
  - `hooks/runner.py:206-209` already avoids this by calling `wait()`, with the comment "children holding the pipes would block wait()".
- **Stale statements:**
  - PLAN.md:222 still argues "subprocess.run only waits for the killed child".
  - RESEARCH.md:95 says a global `patch("subprocess.run")` intercepts `adw.git` calls. That is false under Popen, and it contradicts PLAN.md:136.
- **Verdict: apply.**
- **Edit:**
  - TASK-001: keep `communicate(timeout=KILL_GRACE)` for the grace period, then `proc.wait()` after SIGKILL, without reading the pipes.
  - Rewrite PLAN.md:222 and RESEARCH.md:95.

**4. Catching `ADWError` around the existing `try` blocks in manager.py would swallow the `WorktreeError`s raised inside them.** Severity: med.
- **Evidence:**
  - `WorktreeError` is an `ADWError` (`exceptions.py:133`).
  - `create_worktree`'s single `try` (manager.py:464-505) raises `WORKTREE_CREATE_FAILED` (:477) and `BRANCH_NOT_CREATED`, `recoverable=False` (:488).
  - `remove_worktree`'s `try` (:602-650) raises `WORKTREE_REMOVE_FAILED` (:612) and also runs the branch delete.
- **Consequences of TASK-003:31/34 as written:**
  - `BRANCH_NOT_CREATED` turns into `WORKTREE_CREATE_FAILED`, and cleanup runs twice.
  - A `GIT_TIMEOUT` from `git branch -D`, raised after the worktree is already gone, turns into `WORKTREE_REMOVE_FAILED`. `adw cleanup` then reports failure for a worktree it removed.
  - The same risk applies at TASK-003:14 in `run_lifecycle.py`, if the new `try` encloses the non-zero `raise`.
- **Verdict: apply.**
- **Edit:**
  - TASK-003: wrap only the `git(...)` call (`try: result = git(...) except ADWError as exc: …`), or put `except WorktreeError: raise` first. Add a test that `BRANCH_NOT_CREATED` keeps its code.
  - TASK-002: `branch_exists` and `delete_branch` treat `GIT_TIMEOUT` as a failure (return `False` and log a warning), as `pr_exists` already does for `GH_TIMEOUT`.

**5. TASK-004's positive control can't run as written, and the test-side string-write list is incomplete.** Severity: med.
- **Why the positive control can't run:**
  - `interruption.py` has no FAILED write. It writes aborted at :165 and interrupted at :211 and :273.
  - The saves after :211 and :273 sit inside `except Exception: pass` (:225, :287), so any warning there is swallowed.
  - `tests/unit/core/test_interruption.py` mocks the ContextManager, so nothing is serialized.
- **What the list misses:** four multi-line `model_copy(update={"status": "…"})` sites, each followed by a real save that will warn. They would fail the `-W` run and put warnings in TASK-009's summary line.
  - `tests/integration/core/test_interruption_integration.py:112`, `:171` and `:352`
  - `tests/integration/core/test_orchestrator_integration.py:356`

  `test_context.py:382` and `test_index.py:264` never serialize, so they're harmless.
- **Verdict: apply.**
- **Edit** (TASK-004):
  - For the positive control, revert `interruption.py:165` to `"aborted"` and show `tests/integration/cli/test_abort_integration.py` failing, or use a throwaway `model_copy(...).model_dump_json()` test.
  - List the four integration sites, and add the grep that finds them: `rg -U -n 'model_copy\(\s*update=\{[^}]*"status":\s*"' tests`.

**6. TASK-008's "no runs" tightening contradicts its own fixture rewrite.** Severity: low-med.
- **Evidence:**
  - `test_status_integration.py:265-271` (`test_status_no_runs_exist`) uses `mock_runs_dir`. After TASK-008:57 rewrites that fixture to build `.adw/runs` and chdir, the correct outcome is exit 0 with "No runs found".
  - TASK-008:53 instead says to expect exit 1 and no `.adw`. The outside-a-project case belongs to `test_project_guard`.
  - TASK-008:46-50 still lists `bootstrap.get_runs_dir (2)` and the integration `:31` patches as renames to `require_runs_dir`, while :54-57 drops them. That is the vacuous rename round 1 flagged as #9.
- **Verdict: apply.**
- **Edit:**
  - TASK-008:53: expect exit 0 and "No runs found".
  - TASK-008:46-50: the counts become status 6 and resume 1, both in unit tests. The four integration fixture patches are deleted, not renamed.

**7. TASK-001's tests miss the SIGKILL leg, and the label rule is ambiguous.** Severity: low.
- **Evidence:**
  - Nothing exercises the escalation to SIGKILL. `test_timeout_sends_sigterm_before_sigkill` proves that SIGTERM arrives, not the order.
  - `os.kill(pid, 0)` succeeds on a zombie, and a 1 s poll is tight on a busy CI runner.
  - The trap test calls `git("commit")` with no `cwd`, so a PATH slip would run real git in the checkout.
  - TASK-001:30's rule could label `git commit -m <msg>` as `` `git commit <msg>` ``, depending on whether flags are skipped or end the label. TASK-003:48's test message uses `` `git push -u` ``.
- **Verdict: apply.**
- **Edit:**
  - Add `test_timeout_escalates_to_sigkill_when_term_is_ignored`, with the fake `trap '' TERM; exec sleep 30` and `adw.git.KILL_GRACE` monkeypatched to 0.3.
  - For the grandchild test, give the grandchild its own `trap 'touch "$GC_MARK"' TERM`, or poll for 5 s.
  - Pass `cwd=tmp_path` in every fake-git test.
  - Define the label as the tool plus the args up to the first flag, at most two. Test that `commit -m msg` gives `git commit`.
- **Portability:** the scripts work unchanged under dash and bash-as-sh (`exec sleep`, `trap … TERM; sleep & wait`, `$!`).

**8. The tiers contradict their own rule.** Severity: low.
- **Evidence:**
  - `worktree add` runs the post-checkout hook, usually its slowest part, but gets 300 s (PLAN.md:130), while `checkout` gets 600 s.
  - `push` runs pre-push hooks but stays at 120 s (PLAN.md:132), now with a group kill.
- **Verdict: apply.**
- **Edit:** move `worktree add` to `HOOK_TIMEOUT`. Either move `push` there too, or record why 120 s stays.

**9. Coverage and housekeeping.** Severity: low.
- **Verdict: apply.**
- **Edits:**
  - **TASK-009 coverage:** the matrix doesn't check PLAN AC5's "update_run validates" (`test_update_run_validates_status`) or its typed-fields bullet. Add both, plus the new tests from findings 1 and 7.
  - **TASK-008 dependencies:** PLAN.md:265 lists TASK-008 without the dependencies its task file declares. Sync them, or move the AGENTS.md bullet to TASK-009 and drop the dependencies.
  - **A fourth shadowing site:** `create_or_switch_branch`'s local `branch_exists` (`hooks/git_branch.py:155`) ends up in the same module as the new function. Add it to TASK-002's name-clash list, renamed to `exists`.
  - **TASK-007's wrapper:** state that only the second call raises. The restore at `summary.py:339` is a third call, and it must delegate.
  - **TASK-007's `fchmod`:** do it after `fdopen` owns the file descriptor. Next to the symlink note in Out of Scope, add that a rename also drops hard links and ownership, and fails on a single-file bind mount.
  - **Optional:** `update_run` silently drops unknown keys, both today and after this change. Rejecting keys not in `IndexEntry.model_fields` would catch typos.

**Verified OK:**
- **mypy --strict:** `_run` is implementable (`Popen[str]`, with `CompletedProcess` built from `Any` output).
- **Test-seam migration:** it's complete.
  - The global-patch counts check out: 8/15/11 across the three hooks git tests, 2 in `worktree/test_branch.py`, 1 in `test_manager.py`.
  - The `run_trigger` Popen patches don't touch git.
  - No test would run real git in the checkout, apart from the cwd gap in finding 7.
- **`update_run`'s `model_dump`:** it keeps datetimes and lists, and the validation cost is negligible.
- **TASK-007's permissions:** `os.open(0o666)` plus `fchmod` is correct on macOS and Linux.
- **`get_runs_dir`:** all 20 test references are enumerated.
- **Cycles:** there are no import or task-dependency cycles.

No files or git state changed.

## Triage

<!--
Verdict values:
  apply   — real plan defect; edit PLAN.md / tasks / DECISIONS.md now
  defer   — has merit but out of scope for this plan; capture as a known limitation or follow-up
  reject  — contradicts an explicit Decision in PLAN.md/DECISIONS.md, or is taste/speculation/incorrect
-->

**Design resolution for #1 and #2.** Git stays in the terminal's process group (no `start_new_session`). The reviewer offered this as the explicit alternative.
- **Unchanged from today:** Ctrl+C reaches git directly, so git removes its own locks, and terminal prompts keep working.
- **On a timeout, or any other exception inside `_run`:** send SIGTERM to git's pid, wait `KILL_GRACE`, then SIGKILL, then call `wait()` without reading the pipes.
- **Cost:** a hook grandchild can outlive a timed-out git. This is rare, and recorded in the Risks.
- **Effect on round 1:** the round-1 #6 defer rationale, "a user at a terminal can answer a prompt", holds again.

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Ctrl+C leaves git's locks behind because `start_new_session` keeps SIGINT from reaching git | high | apply | Verified. It's a regression the round-1 edit introduced. Resolved by dropping the new session (see above), so Ctrl+C reaches git as it does today. `_run` also stops git on any exception, SIGTERM first. | TASK-001 (`_run`, `_stop`, interrupt test), PLAN.md:Decisions, PLAN.md:Risks, PLAN.md:Acceptance, TASK-009 |
| 2 | `start_new_session` removes git's controlling terminal, so prompts fail and the #6 defer rationale is void | med | apply | Resolved by the same choice. Git keeps its terminal, prompts keep working, and #6 stays deferred on its original rationale. | TASK-001 (Notes), PLAN.md:Decisions |
| 3 | The `communicate()` after SIGKILL can block on inherited pipes; PLAN.md:222 and RESEARCH.md:95 are stale | med | apply | After SIGKILL, call `wait()` without reading the pipes, as `hooks/runner.py` does. Fix both statements. | TASK-001, PLAN.md:Risks, RESEARCH.md |
| 4 | `except ADWError` around manager.py's existing `try` blocks swallows the `WorktreeError`s raised inside; `branch_exists`/`delete_branch` don't handle `GIT_TIMEOUT` | med | apply | Verified: `WorktreeError` subclasses `ADWError`. Wrap only the `git()` call. | TASK-003 (+`BRANCH_NOT_CREATED` test), TASK-002 |
| 5 | TASK-004's positive control can't run (there's no FAILED write in `interruption.py`); 4 multi-line test `model_copy` sites are missed | med | apply | Verified | TASK-004 |
| 6 | TASK-008's "no runs" tightening contradicts its fixture rewrite; the patch counts are stale | low | apply | Correct: `test_status_no_runs_exist` should expect exit 0 and "No runs found" | TASK-008 |
| 7 | No test for the SIGKILL leg; the zombie-pid poll; a fake-git test without `cwd`; an ambiguous label rule | low | apply | Add an escalation test and `cwd=tmp_path`, and define the label as args up to the first flag. The grandchild test goes (see the design resolution). | TASK-001, TASK-003 |
| 8 | The tiers contradict their rule: `worktree add` (post-checkout hook) and `push` (pre-push hook) sit below `HOOK_TIMEOUT` | low | apply | Both move to `HOOK_TIMEOUT` | PLAN.md:Decisions, TASK-001, TASK-003 |
| 9a | TASK-009 misses `test_update_run_validates_status`, the typed-fields bullet and the new `_run` tests | low | apply | Keeps coverage complete | TASK-009 |
| 9b | PLAN.md's task list doesn't show TASK-008's dependencies | low | apply | Sync with the task file | PLAN.md:Tasks |
| 9c | A fourth shadowing site: the local `branch_exists` in `create_or_switch_branch` | low | apply | Verified at `hooks/git_branch.py:155` | TASK-002 |
| 9d | TASK-007: only the second wrapped call raises (the restore is a third call); `fchmod` after `fdopen`; renames drop hard links and ownership and fail on bind mounts | low | apply | Precision | TASK-007, PLAN.md:Out of Scope |
| 9e | Make `update_run` reject unknown keys | low | reject | Optional hardening outside this phase's goal. The drop-unknown behaviour predates it, and rejecting could break callers that pass extra keys today. | |
