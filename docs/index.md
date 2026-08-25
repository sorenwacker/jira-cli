# jira-cli

Command-line tools for Jira Cloud and Confluence Cloud: a `jira` CLI with an interactive shell, a `confluence` CLI, and a `jira-mcp` server that exposes the same operations to AI assistants such as Claude Code and Claude Desktop.

## Features

- **Issues**: list, view, search with JQL, create (including subtasks), edit, transition, watch, delete
- **Comments**: add, edit, delete
- **Quality report**: score issues on completeness (1-10)
- **Confluence pages**: search with CQL, read, create and update from markdown
- **Interactive shell**: filesystem-like navigation (`cd PROJ-123`, `ls`, `cat`) with tab completion
- **MCP server**: every CLI capability as an MCP tool, with configurable writing guidance

## Quick Install

```bash
uv tool install git+https://github.com/sorenwacker/jira-cli.git
```

## Quick Start

```bash
jira config                      # store URL, email and API token
jira issue list                  # issues assigned to you
jira issue view PROJ-123 --comments
jira shell                       # interactive mode
```

## Documentation

**Getting Started**

- [Installation](getting-started/installation.md)
- [Configuration](getting-started/configuration.md)

**Guides**

- [Jira CLI](guides/jira-cli.md)
- [Interactive Shell](guides/shell.md)
- [Confluence CLI](guides/confluence.md)
- [MCP Server](guides/mcp.md)

**Reference**

- [Markdown Formatting](reference/markdown.md)
- [Issue Quality Scoring](reference/quality.md)

**Architecture**

- [Overview](architecture/overview.md)

**Contributing**

- [Development](contributing/development.md)
