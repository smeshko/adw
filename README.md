# adw

adw is a Python CLI that drives Claude Code through plan, build, validate, document and ship phases to take a ticket to a merged PR.

## How it works

- `adw run` takes a feature description or a Linear ticket and runs the five phases in a fixed order.
- Each run works in its own git worktree and branch. `--no-worktree` runs in the current directory.
- adw writes the state of a run to disk as it goes, so `adw run --from-run <run-id>` continues an earlier run with the same worktree, branch and artifacts.
- A phase is a folder with a `config.yaml`, a `prompt.md` and optional `pre.sh` and `post.sh` hooks. The built-in phases are in [`src/adw/defaults/commands/`](src/adw/defaults/commands/).
- A web dashboard lists runs and shows their phases, logs and costs.

## Requirements

- Python 3.13 or newer and [`uv`](https://docs.astral.sh/uv/)
- [Claude Code](https://code.claude.com/docs) on your `PATH` as `claude`
- `git` and the GitHub CLI, `gh`

## Install

From a checkout:

```bash
uv tool install --editable .
adw --version
```

## Use

Set up a repository once. `adw init` writes `.adw/project.yaml`, which holds the project's test and build commands.

```bash
adw init
```

Run the workflow:

```bash
adw run "Add CSV export to the reports page"   # all five phases
adw run ADW-23                                  # start from a Linear ticket
adw run --phase plan "Add CSV export"           # one phase only
adw run --from-run <run-id>                     # continue an earlier run
adw run --dry-run "Add CSV export"              # show what would happen
```

Watch and manage runs:

| Command | What it does |
|---|---|
| `adw dashboard web` | Opens the web dashboard in the browser |
| `adw logs follow` | Streams the model's output from a live run |
| `adw logs state` | Shows the state of a run, now or at a snapshot |
| `adw logs export` | Bundles a run's logs and state for sharing |
| `adw abort <run-id>` | Stops a running execution |
| `adw cleanup <run-id>` | Removes a run's worktree, and its branch if asked |
| `adw cleanup-orphans` | Finds and removes worktrees no run owns |
| `adw global list` | Lists runs across all projects |
| `adw global stats` | Shows totals across all projects |

Every command takes `--help`.

## Development

```bash
uv sync
scripts/preflight.sh   # lint, format and types, the same gates as CI
uv run pytest          # about 3 minutes, enforces 80% coverage
```

Tests run against a mock executor, so they never call a model. Pull requests target `staging`. [`AGENTS.md`](AGENTS.md) has the full contributor guide.

## Docs

- [Orchestrator](docs/architecture/deep-dive/orchestrator.md)
- [Phase runner](docs/architecture/deep-dive/phase-runner.md)
- The [plan](docs/architecture/deep-dive/plan-phase.md), [build](docs/architecture/deep-dive/build-phase.md), [validate](docs/architecture/deep-dive/validate-phase.md) and [document](docs/architecture/deep-dive/document-phase.md) phases
- [Extensions](docs/architecture/deep-dive/extensions-system.md)
