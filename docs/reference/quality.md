# Issue Quality Scoring

`jira issue quality` and the `get_issue_quality_report` MCP tool score each issue on a 1-10 scale. Issues are selected by `--project` and `--status` filters (combined with AND) or by an explicit `--jql` query, which overrides the filters. Without any filter the most recently created issues are analyzed, up to `--limit` (default 50).

| Criterion | Points | Condition |
|-----------|--------|-----------|
| Description | 3 | Present and longer than 50 characters (1 if present but shorter) |
| Labels | 2 | Has labels |
| Assignee | 2 | Is assigned |
| Priority | 1 | Priority set |
| Attachments | 1 | Has attachments |
| Activity | 1 | Updated in the last 30 days |

Each report row contains the key, summary, creator, age, status, and rating.
