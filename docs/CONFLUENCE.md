# Confluence Support - Design Document

## Overview

In addition to Jira, the project provides a `confluence` CLI and matching MCP
tools for managing Confluence Cloud pages from the terminal. Confluence Cloud
runs on the same Atlassian site as Jira (under the `/wiki` path) and uses the
same authentication, so no separate credentials are required.

## Authentication

Confluence Cloud uses the same account email and API token as Jira:

- **Email**: Atlassian account email
- **API Token**: Generated at https://id.atlassian.com/manage-profile/security/api-tokens
- **Site URL**: The Atlassian site URL (e.g., `https://yourcompany.atlassian.net`)

The client appends `/wiki` to the site URL to reach the Confluence API.

### Configuration resolution

Configuration is read from the shared file `~/.config/jira-cli/config.toml`
and from environment variables. Environment variables take precedence over the
file. For each value, a Confluence-specific variable is checked first, then the
Jira variable, then the file:

| Value | Resolution order |
|-------|------------------|
| Site URL | `CONFLUENCE_URL` -> `JIRA_URL` -> file `url` |
| Email | `CONFLUENCE_EMAIL` -> `JIRA_EMAIL` -> file `email` |
| API token | `CONFLUENCE_API_TOKEN` -> `JIRA_API_TOKEN` -> file `api_token` |

This means an existing working `jira` configuration also enables `confluence`
without further setup. The Confluence-specific variables exist only for the
case where Confluence lives on a different site or uses a different token.

## CLI Commands

The `confluence` command is a separate entry point installed alongside `jira`.

### Configuration

```bash
# Show the resolved configuration (token redacted)
confluence config --show
```

### Search

Searches content using CQL (Confluence Query Language).

```bash
confluence search "text ~ 'roadmap'"
confluence search "space = DEV and type = page" --limit 10
```

### Spaces

```bash
confluence space list
confluence space list --limit 50
```

### Pages

```bash
# Read a page by numeric ID (rendered to plain text)
confluence page 12345

# Show the raw storage-format (XHTML) body instead of rendered text
confluence page 12345 --raw

# Create a page from inline markdown
confluence create --space DEV --title "Release notes" --body "# Heading"

# Create a page from a markdown file, nested under a parent page
confluence create --space DEV --title "Child" --file notes.md --parent 12345

# Update a page's title and/or body
confluence update 12345 --title "New title"
confluence update 12345 --file notes.md
```

To find a page's numeric ID, use `confluence search`.

## Data Models

### Space

```python
class Space:
    id: str          # Numeric space ID
    key: str         # Space key (e.g., "DEV")
    name: str
    type: str        # e.g., "global", "personal"
    status: str      # e.g., "current"
```

### Page

```python
class Page:
    id: str              # Numeric page ID
    title: str
    space_id: str | None # Numeric space ID (absent in search results)
    status: str          # e.g., "current"
    version: int | None  # Current version number (absent in search results)
    body: str | None     # Storage-format XHTML (only when fetched in full)
    url: str | None      # Web UI URL
```

## Markdown to Storage Format Conversion

Confluence pages are stored as **storage format**, an XHTML-based
representation. When creating or updating a page, markdown is converted to
storage format. The supported syntax mirrors the Jira ADF converter:

| Syntax | Storage output |
|--------|----------------|
| `# Heading` | `<h1>`...`<h6>` |
| `**bold**` | `<strong>` |
| `*italic*` | `<em>` |
| `` `code` `` | `<code>` |
| ```` ```lang ```` | `code` macro with language parameter |
| `- item` | `<ul><li>` |
| `- [ ] item` / `- [x] item` | `task-list` macro (unchecked / checked) |
| `1. item` | `<ol><li>` |
| `[text](url)` | `<a href>` |
| `---` | `<hr/>` |
| Blank line | Paragraph break (`<p>`) |

Reading a page renders the storage-format body to plain text for the terminal.
Use `--raw` to view the unmodified storage XHTML.

## API Endpoints Used

CRUD operations use the Confluence REST API v2. CQL search uses the v1 search
endpoint, which has no v2 equivalent.

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Search | GET | `/wiki/rest/api/search?cql=...` |
| Read page | GET | `/wiki/api/v2/pages/{id}?body-format=storage` |
| List spaces | GET | `/wiki/api/v2/spaces` |
| Resolve space key | GET | `/wiki/api/v2/spaces?keys={key}` |
| Create page | POST | `/wiki/api/v2/pages` |
| Update page | PUT | `/wiki/api/v2/pages/{id}` |

Updating a page requires the current version number; the client fetches the
page first and submits the incremented version.

## MCP Server

The Confluence tools are registered on the same `jira-mcp` server.

### Available Tools

| Tool | Description |
|------|-------------|
| `confluence_search` | Search content with CQL |
| `get_page` | Get a page by ID, including its rendered body |
| `list_spaces` | List Confluence spaces |
| `create_page` | Create a page from markdown |
| `update_page` | Update a page's title and/or body |

## Modules

| Module | Purpose |
|--------|---------|
| `confluence_models.py` | `Space` and `Page` data models |
| `confluence_storage.py` | Markdown to storage format conversion and rendering |
| `confluence_client.py` | `ConfluenceClient` REST wrapper |
| `confluence_cli.py` | `confluence` Typer application |
| `confluence_mcp.py` | Registers Confluence tools on the MCP server |
