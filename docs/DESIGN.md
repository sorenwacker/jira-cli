# Jira CLI - Design Document

## Overview

A CLI tool for managing Jira Cloud issues from the terminal. Built with Typer, with a planned NiceGUI web interface.

## Architecture

```
jira-cli/
├── src/
│   └── jira_cli/
│       ├── __init__.py
│       ├── cli.py          # Typer CLI commands
│       ├── client.py       # Jira API client
│       ├── models.py       # Data models (Pydantic)
│       ├── config.py       # Configuration management
│       └── shell.py        # Interactive shell
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
```

## Data Models

### Issue

```python
class Issue:
    key: str              # e.g., "PROJ-123"
    summary: str
    status: str
    assignee: str | None
    project: str
    priority: str | None
    created: datetime
    updated: datetime
    description: str | None
```

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

## Future (v2+)

- NiceGUI web interface
- Create new issues
- Update issue fields (priority, labels, assignee)
- Watch/unwatch issues
- Bulk operations
- Caching for offline viewing
