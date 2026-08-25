"""MCP server exposing Jira operations as tools."""

from typing import Any

import httpx
from fastmcp import FastMCP

from jira_cli.client import (
    IssueCreateParams,
    IssueUpdateParams,
    JiraClient,
    UserSearchParams,
)
from jira_cli.config import load_config, load_writing_guidance
from jira_cli.confluence_mcp import register as register_confluence_tools
from jira_cli.models import Issue, IssueType, Status
from jira_cli.quality import generate_quality_report

__all__ = ["main", "mcp"]

DEFAULT_WRITING_GUIDANCE = (
    "Jira issue descriptions and Confluence pages must be written in plain "
    "English prose. Do not use markdown tables; Jira does not render them and "
    "the Confluence converter leaves them as literal text. "
    "Structure every issue description with these sections: "
    "Context, Goal, Scope, Acceptance criteria."
)

_INSTANCE_METADATA_UNAVAILABLE = (
    "The instance's ticket statuses and issue types could not be fetched at "
    "startup; use get_transitions to discover valid statuses for an issue."
)

mcp = FastMCP("Jira", instructions=DEFAULT_WRITING_GUIDANCE)


def _dedup(names: list[str]) -> list[str]:
    """Drop duplicate names while preserving order."""
    return list(dict.fromkeys(names))


def _format_statuses(statuses: list["Status"]) -> str:
    """Format statuses grouped by category, one category per line."""
    by_category: dict[str, list[str]] = {}
    for status in statuses:
        by_category.setdefault(status.category, []).append(status.name)
    return "\n".join(
        f"{category}: {', '.join(_dedup(names))}"
        for category, names in by_category.items()
    )


def _format_issue_types(issue_types: list["IssueType"]) -> str:
    """Format issue types with subtask types listed separately."""
    regular = _dedup([t.name for t in issue_types if not t.subtask])
    subtask = _dedup([t.name for t in issue_types if t.subtask])
    text = ", ".join(regular)
    if subtask:
        text += f". Subtask types: {', '.join(subtask)}"
    return text


def build_instructions() -> str:
    """Build server instructions including the instance's statuses and issue types."""
    guidance = load_writing_guidance() or DEFAULT_WRITING_GUIDANCE
    try:
        with get_client() as client:
            statuses = client.get_statuses()
            issue_types = client.get_issue_types()
    except (httpx.HTTPError, ValueError):
        return f"{guidance}\n\n{_INSTANCE_METADATA_UNAVAILABLE}"
    return (
        f"{guidance}\n\n"
        "Ticket statuses defined in this Jira instance, grouped by category; "
        "pass the exact status name to transition_issue:\n"
        f"{_format_statuses(statuses)}\n\n"
        "Issue types defined in this instance; pass the exact name as "
        f"issue_type to create_issue: {_format_issue_types(issue_types)}"
    )


def _issue_to_dict(issue: Issue, *, full: bool = False) -> dict[str, Any]:
    """Convert Issue to dictionary for MCP response."""
    result: dict[str, Any] = {
        "key": issue.key,
        "summary": issue.summary,
        "status": issue.status,
        "assignee": issue.assignee,
        "priority": issue.priority,
    }
    if full:
        result.update(
            {
                "reporter": issue.reporter,
                "project": issue.project,
                "description": issue.description,
                "created": issue.created.isoformat(),
                "updated": issue.updated.isoformat(),
                "due_date": issue.due_date.isoformat() if issue.due_date else None,
                "labels": issue.labels,
                "components": issue.components,
                "fix_versions": issue.fix_versions,
                "attachments": [a.model_dump(mode="json") for a in issue.attachments],
            }
        )
    return result


def get_client() -> JiraClient:
    """Get a configured Jira client."""
    return JiraClient(load_config())


@mcp.tool()
def get_issue(issue_key: str) -> dict[str, Any]:
    """Get issue details by key.

    Args:
        issue_key: The issue key (e.g., PROJ-123).

    Returns:
        Issue details including summary, status, assignee, and description.
    """
    with get_client() as client:
        issue = client.get_issue(issue_key)
        return _issue_to_dict(issue, full=True)


