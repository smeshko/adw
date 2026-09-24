# Evidence — 02.6-collapse-init-wizard

Transcripts of `adw init --wizard` in a scratch `git init` repo with `HOME` pointed at a scratch dir. `<scratch>` stands for the session scratchpad.

- `before-*.txt` — `staging` at `5f40b3bb`, before this branch. Declining at the summary prints "files have been written" and exits 0, although nothing was written.
- `after-accept-defaults.txt` — this branch (`.worktrees/adw-22/.venv/bin/adw`), 40 empty lines on stdin, then `adw validate`: exit 0, `Step 1/7` … `Step 7/7`, one "Configuration written", `0 errors`.
- `after-decline-at-summary.txt` — 12 empty lines, then `n` at "Create configuration?": "Nothing was written", exit 1, no `.adw`.
- `after-sigint-at-prompt.txt` — SIGINT sent to the `adw` process while it waits at the first prompt: exit 130, no `.adw`.
