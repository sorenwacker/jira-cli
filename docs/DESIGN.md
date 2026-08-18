# Jira CLI - Design Document

## Overview

A CLI tool for managing Jira Cloud issues from the terminal. Built with Typer, with a planned NiceGUI web interface.

## Architecture

```
jira-cli/
├── src/
│   └── jira_cli/
│       ├── __init__.py
│       ├── adf.py          # Markdown to ADF conversion
│       ├── cli.py          # Typer CLI commands
│       ├── client.py       # Jira API client
│       ├── models.py       # Data models (Pydantic)
│       ├── config.py       # Configuration management
│       ├── mcp.py          # MCP server for Claude Desktop
│       ├── shell.py        # Interactive shell
│       ├── confluence_models.py   # Confluence data models
│       ├── confluence_storage.py  # Markdown to storage format conversion
│       ├── confluence_client.py   # Confluence API client
│       ├── confluence_cli.py      # Confluence Typer CLI
│       └── confluence_mcp.py      # Confluence MCP tools
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_client.py
│   ├── test_shell.py
│   └── conftest.py         # Fixtures
├── docs/
│   └── DESIGN.md
├── pyproject.toml
└── README.md
```

## Authentication

Jira Cloud uses:
- **Email**: Your Atlassian account email
- **API Token**: Generated at https://id.atlassian.com/manage-profile/security/api-tokens
- **Jira URL**: Your instance URL (e.g., `https://yourcompany.atlassian.net`)

Credentials stored in `~/.config/jira-cli/config.toml` or environment variables:
- `JIRA_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`

## CLI Commands

### Configuration

```bash
# Configure credentials (interactive)
jira config

# Show current config (redacted)
jira config --show
```

### Interactive Shell

```bash
jira shell
```

Shell commands:

| Command | Description |
|---------|-------------|
| `l` / `ls` | At root: list issues. Inside issue: show details |
| `list` | List your assigned issues |
| `cd ISSUE-KEY` | Select an issue |
| `cd ..` / `..` | Go back to root |
| `pwd` | Show current issue |
| `cat ISSUE-KEY` | Show issue details (works from anywhere) |
| `cat` / `show` | Show current issue details |
| `comments` | Show comments |
| `comment "text"` | Add a comment |
| `status` | Show available transitions |
| `status "New"` | Change status |
| `h` / `help` | Show help |
| `exit` / `quit` / `q` | Exit shell |

### Direct Commands

```bash
# List issues assigned to me
jira list
jira list --status "In Progress"
jira list --project PROJ
jira list --limit 10

# View issue details
jira view PROJ-123
jira view PROJ-123 --comments

# Add a comment
jira comment PROJ-123 "This is my comment"

# List available transitions
jira status PROJ-123

# Transition to new status
jira status PROJ-123 "In Progress"

# List assignable users for a project
jira user list --project PROJ

# Search users by name
jira user list --project PROJ --query "john"
```

## Data Models

### Issue

```python
class Issue:
    key: str                      # e.g., "PROJ-123"
    summary: str
    status: str
    assignee: str | None          # display name
    reporter: str | None          # display name
    project: str
    priority: str | None
    created: datetime
    updated: datetime
    due_date: date | None
    description: str | None
    attachments: list[Attachment]
    labels: list[str]
    components: list[str]         # component names
    fix_versions: list[str]       # version names
```

### Issue Field Writes

`create_issue` and `update_issue` accept the same metadata fields. People fields (`assignee`, `reporter`) are sent as account IDs; setting the reporter requires the "Modify Reporter" project permission. `components` and `fix_versions` are lists of names that must already exist in the project; an update replaces the stored list. `due_date` is an ISO date (`YYYY-MM-DD`). Fields left as `None` are not sent.

### Comment

```python
class Comment:
    id: str
    author: str
    body: str
    created: datetime
```

### Transition

```python
class Transition:
    id: str
    name: str
```

## Markdown to ADF Conversion

The CLI converts markdown text to Atlassian Document Format (ADF) for descriptions and comments. This preserves formatting when viewing in Jira's web UI.

### Supported Markdown Syntax

| Syntax | Description |
|--------|-------------|
| `**bold**` | Bold text |
| `*italic*` | Italic text |
| `` `code` `` | Inline code |
| ```` ```lang ```` | Code blocks with language |
| `# Heading` | Headings (levels 1-6) |
| `- item` | Bullet lists |
| `1. item` | Numbered lists |
| `[text](url)` | Links |
| `---` | Horizontal rule |
| Blank line | Paragraph break |

### Example

```bash
jira issue create PROJ "New feature" -d "## Overview

This is a **new feature** with:
- Item one
- Item two

\`\`\`python
def hello():
    print('world')
\`\`\`
"
```

## Dependencies

- `typer` - CLI framework
- `httpx` - HTTP client
- `pydantic` - Data validation
- `rich` - Terminal formatting

## API Endpoints Used

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Search issues | POST | `/rest/api/3/search/jql` |
| Get issue | GET | `/rest/api/3/issue/{key}` |
| Get comments | GET | `/rest/api/3/issue/{key}/comment` |
| Add comment | POST | `/rest/api/3/issue/{key}/comment` |
| Get transitions | GET | `/rest/api/3/issue/{key}/transitions` |
| Do transition | POST | `/rest/api/3/issue/{key}/transitions` |
| List statuses | GET | `/rest/api/3/status` |
| Search users | GET | `/rest/api/3/users/search` |

## Data Models

### User

```python
class User:
    account_id: str        # Jira account ID
    display_name: str      # Display name
    email: str | None      # Email (may be None for privacy)
    active: bool           # Whether user is active
    avatar_url: str | None # Avatar image URL
```

## Subtask Creation

Subtasks are child issues linked to a parent issue. Created using the `parent` parameter in `create_issue()` or the dedicated CLI command.

### CLI Command

```bash
# Create subtask under parent issue
jira issue create-subtask PROJ-123 "Subtask summary"

# With options
jira issue create-subtask PROJ-123 "Summary" --type "Sub-task" --description "Details"
```

### API

```python
# Create subtask programmatically
client.create_issue(
    project="PROJ",
    summary="Subtask summary",
    issue_type="Sub-task",
    parent="PROJ-123",
)
```

## MCP Server

The MCP (Model Context Protocol) server exposes Jira operations as tools for AI assistants like Claude Desktop.

### Running the Server

```bash
# Start MCP server (stdio transport)
jira-mcp
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "jira-mcp"
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `get_issue` | Get issue details by key |
| `search_issues` | Search issues with JQL |
| `get_my_issues` | Get issues assigned to current user |
| `create_issue` | Create an issue or subtask |
| `update_issue` | Update issue fields |
| `get_transitions` | List available status transitions |
| `transition_issue` | Change issue status |
| `get_comments` | Get issue comments |
| `add_comment` | Add a comment |
| `get_projects` | List all projects |
| `get_users` | Search users |
| `watch_issue` | Start watching an issue |
| `unwatch_issue` | Stop watching an issue |

## Confluence Support

Confluence Cloud management is provided by a separate `confluence` CLI and
matching MCP tools, reusing the same Atlassian credentials. See
[CONFLUENCE.md](CONFLUENCE.md) for the full design.

## Future (v2+)

- NiceGUI web interface
- Bulk operations
- Caching for offline viewing