@mcp.tool()
def search_issues(jql: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search issues using JQL.

    Args:
        jql: JQL query string (e.g., "project = PROJ AND status = Open").
        limit: Maximum number of results (default 50).

    Returns:
        List of matching issues.
    """
    with get_client() as client:
        issues = client.search(jql, limit=limit)
        return [_issue_to_dict(issue) for issue in issues]


@mcp.tool()
def get_my_issues(
    status: str | None = None,
    project: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get issues assigned to current user.

    Args:
        status: Filter by status name (e.g., "In Progress").
        project: Filter by project key (e.g., "PROJ").
        limit: Maximum number of results (default 50).

    Returns:
        List of assigned issues.
    """
    with get_client() as client:
        issues = client.get_my_issues(status=status, project=project, limit=limit)
        return [_issue_to_dict(issue) for issue in issues]


@mcp.tool()
def create_issue(
    project: str,
    summary: str,
    issue_type: str = "Task",
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    parent: str | None = None,
    reporter: str | None = None,
    components: list[str] | None = None,
    fix_versions: list[str] | None = None,
    due_date: str | None = None,
) -> dict[str, str]:
    """Create a new issue or subtask.

    Write the description following the writing conventions stated in the
    server instructions. Jira never renders markdown tables.

    Args:
        project: Project key (e.g., "PROJ").
        summary: Issue summary/title.
        issue_type: Issue type (e.g., "Task", "Bug", "Story", "Sub-task").
        description: Issue description.
        priority: Priority name (e.g., "High", "Medium", "Low").
        labels: List of labels.
        parent: Parent issue key for subtasks (e.g., "PROJ-123").
        reporter: Reporter account ID (requires Modify Reporter permission).
        components: Component names; must already exist in the project.
        fix_versions: Fix version names; must already exist in the project.
        due_date: Due date in YYYY-MM-DD format.

    Returns:
        Created issue key.
    """
    params = IssueCreateParams(
        project=project,
        summary=summary,
        issue_type=issue_type,
        description=description,
        priority=priority,
        labels=labels,
        parent=parent,
        reporter=reporter,
        components=components,
        fix_versions=fix_versions,
        due_date=due_date,
    )
    with get_client() as client:
        issue_key = client.create_issue(params)
        return {"key": issue_key}


@mcp.tool()
def update_issue(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    assignee: str | None = None,
    reporter: str | None = None,
    components: list[str] | None = None,
    fix_versions: list[str] | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Update an issue's fields.

    Write the description following the writing conventions stated in the
    server instructions. Jira never renders markdown tables.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").
        summary: New summary.
        description: New description.
        priority: New priority name.
        labels: New labels list.
        assignee: New assignee account ID.
        reporter: New reporter account ID (requires Modify Reporter permission).
        components: New component names; replaces the current list.
        fix_versions: New fix version names; replaces the current list.
        due_date: New due date in YYYY-MM-DD format.

    Returns:
        Success status.
    """
    params = IssueUpdateParams(
        summary=summary,
        description=description,
        priority=priority,
        labels=labels,
        assignee=assignee,
        reporter=reporter,
        components=components,
        fix_versions=fix_versions,
        due_date=due_date,
    )
    with get_client() as client:
        updated = client.update_issue(issue_key, params)
        return {"success": True, "updated": updated, "issue_key": issue_key}


@mcp.tool()
def get_transitions(issue_key: str) -> list[dict[str, str]]:
    """Get available status transitions for an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        List of available transitions.
    """
    with get_client() as client:
        transitions = client.get_transitions(issue_key)
        return [{"id": t.id, "name": t.name} for t in transitions]


@mcp.tool()
def transition_issue(issue_key: str, transition_name: str) -> dict[str, Any]:
    """Change an issue's status.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").
        transition_name: The target status name (e.g., "In Progress", "Done").

    Returns:
        Success status.
    """
    with get_client() as client:
        client.transition_issue(issue_key, transition_name)
        return {"success": True, "issue_key": issue_key, "new_status": transition_name}


@mcp.tool()
def get_comments(issue_key: str) -> list[dict[str, Any]]:
    """Get comments for an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        List of comments.
    """
    with get_client() as client:
        comments = client.get_comments(issue_key)
        return [
            {
                "id": c.id,
                "author": c.author,
                "body": c.body,
                "created": c.created.isoformat(),
            }
            for c in comments
        ]


@mcp.tool()
def add_comment(issue_key: str, body: str) -> dict[str, Any]:
    """Add a comment to an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").
        body: The comment text.

    Returns:
        Created comment details.
    """
    with get_client() as client:
        comment = client.add_comment(issue_key, body)
        return {
            "id": comment.id,
            "author": comment.author,
            "body": comment.body,
            "created": comment.created.isoformat(),
        }


@mcp.tool()
def update_comment(issue_key: str, comment_id: str, body: str) -> dict[str, Any]:
    """Replace the body of an existing comment.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").
        comment_id: The comment ID as returned by get_comments.
        body: The new comment text; replaces the previous body entirely.

    Returns:
        Success status.
    """
    with get_client() as client:
        client.update_comment(issue_key, comment_id, body)
        return {"success": True, "issue_key": issue_key, "comment_id": comment_id}


@mcp.tool()
def get_projects() -> list[dict[str, str]]:
    """Get all projects visible to the current user.

    Returns:
        List of projects with key, name, and type.
    """
    with get_client() as client:
        projects = client.get_projects()
        return [
            {"key": p.key, "name": p.name, "project_type": p.project_type}
            for p in projects
        ]


@mcp.tool()
def get_users(
    query: str | None = None,
    project: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search for users.

    Args:
        query: Search string to filter by name or email.
        project: Project key to get assignable users for.
        limit: Maximum number of results (default 50).

    Returns:
        List of users.
    """
    params = UserSearchParams(query=query, project=project, limit=limit)
    with get_client() as client:
        users = client.get_users(params)
        return [
            {
                "account_id": u.account_id,
                "display_name": u.display_name,
                "email": u.email,
                "active": u.active,
            }
            for u in users
        ]


@mcp.tool()
def watch_issue(issue_key: str) -> dict[str, Any]:
    """Start watching an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        Success status.
    """
    with get_client() as client:
        client.watch_issue(issue_key)
        return {"success": True, "issue_key": issue_key, "watching": True}


@mcp.tool()
def unwatch_issue(issue_key: str) -> dict[str, Any]:
    """Stop watching an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        Success status.
    """
    with get_client() as client:
        client.unwatch_issue(issue_key)
        return {"success": True, "issue_key": issue_key, "watching": False}


@mcp.tool()
def delete_issue(issue_key: str) -> dict[str, Any]:
    """Delete an issue permanently.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        Success status.
    """
    with get_client() as client:
        client.delete_issue(issue_key)
        return {"success": True, "issue_key": issue_key, "deleted": True}


@mcp.tool()
def get_issue_quality_report(
    project: str | None = None,
    status: str | None = None,
    jql: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Generate issue quality report with ratings.

    Analyzes issues and scores them on a 1-10 scale based on:
    - Description quality (3 pts)
    - Labels (2 pts)
    - Assignee (2 pts)
    - Priority (1 pt)
    - Attachments (1 pt)
    - Recent activity (1 pt)

    Args:
        project: Filter by project key (e.g., "PROJ").
        status: Filter by status name (e.g., "In Progress").
        jql: Custom JQL query. If provided, project and status are ignored.
        limit: Maximum number of issues to analyze (default 50).

    Returns:
        List of issues with quality ratings.
    """
    with get_client() as client:
        if jql:
            issues = client.search(jql, limit=limit)
        else:
            jql_parts = []
            if project:
                jql_parts.append(f"project = {project}")
            if status:
                jql_parts.append(f'status = "{status}"')
            query = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"
            issues = client.search(query, limit=limit)

        return generate_quality_report(issues)


register_confluence_tools(mcp)


def main() -> None:
    """Entry point for MCP server."""
    mcp.instructions = build_instructions()
    mcp.run()


if __name__ == "__main__":
    main()
