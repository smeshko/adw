# Status colours: adw list vs adw status <id>

Scratch project (`adw init --no-interactive`) with one fabricated run per status; `FORCE_COLOR=1 COLUMNS=160`. Each cell is the ANSI SGR sequence directly in front of the status word. Raw transcripts: `colours-after.txt`, `colours-before.txt`.

## After (this branch)

| Status | `adw list` SGR | `adw status <id>` SGR | Same |
|---|---|---|---|
| running | `\x1b[33m` | `\x1b[33m` | yes |
| completed | `\x1b[32m` | `\x1b[32m` | yes |
| failed | `\x1b[31m` | `\x1b[31m` | yes |
| interrupted | `\x1b[38;5;214m` | `\x1b[38;5;214m` | yes |
| aborted | `\x1b[90m` | `\x1b[90m` | yes |

## Before (staging bc66b08c)

| Status | `adw list` SGR | `adw status <id>` SGR | Same |
|---|---|---|---|
| running | `\x1b[33m` | `\x1b[33m` | yes |
| completed | `\x1b[32m` | `\x1b[32m` | yes |
| failed | `\x1b[31m` | `\x1b[31m` | yes |
| interrupted | `\x1b[38;5;214m` | `\x1b[38;5;214m` | yes |
| aborted | `\x1b[90m` | `\x1b[31m` | NO |
