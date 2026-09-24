# Adversarial Validation — Round 1

**Run:** 2026-09-24 06:30 UTC
**Plan:** 02.7-one-home-for-git-format-paths-status
**Status at start:** draft
**Reviewers:** subagent (in Codex's place) + subagent (independent lens). The plan's risk is `large`, so Codex and an independent lens run in parallel. Codex failed at once with "You've hit your usage limit … try again at 11:57 AM", so a clean `general-purpose` subagent ran the Codex focus text verbatim.
**Mid-round event:** during the round, the user asked to merge `staging`. It fast-forwarded to `7b61e72a` (#212, phase 2.3 merged). The triage adds the resulting plan updates as row M1.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

### Codex (failed)

```
# Codex Adversarial Review

Codex did not return valid structured JSON.

- Parse error: You’ve hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 11:57 AM.
```

### Reviewer A: subagent running the Codex focus text

**Verdict: needs-attention.** The plan is well researched. Every line reference I spot-checked is current, and all the counts I re-derived hold: 31 git/gh calls, 19 formatter definitions, 5 CLI colour maps, and the `analytics.html:132` tooltip bug. It covers the epic's "What to build" and all five of its acceptance criteria, and TASK-009 maps every PLAN criterion.

Some of it needs fixing before implementation:
- Three edits the plan prescribes fail as written.
- One gate does nothing. I ran it to confirm.
- Two greps can't be satisfied without touching out-of-scope code.
- The timeout and atomic-write designs create real-world failure modes that the Risks section doesn't cover.

## Findings

**1. The prescribed names collide with existing parameters and locals.** Severity: high.
- **Evidence:**
  - TASK-002:24,35,38 call a new `delete_branch()` inside two functions where `delete_branch` is already a bool:
    - `WorktreeManager.remove_worktree(..., delete_branch: bool)` (manager.py:520, call at :643)
    - `cleanup_command(delete_branch: bool = typer.Option…)` (cleanup.py:27, call at :138)
  - So the new call becomes `True(...)`.
  - `remove_worktree` also has a local `pr_exists = …` at manager.py:627. Importing a `pr_exists` function into that module raises `UnboundLocalError` (ruff F823).
  - TASK-006:30 says to "call `status_style(s).color`", but `status_style` is already a local in two places: `status_style = _get_status_style(...)` at list.py:221 and global_commands.py:164. This is the same F823 trap that 1.8 avoided for `runs_dir`.
- **Why it matters:** preflight fails. The implementer then improvises aliases, which changes the patch target that TASK-002:44 names (`adw.worktree.manager.pr_exists`).
- **Verdict:** apply. The fix is cheap and deterministic.
- **Edit:**
  - TASK-002: prescribe `from adw.git import delete_branch as git_delete_branch, pr_exists as git_pr_exists` in manager.py and cleanup.py, and update the patch targets at :44.
  - TASK-006: rename the locals to `color`.
  - Add a PLAN Decision noting the shadowing hazard.

**2. TASK-004's warnings-as-errors gate never fires.** Severity: high.
- **Evidence:**
  - TASK-004:52 uses `-W "error::UserWarning:pydantic.*"`.
  - pytest regex-escapes the module field of a command-line `-W`: `parse_warning_filter(..., escape=True)` turns it into `'pydantic\\.\\*\\Z'`, which matches no module.
  - Repro in the scratchpad: a `model_copy(update={"status": "failed"})` test passes under that filter with "1 warning", and fails under `-W "error:Pydantic serializer warnings"`.
- **Why it matters:**
  - The fallback in TASK-004:75 depends on someone noticing that the filter didn't match, and that failure is silent.
  - mypy doesn't help: it flags direct attribute assignment, but not `model_copy(update=…)` or `update_run(**Any)`.
- **Verdict:** apply.
- **Edit:**
  - TASK-004:52: make the message filter the primary one, and delete the note at :75.
  - Add a one-line positive control to the evidence: inject a string write, show that the run fails, then revert.

**3. The status-literal greps can't be satisfied within scope.** Severity: high.
- **Evidence:** I ran the grep in PLAN.md:215 / TASK-004:50 on today's code.
  - `status[\"']?\s*[:=]` also matches the phase-pipeline assignment `phase_status = "completed"` (routes.py:454,459,462,626,631,633) and partials.py:663. The plan's Out of Scope keeps both.
  - It also matches docstrings: index_manager.py:51,77,127,183, run_lookup.py:86,156, models/index.py:39, context.py:65, snapshot_manager.py:122 and partials.py:688.
  - The tuple grep matches the usage comment at status_badge.html:5 and the docstring at partials.py:657.
- **Why it matters:** a criterion that says "prints nothing" pushes the implementer either to edit the out-of-scope phase vocabulary or to ignore the criterion.
- **Verdict:** apply.
- **Edit:** in PLAN.md AC5, TASK-004 and TASK-009, either:
  - use `\bstatus…`, which drops `phase_status`, and exclude `>>>` and docstring lines, or
  - keep the regex and list the expected residual hits.

**4. Nothing is designed for what happens to git's process when a timeout fires.** Severity: med.
- **Evidence:**
  - TASK-001 uses `subprocess.run(timeout=)`, which sends SIGKILL to `git` alone. git cleans up its lockfiles on SIGTERM and SIGINT, but SIGKILL skips that, and it orphans hook grandchildren.
  - So a killed commit, `add` or `pull` can leave `.git/index.lock` or ref `.lock` files behind. For `pull` that happens in the user's main checkout (ship.py:198).
  - PLAN.md:176 claims a timeout makes "the run fail with a readable panel". That is false for commit and stage: `_auto_commit` catches `Exception` (phase_runner.py:1212), logs a warning, and the run continues. Every later git call in that worktree then fails on the stale lock.
  - A killed `worktree add` leaves `.git/worktrees/<id>` behind. `_cleanup_partial_worktree`'s `branch -D` then refuses to delete the branch, so a retry with a feature-branch name hits `BRANCH_EXISTS`.
  - TASK-003 wraps timeouts for fetch and add, but leaves a `worktree remove` timeout as a raw `GIT_TIMEOUT`.
- **Verdict:** apply.
- **Edit:**
  - TASK-001 `_run`: use `Popen(start_new_session=True)`. On timeout, SIGTERM the process group, wait about 5 s, then SIGKILL.
  - Add a PLAN Risk covering stale locks and the auto-commit swallow.
  - TASK-003: run `git worktree prune` in `_cleanup_partial_worktree`, and map a `worktree remove` timeout to `WORKTREE_REMOVE_FAILED`.

**5. The timeout tiers miss other commands that run hooks, move a lot of data, or can prompt.** Severity: med.
- **Evidence:** PLAN.md:119-125 raise the timeout only for commit (600 s) and `worktree add` (300 s). These all stay at 60 s:
  - `checkout`, which runs the post-checkout hook (git_branch.py:159,168; ship.py:192)
  - `pull`, which runs the post-merge hook (for example husky running `npm install`) and downloads LFS objects
  - `git add -A`, which runs the LFS clean filter and can walk a large untracked tree
  - `worktree remove`, which deletes a whole tree
  - `fetch` on a large repo or a slow link

  The most common "hang" is actually a credential or SSH-passphrase prompt on /dev/tty. A timeout turns that into a misleading "check network" failure.
- **Verdict:** apply.
- **Edit:** in PLAN Decisions and TASK-001/002/003:
  - add `NETWORK_TIMEOUT` (about 300 s) for fetch and pull
  - put checkout, pull and `worktree remove` on the hook or checkout tier
  - name credentials and ssh-agent in the `GIT_TIMEOUT` suggestion
  - record a decision on `GIT_TERMINAL_PROMPT=0` for the non-interactive paths (the lifecycle fetch and the ship pull)

**6. `atomic_write` changes state files from 0644 to 0600.** Severity: med.
- **Evidence:**
  - TASK-007:13 uses `NamedTemporaryFile`, which calls mkstemp and creates the file with mode 0600.
  - I verified that a 0644 `project.yaml` is 0600 after the `os.replace`. The same happens to the wizard's phase configs, `context.json`, `~/.adw/index.jsonl` and `projects.yaml`.
  - `os.replace` also turns a symlinked target into a regular file.
- **Why it matters:** the permission change is user-visible, for example in a container or CI job that runs as another uid, or in a shared checkout.
- **Verdict:** apply.
- **Edit:**
  - TASK-007: before the replace, `os.fchmod` the temp file to the existing target's mode, or to `0o666 & ~umask` for a new file.
  - Add a mode-preservation case to `test_fs.py`.
  - Note the symlink behaviour in Out of Scope.

**7. Two test rewrites would stop proving or intercepting anything.** Severity: med.
- **Evidence:**
  - TASK-007:33's `side_effect=[None, OSError]` mocks out the first write. `test_atomic_write_preserves_existing_files_on_failure` then passes without the backup and restore ever running.
  - TASK-008:50 renames the patch target `adw.cli.bootstrap.get_runs_dir` to `require_runs_dir`. After the change, `create_orchestrator` doesn't call any helper, so the patches in test_resume_integration.py:32 and test_status_integration.py:32 intercept nothing.
  - `adw resume` then builds its orchestrator against the checkout's own `.adw/runs` in the cwd. The fixture never chdirs, which breaks the AGENTS.md rule that such tests run in a throwaway directory.
- **Verdict:** apply.
- **Edit:**
  - TASK-007: make the first call delegate to the real `adw.fs.atomic_write`.
  - TASK-008: replace those patches with `monkeypatch.chdir(tmp_path)` in the fixtures.

**8. A missing test file, and `adw cleanup` has no coverage.** Severity: med.
- **Evidence:**
  - TASK-002:46,55 name `tests/unit/cli/test_cleanup.py`, which doesn't exist. The acceptance pytest command exits 4.
  - No test anywhere covers the `cleanup --delete-branch` WORKTREE_NOT_FOUND path, and that is where finding 1's clash lives.
- **Verdict:** apply.
- **Edit:** TASK-002: drop the missing path, and add a `CliRunner` test for `cleanup <id> --delete-branch` when the worktree is already gone.

**9. The phase is well beyond the epic's "small-to-medium PR".** Severity: med.
- **Evidence:**
  - PLAN.md:4 says `Risk: large`, and I estimate about 80 files.
  - TASK-004:27-45 rewrites about 40 plain comparisons. The plan's own Out of Scope says a StrEnum compares equal to its string, and I confirmed mypy strict doesn't flag those comparisons.
  - The epic asks for status *sets*, not comparisons, and phases 2.11 and 2.12 rewrite those same dashboard and CLI files next.
- **Verdict:**
  - Apply: limit TASK-004 to typing, writes and sets.
  - Defer to the user: splitting the phase into two PRs, one for git + fs + runs dir and one for format + status.

**10. The greps don't agree with each other.** Severity: low.
- **Evidence:**
  - PLAN.md:208 and TASK-009:35 use `:\.2f\}`, which misses `:,.2f}`, so "prints only format.py" can never be true. TASK-005:86 uses `:,?\.2f\}`.
  - stats_aggregator.py:73 has a `.2f` docstring hit that no task lists.
  - TASK-002's grep for `subprocess` in `git.py` will also hit the module docstring.
  - The `atomic_write` grep also matches `atomic_write_config`.
- **Verdict:** apply.
- **Edit:** unify on `:,?\.2f\}` in PLAN.md and TASK-009, and list the expected hits.

**11. Several references are wrong.** Severity: low.
- **Evidence:**
  - TASK-003:43: the test file is `tests/unit/core/test_ship_extension.py`, not under `core/extensions/`.
  - TASK-002:43: `:856` is the `WorktreeBranchManager` import. The whole test at 854-861 should go, not just the import.
  - TASK-005:51: the function is `create_dashboard_app`, not `create_app`.
  - `PHASE_SEQUENCE` is a tuple, so the rewritten comparisons against lists in test_phases.py:68 and :133-135 fail. They need `list(PHASE_SEQUENCE)`.
  - PLAN.md:62 lists 3 feature docs, but more name helpers that move:
    - analytics-time-range-stat-cards.md:92
    - budget-section-breakdown-table.md:96
    - terminal-focus-view-modes.md:110
    - active-runs-phase-pipeline.md:16
    - epic 04:167
    - the `hooks/__init__.py` docstring
    - progress.py:50
- **Verdict:** apply.
- **Edit:** fix these in TASK-002/003/004/005 and in PLAN.md's Scope/Docs.

**12. The overlap with draft PR #212 is understated.** Severity: low.
- **Evidence:** besides server.py and summary.py (PLAN.md:192), #212 also edits `models/__init__.py`, `cli/app.py`, `logging/live_stream.py` and `test_summary.py`. #212's merge-base is `1212c5b4`, 17 commits behind staging, so it will need a rebase regardless.
- **Verdict:** apply.
- **Edit:** extend the PLAN Risk with those files.

**13. The timeout message names only the first argument.** Severity: low.
- **Evidence:** TASK-001 would print "`gh pr` timed out" and "`git worktree` timed out". Today's GH_TIMEOUT message, "PR creation timed out after 60 seconds", is clearer.
- **Verdict:** apply.
- **Edit:** TASK-001: name the first two non-flag arguments. That is still safe, because the PR body comes later in the argv.

**14. TASK-008 has a hidden dependency.** Severity: low.
- **Evidence:** TASK-008:28 writes an AGENTS.md bullet that names `adw.git`, `adw.format` and `adw.fs`, which TASK-001, 005 and 007 create. Yet TASK-008 says "Depends on: None".
- **Verdict:** apply.
- **Edit:** move the bullet to TASK-009, or declare the dependencies.

**15. Two concerns that belong in Out of Scope.** Severity: low.
- **Evidence:**
  - `IndexManager.update_run` does an unlocked read-modify-write (index_manager.py:110-158). `atomic_write` prevents torn writes, but not lost updates between concurrent runs.
  - Run from a project subdirectory, `require_runs_dir` tells the user to run `adw init`, which would create a nested project.
- **Verdict:** defer. Root discovery and locking belong to 2.8/2.12.
- **Edit:** record both in PLAN.md's Out of Scope.

**Against the epic:** every deviation is justified.
- Keeping `project_runs_dir` avoids the 1.8 shadowing problem.
- The epic's grep matches nothing even today, so replacing it with `rg -U` plus the `import subprocess` list is sound.
- Widening `atomic_write` to the index, the registry and `run_directory` is justified, subject to finding 6.
- Removing the dead unpushed-commits path is sound.

The only unjustified drift is the comparison churn in finding 9.

## Next steps

- Apply findings 1–8, 10–14 and the first half of 9 by editing PLAN.md and TASK-001–009.
- Put two questions to the user: the phase split (the rest of 9), and the prompt-disabling decision (part of 5).
- Once the greps are corrected, run them against d9ba2f79 to record the expected residual hits as the baseline.

(I changed no files and no git state. The pytest and permission repros ran in the session scratchpad.)

### Reviewer B: subagent, independent lens

**Plan review: 02.7 one home for git, format, paths, status**

20 findings: 3 high, 6 med and 11 low. Each one names the plan edit it needs, so the full list follows. The five most important:

- **#1:** TASK-004's warnings-as-errors flag is inert (verified).
- **#2:** the RunStatus grep can't print nothing, which its criterion requires.
- **#3:** after TASK-008, the resume integration tests would pass without testing anything, and they would write into the checkout.
- **#4:** TASK-007's wizard rollback tests would become vacuous.
- **#5:** several of the prescribed edits create name clashes that break the code.

### Findings

**1. TASK-004's `-W` filter is inert, and a working filter would surface about 18 test-side string writes the plan doesn't list** (high)
- **Evidence:**
  - pytest escapes the module field of `-W`. In a scratch test, `-W "error::UserWarning:pydantic.*"` gave "1 passed, 1 warning".
  - `-W "error:Pydantic serializer warnings"` and `error::UserWarning:pydantic.main` both correctly fail the same test.
  - The plan's approach is that every write uses a member. But `IndexManager.update_run` applies updates with `entry.model_copy(update=updates)` (index_manager.py:145), which skips validation.
  - Tests pass plain strings to it:
    - `update_run(..., status="completed")` appears 7× in `tests/unit/core/test_index_manager.py`, 8× in `tests/integration/cli/test_global_commands_integration.py`, and once in `test_feature_description.py:202`.
    - `model_copy(update={"status": ...})` appears in `test_resume_manager.py:125` and `test_abort.py:66`.
- **Verdict:** apply. The gate is vacuous today, and a working gate would fail TASK-009's "no warnings" criterion.
- **Edit:** in TASK-004:
  - Use `-W "error:Pydantic serializer warnings"` as the only filter.
  - Make `update_run` validate its updates, either with `setattr` under the existing `validate_assignment` or with `IndexEntry.model_validate({**entry.model_dump(), **updates})`. Add a test for it.
  - Convert the two test `model_copy` sites to members.
  - Add a note: the warnings-as-errors run can miss writes inside `except Exception` blocks (phase_runner.py:1217, registry.py), so the plain full-suite "no warnings" check stays the real gate.

**2. The status-literal grep can't print nothing, and it doesn't check comparisons at all** (high)
- **Evidence:** running the regex today shows three problems:
  - It matches code that the plan leaves out of scope: the phase-pipeline assignments `phase_status = "completed"` in routes.py:454/459/462/626/631/633, and the local `status = "completed"` at partials.py:663.
  - It matches docstrings: snapshot_manager.py:122, models/context.py:65, models/index.py:39, index_manager.py:51/77/127/183, run_lookup.py:86/156 and partials.py:688.
  - `[:=]` followed by a quote can never match `==` or `!=`, so no comparison is checked.

  The tuple regex also hits a docstring at partials.py:657 and a template usage comment at status_badge.html:5. And the plan misses one comparison: global_commands.py:751, `entry.status != "running"`.
- **Verdict:** apply. The criterion can't be met without editing out-of-scope code, and it doesn't cover the scope it claims.
- **Edit:** in TASK-004, PLAN.md and TASK-009, use:

  ```
  rg -n --type py "status[\"']?\]?\s*(==|!=|=|:)\s*[\"'](running|completed|failed|interrupted|aborted)[\"']" src | rg -v 'phase_status|phase\["status"\]|>>>|description='
  ```

  Then:
  - Rename the partials.py:663 local to `phase_status`.
  - Rewrite the four prose docstrings: run_lookup.py:86, snapshot_manager.py:122, index_manager.py:77 and partials.py:688.
  - Add global_commands.py:751 to the sites.
  - Restrict the tuple regex to `--type py`, and fix partials.py:657.

**3. The resume integration fixture would stop intercepting and write into the checkout** (high)
- **Evidence:**
  - `tests/integration/cli/test_resume_integration.py:31-32` patches `adw.cli.bootstrap.get_runs_dir`, so that `create_orchestrator` (called at resume.py:139) uses the tmp runs dir. The tests never chdir.
  - TASK-008 moves this patch to `require_runs_dir`, which `create_orchestrator` won't call.
  - `create_orchestrator` would then mkdir `cwd/.adw/runs` inside the checkout, and `orchestrator.resume` would fail with CONTEXT_NOT_FOUND.
  - The tests only assert header text printed before that point, so they would still pass.
- **Verdict:** apply. This is a test passing for the wrong reason, with side effects on the repo.
- **Edit:** in TASK-008, rewrite the `mock_runs_dir` fixtures in the resume and status integration tests to use `monkeypatch.chdir(tmp_path)`, and drop the runs-dir patches.

**4. TASK-007's new failure injection makes both wizard rollback tests vacuous** (med)
- **Evidence:**
  - With `side_effect=[None, OSError]`, the first `atomic_write` does nothing.
  - `test_atomic_write_preserves_existing_files_on_failure` (test_summary.py:473-509) then sees the original `project.yaml` without any restore having happened.
  - `test_atomic_write_rollback_on_failure` sees "not exists" trivially.
  - The actual patch lines are :465 and :501, not :505 and :541.
- **Verdict:** apply.
- **Edit:** in TASK-007, use a counter wrapper: its first call delegates to the real `adw.fs.atomic_write`, and its second raises OSError.

**5. The prescribed edits create name clashes** (med)
- **Evidence:**
  - `remove_worktree(..., delete_branch: bool)` (manager.py:520) and `cleanup_command(delete_branch: bool)` (cleanup.py:27) both shadow the new `delete_branch()` function. mypy would report "bool not callable".
  - `pr_exists = self._branch_manager.check_pr_exists(...)` (manager.py:627) would become `pr_exists = pr_exists(...)`, an UnboundLocalError (ruff F823).
  - TASK-006 repeats the pattern: `status_style = _get_status_style(...)` at list.py:221 and global_commands.py:164.
  - `cleanup_command` has no tests at all.
- **Verdict:** apply. Preflight would catch these, but the plan's code and its patch target (`adw.worktree.manager.pr_exists`) should be right as written.
- **Edit:**
  - TASK-002: rename the local to `has_pr`, and import `delete_branch` under an alias (e.g. `delete_local_branch`) in manager.py and cleanup.py. State the matching patch targets.
  - TASK-006: rename the `status_style` locals to `color`.

**6. A timeout sends SIGKILL, which leaves `index.lock` behind and orphans hook processes** (med)
- **Evidence:**
  - On a timeout, `subprocess.run` calls `kill()` and then `wait()` (checked on 3.13.7).
  - git holds `.git/index.lock` while pre-commit hooks run, and SIGKILL means it never removes the lock. Hook and ssh grandchildren keep running.
  - Auto-commit swallows the error (phase_runner.py:1190-1227), so every later `git add -A` fails silently and the PR ships without those commits.
  - Ship's `git checkout <base>` (ship.py:192) can leave the user's main checkout half-switched.
- **Verdict:** apply. The Risks section claims a timeout only produces "a readable panel".
- **Edit:**
  - TASK-001: `_run` uses `Popen(start_new_session=True)`. On timeout it sends SIGTERM to the process group, waits about 5 s, then sends SIGKILL. git removes its lockfiles on SIGTERM.
  - Add this to the PLAN Risks, and mention `index.lock` in the GIT_TIMEOUT suggestion.

**7. The timeout classes miss hook-running and network commands, and there's no override** (med)
- **Evidence:**
  - `git pull` (ship.py:198) runs post-merge hooks.
  - `git checkout <branch>` (git_branch.py:159/168) runs post-checkout hooks and the LFS smudge filter, which downloads.
  - `git fetch` at run start (run_lifecycle.py:580) is on the critical path, and a large repo on a slow link can exceed 60 s.
  - The Risks section's claim that fetch and pull "finish in seconds or are hung" is unsupported.
- **Verdict:** apply.
- **Edit:** in the PLAN Decisions and TASK-001/002/003, either:
  - add `NETWORK_TIMEOUT = 300` for fetch, pull and `gh pr view`, and use `HOOK_TIMEOUT` for checkout and pull, or
  - add an `ADW_GIT_TIMEOUT_SCALE` environment override, recorded in the Risks.

**8. The cost grep in PLAN.md and TASK-009 is wrong in both directions** (med)
- **Evidence:**
  - `format_cost` produces `$1,234.56`, so its format spec is `:,.2f}`, which `:\.2f\}` doesn't match. `format.py` would never show up.
  - stats_aggregator.py:73 has a docstring containing `${stats.estimated_cost:.2f}`, which does match. TASK-005's `:,?\.2f\}` also hits it, but TASK-005 doesn't list it.
- **Verdict:** apply.
- **Edit:** use `:,?\.2f\}` in PLAN.md and TASK-009, and add the stats_aggregator.py:73 docstring edit to TASK-005.

**9. Two test paths don't exist** (med)
- **Evidence:**
  - `tests/unit/cli/test_cleanup.py` doesn't exist, so TASK-002's acceptance pytest command exits 4 ("file or directory not found").
  - TASK-003 cites `tests/unit/core/extensions/test_ship_extension.py`; the real file is `tests/unit/core/test_ship_extension.py:227`.
- **Verdict:** apply.
- **Edit:** fix both paths. Optionally add one CliRunner test in TASK-002 for `cleanup --delete-branch --force` when the worktree doesn't exist (WORKTREE_NOT_FOUND).

**10. `status_style(status: str)` built on `Mapping[RunStatus, …].get(status)` fails mypy strict** (low)
- **Evidence:** I checked this; mypy reports call-overload and no-any-return errors.
- **Verdict:** apply.
- **Edit:** TASK-006 specifies:

  ```
  try: return STATUS_STYLES[RunStatus(status)]
  except ValueError: return UNKNOWN_STATUS_STYLE
  ```

**11. `atomic_write` changes file permissions to 0600** (low)
- **Evidence:**
  - `NamedTemporaryFile` creates its file through mkstemp with mode 0600, and `os.replace` keeps that mode.
  - Under the default umask these files are 0644 today. The change would hit `context.json`, `~/.adw/index.jsonl`, `projects.yaml`, and the wizard's committed `.adw/project.yaml` and phase configs.
- **Verdict:** apply.
- **Edit:** in TASK-007, before the replace, chmod the temp file to the existing target's mode, or to `0o666 & ~umask` when the target is new. Add a test.

**12. The round-trip test asserts spaced JSON** (low)
- **Evidence:** plain `model_dump_json()` writes `{"status":"failed"}` with no spaces (checked).
- **Verdict:** apply.
- **Edit:** in TASK-004, use `model_dump_json(indent=2)` (which is what `ContextManager.save` writes), or assert on `json.loads(...)["status"]`.

**13. Timeout errors are mapped inconsistently** (low)
- **Evidence:**
  - A `git worktree remove` timeout becomes a bare ADWError. It escapes `except WorktreeError` in the cleanup-orphans loop (cleanup.py:258) and stops the loop.
  - The timeout variant of GIT_FETCH_FAILED is recoverable, but the non-zero-exit variant at run_lifecycle.py:590 isn't.
- **Verdict:** apply.
- **Edit:** in TASK-003, map the `worktree remove` timeout to WORKTREE_REMOVE_FAILED, and make both fetch variants agree on `recoverable`.

**14. Visible changes the PLAN Risks section doesn't list** (low)
- **Evidence:**
  - Stats-cache age: `5 minutes ago` becomes `5m ago` (global_commands.py:553).
  - Progress summary: `13m44s` becomes `13m 44s`.
  - live.log: `(0.4s)` becomes `(0s)`, which loses information for short streams.
  - `adw list --global` changes colours too (list.py:249).
  - The badge's fallback for an unknown status changes from `⦻` to `?`.
  - The GH_TIMEOUT message and suggestion text change.
  - `--status` "Valid values:" switches from alphabetical to definition order.
  - `adw projects` shows a time instead of "unknown" for naive timestamps.
- **Verdict:** apply.
- **Edit:** add these to the PLAN Risks.

**15. The timeout message is ambiguous for gh and worktree** (low)
- **Evidence:** `{args[0]}` produces "`gh pr` timed out" and "`git worktree` timed out".
- **Verdict:** apply.
- **Edit:** in TASK-001, name up to two leading non-option arguments (`gh pr create`). That still never includes the body.

**16. Docs the plan misses** (low)
- **Evidence:**
  - Four feature docs name private helpers that TASK-005 deletes: `docs/features/active-runs-phase-pipeline.md:16`, `budget-section-breakdown-table.md:96`, `analytics-time-range-stat-cards.md:92` and `terminal-focus-view-modes.md:110`.
  - The `src/adw/hooks/__init__.py` docstring still describes branch, commit and diff handling.
- **Verdict:** apply.
- **Edit:** add the four docs to TASK-005, and the docstring to TASK-002.

**17. Phase-list comparisons would break** (low)
- **Evidence:** `AVAILABLE_PHASES` is a list; `PHASE_SEQUENCE` is a tuple. `test_phases.py:68` and :133-135 compare function results, which are lists, against it, so they would fail.
- **Verdict:** apply.
- **Edit:** TASK-004 says `list(PHASE_SEQUENCE)` in the code and the tests.

**18. Test changes the task lists miss** (low; these fail visibly, not silently)
- **Evidence:**
  - test_run_lifecycle.py:~1257 asserts `call_args[0][0] == ["git", "fetch", …]`.
  - test_manager.py:854-861 is the property test; all of it must go, not just the import at :856.
  - test_context_manager.py:348-383 injects its failure through `Path.rename`.
  - test_artifact_manager.py's `builtins.open` patch will be bypassed, not just "might be", because tempfile calls `io.open` directly.
- **Verdict:** apply.
- **Edit:** list these in TASK-003, TASK-002 and TASK-007.

**19. Two acceptance greps expect less output than they'll print** (low)
- **Evidence:**
  - `rg 'atomic_write' src` also prints the `atomic_write_config` definition and call, plus the imports.
  - `rg subprocess src/adw/git.py` also hits the module docstring.
- **Verdict:** apply.
- **Edit:** in TASK-007, use `rg -n 'atomic_write\(' src | rg -v 'def |atomic_write_config'`. In TASK-002, allow the docstring hit.

**20. TASK-008's dependencies and assumptions** (low)
- **Evidence:**
  - Its AGENTS.md note names modules from TASK-001, 005, 006 and 007, but it says "Depends on: None".
  - The resume uncertainty is already settled: resume's first call reaches the runs-dir helper (resume.py:77→36).
  - The RED claim is wrong for `logs`, which already exits 1 and creates nothing.
- **Verdict:** apply.
- **Edit:**
  - Move the AGENTS.md bullet to TASK-009, or declare the dependencies.
  - Drop the resume hedge from RESEARCH.md and TASK-008.
  - Fix the RED wording.

### Verified

- **Git calls:** 31 `subprocess.run` calls in 10 files, plus `run_trigger`'s `Popen` of `adw` itself.
  - 3 of them set a timeout.
  - `rg -U` matches 24 today; the other 7 pass their argv as a variable.
  - The epic's single-line grep matches nothing.
- **`force=True`:** every caller passes it (manager.py:643, cleanup.py:138).
- **`RunLookup._list_runs`:** returns `[]` when the runs directory is missing (:114).
- **No import cycles:** nothing under `adw.models` imports `adw.core`, so constants→models and format→models are cycle-free.
- **StrEnum on 3.13.7:** `"running" in RunStatus` is True, `"paused"` is False, and `", ".join(RunStatus)` works.
- **Pydantic 2.12.5:**
  - `model_copy` leaves a plain `str` in the field.
  - `model_dump_json` still writes the value, and warns with a UserWarning attributed to `pydantic.main`.
- **mypy:** catches a string passed to the constructor and attribute assignment, but not `model_copy` or `update_run`.
- **Timeouts:** after a timeout on POSIX, `subprocess.run` waits only for the killed child.
- **Jinja:** env globals are visible inside `{% import %}`/`{% from %}` macros (tested with `Jinja2Templates`), and NamedTuple attribute access works in templates.
- **Code facts confirmed:**
  - the `analytics.html:132` `total_tokens` bug is real
  - `get_runs_dir` calls mkdir
  - `call_on_complete` and auto-commit swallow errors as warnings
- **Test fixtures:** `isolated_home` places HOME at `tmp_path/"home"`, so "nothing new" is the right assertion.

## Triage

<!--
Verdict values:
  apply   — real plan defect; edit PLAN.md / tasks / DECISIONS.md now
  defer   — has merit but out of scope for this plan; capture as a known limitation or follow-up
  reject  — contradicts an explicit Decision in PLAN.md/DECISIONS.md, or is taste/speculation/incorrect
-->

A = Reviewer A (in Codex's place), B = Reviewer B (lens). Duplicates are merged into one row.

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | The new `delete_branch` / `pr_exists` / `status_style` names clash with existing parameters and locals (A1, B5) | high | apply | Verified at manager.py:520/627, cleanup.py:27, list.py:221 and global_commands.py:164; preflight would fail on the prescribed code | TASK-002 (Name clashes; patch targets), TASK-006 (locals → `color`), PLAN.md:Decisions |
| 2 | The `-W "error::UserWarning:pydantic.*"` gate never fires; `update_run` and 18 test sites still write plain strings (A2, B1) | high | apply | Both reviewers reproduced it. Use the message filter, make `update_run` validate, and convert the test writes | TASK-004 (message `-W` filter + positive control; `update_run` validates; test `model_copy` sites), PLAN.md:Decisions, PLAN.md:Acceptance |
| 3 | The status-literal grep can't print nothing, doesn't check `==`/`!=`, and misses global_commands.py:751 (A3, B2) | high | apply | Verified; it hits the out-of-scope `phase_status` and docstrings | TASK-004 (two greps; `phase_status` rename; docstrings; global_commands.py:751), PLAN.md:Acceptance, TASK-009 |
| 4 | SIGKILL on timeout leaves `index.lock` and orphans hooks; auto-commit swallows the error; a partial `worktree add` leaves admin files (A4, B6) | med | apply | A real failure mode the Risks section misstated. Kill the process group with SIGTERM before SIGKILL, run `worktree prune` in partial cleanup, and state the Risk correctly | TASK-001 (Popen + killpg SIGTERM→SIGKILL; 2 tests), TASK-003 (`worktree prune`), PLAN.md:Risks, PLAN.md:Decisions. **Deeper than expected:** with `Popen`, every `patch("subprocess.run")` on git code stops intercepting, so TASK-002/003 now patch the `git`/`gh` seam and grep for leftovers |
| 5 | Timeout tiers miss network and hook commands (fetch, pull, checkout, `worktree remove`, `add -A`) (A5, B7) | med | apply | Add `NETWORK_TIMEOUT` = 300 s for fetch / pull / `gh pr view`. `HOOK_TIMEOUT` covers checkout and pull; `CHECKOUT_TIMEOUT` covers `worktree remove` and `add -A`. The suggestion names credentials. No env override (YAGNI) | PLAN.md:Decisions (tiers), TASK-001 (constants, suggestion), TASK-002 (checkout, add -A, `pr_exists`), TASK-003 (fetch, ship checkout/pull, worktree remove) |
| 6 | `GIT_TERMINAL_PROMPT=0` for non-interactive paths (A5, second half) | low | defer | It changes behaviour beyond "add timeouts": today a user at a terminal can answer a credential prompt. The new suggestion names credentials, so a prompt-caused timeout is diagnosable. Filed as follow-up | PLAN.md:Out of Scope (follow-up) |
| 7 | `atomic_write` changes file modes to 0600 and replaces symlinks with files (A6, B11) | med | apply | Verified by both. Preserve the existing mode (else `0o666 & ~umask`); symlinks go to Out of Scope | TASK-007 (`os.open` 0o666 + `fchmod`; 2 mode tests), PLAN.md:Decisions, PLAN.md:Out of Scope (symlinks), PLAN.md:Acceptance |
| 8 | The wizard rollback tests go vacuous with `side_effect=[None, OSError]`; the line refs are :465/:501 (A7a, B4) | med | apply | The first call must run the real `atomic_write` | TASK-007 (delegating counter wrapper; :465/:501) |
| 9 | The resume/status integration fixtures stop intercepting after TASK-008 and write into the checkout (A7b, B3) | high | apply | A test passing for the wrong reason, with repo side effects; use `monkeypatch.chdir(tmp_path)` | TASK-008 (resume/status/list integration fixtures → `monkeypatch.chdir`) |
| 10 | `tests/unit/cli/test_cleanup.py` doesn't exist; `cleanup --delete-branch` is untested (A8, B9a) | med | apply | Drop the path; add a CliRunner test where the clash from #1 lives | TASK-002 (+`tests/unit/cli/test_cleanup.py`) |
| 11 | Limit TASK-004 to typing, writes and sets; skip the ~40 plain comparisons (A9, first half) | med | reject | A StrEnum member catches typos that a string literal can't. "No run-status literals in `src` Python" is one checkable rule (#3), where "writes and sets only" is not. The edits are mechanical | |
| 12 | Split the phase into two PRs (A9, second half) | med | reject | The user asked for phase 2.7 end to end as one PR, and the epic sizes it as one phase. The 8 task commits keep the change reviewable piece by piece | |
| 13 | The cost grep `:\.2f\}` misses `:,.2f}`, and stats_aggregator.py:73's docstring matches (A10, B8) | med | apply | Unify on `:,?\.2f\}` and fix the docstring | PLAN.md:Acceptance, TASK-005 (stats_aggregator.py:73), TASK-009 |
| 14 | Wrong references: the `test_ship_extension.py` path, all of test_manager.py:854-861, `create_dashboard_app`, the tuple-vs-list `PHASE_SEQUENCE`, 4 more feature docs, epic 04:167, the `hooks/__init__.py` and progress.py:50 docstrings (A11, B9b, B16, B17) | low | apply | Each one verified | TASK-002 (test_manager 854-861, hooks/__init__, epic 04), TASK-003 (ship test path), TASK-004 (`list(PHASE_SEQUENCE)`), TASK-005 (`create_dashboard_app`, 4 docs), TASK-006 (progress.py:50), PLAN.md:Scope |
| 15 | Missed test changes: test_run_lifecycle.py ~1257 argv, test_context_manager.py:348-383 rename injection, the artifact test's `builtins.open` bypassed by tempfile (B18) | low | apply | They fail visibly, but the task should list them | TASK-003 (lifecycle ~1257, manager :606), TASK-007 (context 348-383, artifact `fsync` injection) |
| 16 | The #212 overlap is understated (A12) | low | apply | Superseded: #212 merged into this branch (`7b61e72a`) mid-round, so the Risk becomes "resolved" and the refs are refreshed (M1) | PLAN.md:Risks (see M1) |
| 17 | The timeout message names only `args[0]` (`gh pr`, `git worktree`) (A13, B15) | low | apply | Name up to two leading non-option args | TASK-001 (label = tool + up to two non-option args), PLAN.md:Decisions |
| 18 | TASK-008's AGENTS.md bullet depends on TASK-001/005/006/007 (A14, B20a) | low | apply | Declare the dependencies | TASK-008 (Depends on) |
| 19 | `update_run` lost updates, and `require_runs_dir` run from a subdirectory (A15) | low | defer | Both predate this phase (unlocked read-modify-write; cwd-as-root everywhere). Recorded in Out of Scope and filed as follow-ups | PLAN.md:Out of Scope (follow-ups) |
| 20 | `Mapping.get(str)` on a `RunStatus`-keyed map fails mypy strict (B10) | low | apply | Use `RunStatus(status)` in a try/except ValueError | TASK-006 (`RunStatus(status)` try/except) |
| 21 | The round-trip test asserts spaced JSON (B12) | low | apply | Assert on `json.loads(...)["status"]` | TASK-004 (assert on `json.loads`) |
| 22 | Timeout mapping is inconsistent: a `worktree remove` timeout escapes the orphan loop; fetch `recoverable` differs by path (A4, B13) | low | apply | Map to `WORKTREE_REMOVE_FAILED`; make both fetch variants recoverable | TASK-003 (remove → WORKTREE_REMOVE_FAILED + test; fetch recoverable both paths) |
| 23 | Visible changes missing from Risks (stats-cache age, progress `13m44s`, live.log sub-second `0s`, `list --global` colours, badge fallback, GH_TIMEOUT text, `--status` order, `adw projects` naive times) (B14) | low | apply | The PR must list what users will see | PLAN.md:Risks (visible changes) |
| 24 | Acceptance greps expect less output than they'll print (`atomic_write` vs `atomic_write_config`; the docstring in `git.py`) (A10, B19) | low | apply | Tighten the greps | TASK-002 (subprocess grep), TASK-007 (`atomic_write\(` grep) |
| 25 | The resume hedge is settled (resume.py:77→36); the RED wording is wrong for `logs` (B20b) | low | apply | Drop the hedge; `logs` already exits 1 | TASK-008 (Notes, RED), RESEARCH.md:Uncertainty |
| M1 | Merging `staging` mid-round brought #212: line refs moved (server.py:78, summary.py:289, app.py:177/242/349/368, live_stream.py:235) and the baseline is now 2982 passed / 5 skipped / 84.79% | low | apply | Keep the plan's refs and baseline current | PLAN.md (Research baseline, Risks, Acceptance), RESEARCH.md, TASK-004/005/007/008 (line refs), TASK-009 (baseline, remaining phases) |
