# Jira CLI

Direct commands of the `jira` executable. Run `jira --help` or `jira issue --help` for the full option list.

## Issues

List issues assigned to you:

```bash
jira issue list
jira issue list --status "In Progress"
jira issue list --project PROJ --limit 10
```

View an issue:

```bash
jira issue view PROJ-123
jira issue view PROJ-123 --comments
```

Issue details include attachments when present:

```
Attachments:
  - screenshot.png (245 KB) - https://yourcompany.atlassian.net/...
```

Search with JQL:

```bash
jira issue search "project = PROJ AND status = Open"
```

Create an issue or subtask:

```bash
jira issue create PROJ "Issue summary" --type Bug --description "Details"
jira issue create PROJ "Issue summary" --reporter 5b10ac8d... --components "API,UI" --fix-versions "1.2.0" --due-date 2026-09-01
jira issue create-subtask PROJ-123 "Subtask summary" --type "Sub-task"
```

Edit an issue:

```bash
jira issue edit PROJ-123 --summary "New title" --priority High
jira issue edit PROJ-123 --reporter 5b10ac8d... --components "API,UI" --fix-versions "1.2.0" --due-date 2026-09-01
```

`--reporter` and `--assignee` take Jira account IDs (find them with `jira user list`). `--components` and `--fix-versions` take comma-separated names that must already exist in the project; setting them replaces the current value. `--due-date` takes a `YYYY-MM-DD` date. Setting the reporter requires the "Modify Reporter" project permission. Descriptions accept [markdown](../reference/markdown.md).

Change status:

```bash
jira issue move PROJ-123                 # list transitions
jira issue move PROJ-123 "In Progress"   # apply one
```

Watch, unwatch, delete:

```bash
jira issue watch PROJ-123
jira issue unwatch PROJ-123
jira issue delete PROJ-123
```

Quality report ([scoring](../reference/quality.md)):

```bash
jira issue quality --project PROJ --status "To Do"
jira issue quality --jql "project = PROJ AND status = Done" --limit 20
```

## Comments

```bash
jira issue comment add PROJ-123 "This is my comment"
jira issue comment edit PROJ-123 12345 "Updated comment text"
jira issue comment delete PROJ-123 12345
```

Comment IDs are shown by `jira issue view PROJ-123 --comments`.

## Users and projects

```bash
jira user list --project PROJ
jira user list --project PROJ --query "john"
jira project list
```

## See Also

- [Interactive Shell](shell.md)
- [MCP Server](mcp.md)
