# jira-cli

[![CI](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sorenwacker/jira-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/sorenwacker/jira-cli)

CLI tool for managing Jira Cloud issues from the terminal.

## Installation

### Local Development

```bash
git clone https://github.com/sorenwacker/jira-cli.git
cd jira-cli
uv pip install -e .
```

### Global Install with uv

```bash
uv tool install git+https://github.com/sorenwacker/jira-cli.git
```

This installs `jira`, `jira-mcp`, and `confluence` commands globally.

## Configuration

Generate an API token at https://id.atlassian.com/manage-profile/security/api-tokens

Then configure:

```bash
jira config
```

Or set environment variables:

```bash
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_EMAIL="your@email.com"
export JIRA_API_TOKEN="your-api-token"
```

## Usage

### Interactive Shell

```bash
jira shell
```

Shell commands (with tab completion):

```
# Navigation
l / ls                  List open issues (-a for all including Done)
list                    List your assigned issues
cd ISSUE-KEY            Select an issue (e.g., cd DAT-123)
cd .. / ..              Go back to root
pwd                     Show current issue
search "JQL"            Search with custom JQL

# Create/Edit
new PROJECT "Summary"   Create new issue (--type TYPE)
edit --summary "new"    Edit fields (--priority, --labels, --description)

# Issue commands (inside an issue)
cat / show              Show issue details
comments                Show comments
comment "text"          Add a comment
delcomment ID           Delete a comment
status                  Show available transitions
status "New Status"     Change status
watch / unwatch         Watch/unwatch current issue

# General
h / help                Show help
exit / quit / q         Exit shell
```

### Direct Commands

List assigned issues:

```bash
jira issue list
jira issue list --status "In Progress"
jira issue list --project PROJ
```

View issue details:

```bash
jira issue view PROJ-123
jira issue view PROJ-123 --comments
```

Issue details include attachments when present:

```
Attachments:
  - screenshot.png (245 KB) - https://yourcompany.atlassian.net/...
  - data.csv (1.2 MB) - https://yourcompany.atlassian.net/...
```

Create issue:

```bash
jira issue create PROJ "Issue summary" --type Bug --description "Details"
jira issue create PROJ "Issue summary" --reporter 5b10ac8d... --components "API,UI" --fix-versions "1.2.0" --due-date 2026-09-01
```

Edit issue:

```bash
jira issue edit PROJ-123 --summary "New title" --priority High
jira issue edit PROJ-123 --reporter 5b10ac8d... --components "API,UI" --fix-versions "1.2.0" --due-date 2026-09-01
```

`--reporter` and `--assignee` take Jira account IDs (find them with `jira user list`). `--components` and `--fix-versions` take comma-separated names that must already exist in the project; setting them replaces the current value. `--due-date` takes a `YYYY-MM-DD` date. Setting the reporter requires the "Modify Reporter" project permission.

Search with JQL:

```bash
jira issue search "project = PROJ AND status = Open"
```

Add comment:

```bash
jira issue comment add PROJ-123 "This is my comment"
```

Edit comment:

```bash
jira issue comment edit PROJ-123 12345 "Updated comment text"
```

Delete comment:

```bash
jira issue comment delete PROJ-123 12345
```

Change status:

```bash
jira issue move PROJ-123              # List transitions
jira issue move PROJ-123 "In Progress"  # Change status
```

Watch/unwatch:

```bash
jira issue watch PROJ-123
jira issue unwatch PROJ-123
```

## Confluence

The `confluence` command manages Confluence Cloud pages using the same
Atlassian credentials as `jira`. No extra configuration is needed if `jira`
already works.

```bash
# Search content with CQL
confluence search "text ~ 'roadmap'"

# List spaces
confluence space list

# Read a page by ID
confluence page 12345
confluence page 12345 --raw          # raw storage-format XHTML

# Create a page from markdown
confluence create --space DEV --title "Notes" --body "# Heading"
confluence create --space DEV --title "Notes" --file notes.md --parent 12345

# Update a page
confluence update 12345 --title "New title"
confluence update 12345 --file notes.md
```

See [docs/CONFLUENCE.md](docs/CONFLUENCE.md) for details.

## MCP Server

The CLI includes an MCP server for integration with Claude Desktop and Claude Code.

### Claude Code

Register the server at user scope so it is available in every directory:

```bash
claude mcp add jira --scope user -- "$(command -v jira-mcp)"
```

This requires the global install above. User scope stores the entry in
`~/.claude.json`; verify it with `claude mcp list`.

To share the server with a repository instead, add a project `.mcp.json`:

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

Restart Claude Code to load the MCP server.

### Claude Desktop

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

### Issue Writing Convention

The server instructs LLM clients how to write issue text, via the server instructions and the `create_issue`/`update_issue` tool descriptions: descriptions must be plain English prose, must not contain markdown tables (Jira does not render them), and must be structured into the sections Context, Goal, Scope, Acceptance criteria.

### Available Tools

| Tool | Description |
|------|-------------|
| `get_issue` | Get issue details by key |
| `search_issues` | Search issues using JQL |
| `get_my_issues` | Get issues assigned to current user |
| `create_issue` | Create a new issue or subtask |
| `update_issue` | Update issue fields |
| `get_transitions` | Get available status transitions |
| `transition_issue` | Change issue status |
| `get_comments` | Get comments for an issue |
| `add_comment` | Add a comment to an issue |
| `get_projects` | Get all visible projects |
| `get_users` | Search for users |
| `watch_issue` | Start watching an issue |
| `unwatch_issue` | Stop watching an issue |
| `delete_issue` | Delete an issue permanently |
| `get_issue_quality_report` | Generate quality report with ratings (1-10) |
| `confluence_search` | Search Confluence content with CQL |
| `get_page` | Get a Confluence page by ID, including its body |
| `list_spaces` | List Confluence spaces |
| `create_page` | Create a Confluence page from markdown |
| `update_page` | Update a Confluence page's title and/or body |

### Issue Quality Report

The `get_issue_quality_report` tool analyzes issues and scores them on a 1-10 scale:

| Criterion | Points | Condition |
|-----------|--------|-----------|
| Description | 3 | Present and >50 chars (+1 if short) |
| Labels | 2 | Has labels |
| Assignee | 2 | Is assigned |
| Priority | 1 | Priority set |
| Attachments | 1 | Has attachments |
| Activity | 1 | Updated in last 30 days |

Example usage in Claude Code:
```
Generate an issue quality report for project DAT
```

## Development

```bash
uv pip install -e ".[dev]"
pytest
```
