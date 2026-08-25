# Configuration

Both `jira` and `confluence` authenticate with your Atlassian account email and an API token. Generate a token at https://id.atlassian.com/manage-profile/security/api-tokens.

## Interactive setup

```bash
jira config           # prompts for URL, email and token
jira config --show    # print the resolved configuration, token redacted
confluence config --show
```

Credentials are written to `~/.config/jira-cli/config.toml`.

## Environment variables

Environment variables take precedence over the file:

```bash
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_EMAIL="your@email.com"
export JIRA_API_TOKEN="your-api-token"
```

## Confluence resolution order

Confluence Cloud runs on the same Atlassian site as Jira (under `/wiki`), so a working `jira` configuration also enables `confluence`. For each value a Confluence-specific variable is checked first, then the Jira variable, then the file:

| Value | Resolution order |
|-------|------------------|
| Site URL | `CONFLUENCE_URL` -> `JIRA_URL` -> file `url` |
| Email | `CONFLUENCE_EMAIL` -> `JIRA_EMAIL` -> file `email` |
| API token | `CONFLUENCE_API_TOKEN` -> `JIRA_API_TOKEN` -> file `api_token` |

The Confluence-specific variables are only needed when Confluence lives on a different site or uses a different token.

## MCP writing guidance

The MCP server ships default writing guidance for LLM clients. To replace it, create `~/.config/jira-cli/guidance.md`; see [MCP Server](../guides/mcp.md#writing-conventions).
