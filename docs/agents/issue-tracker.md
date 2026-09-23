# Issue tracker

This repo's issues live in Linear, team **ADW**. Issue ids look like `ADW-<n>`.

- Read one issue: `mcp__linear-server__get_issue` with its id. The Linear MCP tools are often deferred — load them with ToolSearch first.
- Find issues: `mcp__linear-server__list_issues` with `team: "ADW"`.
- Where ids appear: in the branch name (`feature/adw-12-<slug>`) and in the PR body's `Closes ADW-12` line. Commits on Linear-tracked branches carry no ticket ref.

## Legacy ids

Commits before September 2026 cite `ADW-7` … `ADW-36` from an earlier, deleted Linear team. The current team reuses the `ADW-` prefix, so those old ids now resolve to unrelated issues — or to nothing. For work from that era, read the PR (`#<number>` in the commit subject) instead.
