# jira-cli

[![CI](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sorenwacker/jira-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/sorenwacker/jira-cli)

Command-line tools for Jira Cloud and Confluence Cloud: a `jira` CLI with an interactive shell, a `confluence` CLI, and a `jira-mcp` server exposing the same operations to Claude Code and Claude Desktop.

Documentation: https://sorenwacker.github.io/jira-cli/

## Install

```bash
uv tool install git+https://github.com/sorenwacker/jira-cli.git
```

## Configure

Generate an API token at https://id.atlassian.com/manage-profile/security/api-tokens, then:

```bash
jira config
```

Or set `JIRA_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`. The same credentials serve `confluence`.

## Use

```bash
jira issue list
jira issue view PROJ-123 --comments
jira issue create PROJ "Summary" --type Bug --description "Details"
jira issue move PROJ-123 "In Progress"
jira issue comment add PROJ-123 "Comment text"
jira issue quality --project PROJ
jira shell

confluence search "text ~ 'roadmap'"
confluence create --space DEV --title "Notes" --file notes.md
```

Register the MCP server with Claude Code:

```bash
claude mcp add jira --scope user -- "$(command -v jira-mcp)"
```

Every CLI capability is also an MCP tool; a test gate keeps the two surfaces in sync. See the [documentation](https://sorenwacker.github.io/jira-cli/) for the full command and tool reference.

## Develop

```bash
uv sync --extra dev
make test
make docs
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
