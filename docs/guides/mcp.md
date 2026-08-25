# MCP Server

`jira-mcp` is a Model Context Protocol server (stdio transport) exposing every Jira and Confluence operation as a tool.

## Claude Code

Register the server at user scope so it is available in every directory:

```bash
claude mcp add jira --scope user -- "$(command -v jira-mcp)"
```

This requires the [global install](../getting-started/installation.md). User scope stores the entry in `~/.claude.json`; verify with `claude mcp list`. To share the server with a repository instead, add a project `.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["run", "jira-mcp"]
    }
  }
}
```

Restart Claude Code after changing the server or its tools.

## Claude Desktop

Configure `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "jira-mcp"
    }
  }
}
```

## Writing conventions

The server instructs LLM clients how to write content through its server instructions; the descriptions of `create_issue`, `update_issue`, `create_page`, and `update_page` refer clients to them. The default convention: Jira issue descriptions and Confluence pages must be plain English prose without markdown tables (Jira does not render them, and the Confluence converter leaves them as literal text), and issue descriptions must be structured into the sections Context, Goal, Scope, Acceptance criteria.

To use your own convention, create `~/.config/jira-cli/guidance.md`; its content replaces the default guidance. Delete the file to return to the default. An empty file is treated as absent.

At startup the server also fetches the ticket statuses and issue types defined in the configured Jira instance and lists them in the server instructions: statuses grouped by category for `transition_issue`, issue types (subtask types marked) for `create_issue`. If the fetch fails, the instructions say so and refer clients to `get_transitions`.

## Tools

Every tool has a CLI equivalent; a test gate enforces this (see [Architecture](../architecture/overview.md#surface-parity)).

| Tool | Description | CLI equivalent |
|------|-------------|----------------|
| `get_issue` | Issue details by key | `jira issue view` |
| `search_issues` | Search issues with JQL | `jira issue search` |
| `get_my_issues` | Issues assigned to the current user | `jira issue list` |
| `create_issue` | Create an issue or subtask | `jira issue create`, `create-subtask` |
| `update_issue` | Update issue fields | `jira issue edit` |
| `get_transitions` | Available status transitions | `jira issue move` |
| `transition_issue` | Change status | `jira issue move` |
| `get_comments` | Comments of an issue | `jira issue view --comments` |
| `add_comment` | Add a comment | `jira issue comment add` |
| `update_comment` | Replace a comment's body | `jira issue comment edit` |
| `delete_comment` | Delete a comment | `jira issue comment delete` |
| `get_projects` | Visible projects | `jira project list` |
| `get_users` | Search users | `jira user list` |
| `watch_issue` | Start watching | `jira issue watch` |
| `unwatch_issue` | Stop watching | `jira issue unwatch` |
| `delete_issue` | Delete an issue permanently | `jira issue delete` |
| `get_issue_quality_report` | [Quality scores](../reference/quality.md) | `jira issue quality` |
| `confluence_search` | Search Confluence with CQL | `confluence search` |
| `get_page` | Page by ID including its body | `confluence page` |
| `list_spaces` | List Confluence spaces | `confluence space list` |
| `create_page` | Create a page from markdown | `confluence create` |
| `update_page` | Update a page's title and/or body | `confluence update` |

Only `confluence_search` carries a `confluence_` prefix; the page and space tool names do not collide with the issue-oriented Jira tools in the shared namespace.

Example prompt in Claude Code:

```
Generate an issue quality report for project DAT
```
