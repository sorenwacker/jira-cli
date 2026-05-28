# jira-cli

[![CI](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/sorenwacker/jira-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sorenwacker/jira-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/sorenwacker/jira-cli)

CLI tool for managing Jira Cloud issues from the terminal.

## Installation

```bash
uv pip install -e .
```

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
```

Edit issue:

```bash
jira issue edit PROJ-123 --summary "New title" --priority High
```

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

## Development

```bash
uv pip install -e ".[dev]"
pytest
```
