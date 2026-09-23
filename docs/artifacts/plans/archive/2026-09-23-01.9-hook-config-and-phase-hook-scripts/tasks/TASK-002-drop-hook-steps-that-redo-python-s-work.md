# TASK-002: Drop hook steps that redo Python's work

Depends on: None
Suggested commit: `refactor(hooks): drop hook steps that duplicate PhaseRunner and DocumentExtension`

## Goal

`build/post.sh` no longer auto-commits, and `document/post.sh` no longer rewrites `pr_description.md`. `PhaseRunner._auto_commit_changes` and `DocumentExtension.extra_artifacts` are the only writers.

## Files

- `src/adw/defaults/commands/build/post.sh`:
  - Delete STEP 2, the `python3 -c` auto-commit block, from the `ADW_FEATURE`/`ADW_RUN_ID` checks to the end of the file.
  - Rewrite the header to describe story-output extraction only, and drop the exit code 1 line and the `git.skip_hooks` line.
- `src/adw/defaults/commands/document/post.sh`:
  - Delete STEP 2, the `## Summary` → `pr_description.md` extraction, and renumber STEP 3.
  - Keep the `feature_doc.md` and `document_output.md` steps.
- `tests/integration/test_phase_hook_scripts.py` (new): two script tests.
- `docs/architecture/deep-dive/build-phase.md:186`: `post.sh` becomes "Story output extraction", and the auto-commit section names `PhaseRunner._auto_commit_changes` as the only committer.
- `docs/architecture/deep-dive/document-phase.md`:
  - Remove the `pr_description.md (from ## Summary to end)` line from the post-hook box (~line 57) and from the post.sh extraction list (~line 188).
  - `pr_description.md` comes only from `DocumentExtension`.

## Acceptance

- [ ] `test_build_post_hook_extracts_story_and_leaves_changes_uncommitted`:
  - Setup: in `git_repo`, commit `.adw/project.yaml` (`name: demo`, `language: python`). The old step 2 exits 0 without committing when no config loads, so without this the RED run would pass. Then write an uncommitted `src.py`. Run `build/post.sh` with `ADW_LLM_OUTPUT` holding the `# UPDATED STORY OUTPUT` … `# END STORY OUTPUT` markers, plus `ADW_ARTIFACTS_DIR`, `ADW_FEATURE`, `ADW_RUN_ID` and `ADW_PHASE=build`.
  - Assert:
    - exit 0
    - `build_output.md` holds the text between the markers
    - `git status --porcelain` still lists `src.py`
    - `git log --oneline | wc -l` is still 1
- [ ] `test_document_post_hook_keeps_extension_pr_description`:
  - Setup: in `tmp_path`, pre-write `pr_description.md` = `"from extension"`. Run `document/post.sh` with an `ADW_LLM_OUTPUT` that contains a `## Summary` section.
  - Assert: the file still reads `"from extension"`, and `document_output.md` exists.
- [ ] `grep -n "python3" src/adw/defaults/commands/build/post.sh` returns nothing.

Evidence:
- the RED run on today's scripts. The build test fails with a new commit, since under pytest the venv's `python3` has adw. The document test fails with the file overwritten.
- the GREEN run
- the grep

## Steps

### RED
- [ ] Write both tests in `tests/integration/test_phase_hook_scripts.py`. Resolve the script paths from `Path(adw.__file__).parent / "defaults" / "commands" / …`, and run them with `subprocess.run(["/bin/bash", str(path)], cwd=…, env={**os.environ, …})`.
- [ ] The build test needs `cwd=git_repo`, so the old auto-commit acts on the test repo and not the checkout. The document test runs in `tmp_path`.
- [ ] Run both, and confirm both fail.

### GREEN
- [ ] Delete the two steps, and fix both headers.
- [ ] Run the tests green, and run `uv run pytest tests/integration/test_document_phase.py -o addopts=""`.

### REFACTOR
- [ ] Update the two deep-dive docs.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Don't run either script from the checkout while developing. The old `build/post.sh` commits whatever is dirty in the cwd.
- `document-feature/instructions.xml` step 5 already makes the final message the raw PR description, starting at `## Summary`. So the PR body `DocumentExtension` stores (`final_output`) matches what the shell step used to extract. No prompt change is needed.
