# jira-cli

[![CI](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sorenwacker/jira-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/sorenwacker/jira-cli)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

Work with Jira Cloud and Confluence Cloud from your terminal, or let an AI assistant do it for you. The project gives you three interfaces over one client: a command-line interface, an interactive shell, and a Model Context Protocol (MCP) server for assistants such as Claude Code and Claude Desktop.

Read the [full documentation](https://sorenwacker.github.io/jira-cli/) for the complete command and tool reference.

## Features

- **Issues**: list, view, search with Jira Query Language (JQL), create issues and subtasks, edit fields, change status, watch, and delete.
- **Comments**: add, edit, and delete.
- **Quality report**: score issues from 1 to 10 on description, labels, assignee, priority, attachments, and recent activity.
- **Confluence pages**: search with Confluence Query Language (CQL), read pages, and create or update them from Markdown.
- **Interactive shell**: move through issues as if they were directories, with tab completion for commands and comment IDs.
- **MCP server**: every command is also a tool. A test keeps both interfaces in sync, so neither one falls behind.

## Requirements

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- An Atlassian account with an API token

## Installation

```bash
uv tool install git+https://github.com/sorenwacker/jira-cli.git
```

This installs three commands: `jira`, `confluence`, and `jira-mcp`.

## Configuration

Create a token on the [Atlassian API tokens page](https://id.atlassian.com/manage-profile/security/api-tokens), then store your credentials:

```bash
jira config
```

To configure without prompts, set these environment variables instead:

```bash
export JIRA_URL="https://SITE_NAME.atlassian.net"
export JIRA_EMAIL="ACCOUNT_EMAIL"
export JIRA_API_TOKEN="API_TOKEN"
```

Replace the following:

- `SITE_NAME`: your Atlassian site name
- `ACCOUNT_EMAIL`: the email address of your Atlassian account
- `API_TOKEN`: the token you created

Confluence reuses the same credentials, so it needs no extra setup.

## Usage

These examples use `PROJ` as a project key and `PROJ-123` as an issue key. Substitute your own.

### Jira issues

```bash
jira issue list
jira issue view PROJ-123 --comments
jira issue search "project = PROJ AND status = 'In Progress'"
jira issue create PROJ "Summary" --type Bug --description "Details"
jira issue edit PROJ-123 --priority High
jira issue move PROJ-123 "In Progress"
jira issue comment add PROJ-123 "Comment text"
jira issue quality --project PROJ
```

### Confluence pages

```bash
confluence search "text ~ 'roadmap'"
confluence space list
confluence page 12345
confluence create --space DEV --title "Release notes" --file notes.md
```

### Interactive shell

```bash
jira shell
```

Inside the shell, `cd PROJ-123` selects an issue, `ls` lists what is in scope, and `comment "text"` adds a comment to the issue you selected. Type `help` for the command list.

### MCP server

To register the server with Claude Code for every directory, run:

```bash
claude mcp add jira --scope user -- "$(command -v jira-mcp)"
```

Restart Claude Code afterwards to load the tools. For Claude Desktop and project-scoped setups, read the [MCP server guide](https://sorenwacker.github.io/jira-cli/guides/mcp/).

## Development

```bash
uv sync --extra dev
uv run pre-commit install
make test
make docs
```

Documentation, tests, and code change together, and every rule the project adopts has a test that enforces it. The [development guide](https://sorenwacker.github.io/jira-cli/contributing/development/) describes the gates and the dependency policy.

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Attribution

This project, including its documentation, was written with [Claude Code](https://claude.com/claude-code).
