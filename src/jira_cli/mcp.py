"""MCP server exposing Jira operations as tools."""

from fastmcp import FastMCP

from jira_cli.client import JiraClient
from jira_cli.config import load_config

mcp = FastMCP("Jira")


def get_client() -> JiraClient:
    """Get a configured Jira client."""
    return JiraClient(load_config())


@mcp.tool()
def get_issue(issue_key: str) -> dict:
    """Get issue details by key.

    Args:
        issue_key: The issue key (e.g., PROJ-123).

    Returns:
        Issue details including summary, status, assignee, and description.
    """
    with get_client() as client:
        issue = client.get_issue(issue_key)
        return {
            "key": issue.key,
            "summary": issue.summary,
            "status": issue.status,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "project": issue.project,
            "priority": issue.priority,
            "description": issue.description,
            "created": issue.created.isoformat(),
            "updated": issue.updated.isoformat(),
        }


@mcp.tool()
def search_issues(jql: str, limit: int = 50) -> list[dict]:
    """Search issues using JQL.

    Args:
        jql: JQL query string (e.g., "project = PROJ AND status = Open").
        limit: Maximum number of results (default 50).

    Returns:
        List of matching issues.
    """
    with get_client() as client:
        issues = client.search(jql, limit=limit)
        return [
            {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status,
                "assignee": issue.assignee,
                "priority": issue.priority,
            }
            for issue in issues
        ]


@mcp.tool()
def get_my_issues(
    status: str | None = None,
    project: str | None = None,
    limit: int = 50,
) -> list[dict]:
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
        return [
            {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status,
                "priority": issue.priority,
            }
            for issue in issues
        ]


@mcp.tool()
def create_issue(
    project: str,
    summary: str,
    issue_type: str = "Task",
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    parent: str | None = None,
) -> dict:
    """Create a new issue or subtask.

    Args:
        project: Project key (e.g., "PROJ").
        summary: Issue summary/title.
        issue_type: Issue type (e.g., "Task", "Bug", "Story", "Sub-task").
        description: Issue description.
        priority: Priority name (e.g., "High", "Medium", "Low").
        labels: List of labels.
        parent: Parent issue key for subtasks (e.g., "PROJ-123").

    Returns:
        Created issue key.
    """
    with get_client() as client:
        issue_key = client.create_issue(
            project=project,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            labels=labels,
            parent=parent,
        )
        return {"key": issue_key}


@mcp.tool()
def update_issue(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    assignee: str | None = None,
) -> dict:
    """Update an issue's fields.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").
        summary: New summary.
        description: New description.
        priority: New priority name.
        labels: New labels list.
        assignee: New assignee account ID.

    Returns:
        Success status.
    """
    with get_client() as client:
        client.update_issue(
            issue_key,
            summary=summary,
            description=description,
            priority=priority,
            labels=labels,
            assignee=assignee,
        )
        return {"success": True, "issue_key": issue_key}


@mcp.tool()
def get_transitions(issue_key: str) -> list[dict]:
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
def transition_issue(issue_key: str, transition_name: str) -> dict:
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
def get_comments(issue_key: str) -> list[dict]:
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
def add_comment(issue_key: str, body: str) -> dict:
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
def get_projects() -> list[dict]:
    """Get all projects visible to the current user.

    Returns:
        List of projects with key, name, and type.
    """
    with get_client() as client:
        projects = client.get_projects()
        return [
            {
                "key": p.key,
                "name": p.name,
                "project_type": p.project_type,
            }
            for p in projects
        ]


@mcp.tool()
def get_users(
    query: str | None = None,
    project: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search for users.

    Args:
        query: Search string to filter by name or email.
        project: Project key to get assignable users for.
        limit: Maximum number of results (default 50).

    Returns:
        List of users.
    """
    with get_client() as client:
        users = client.get_users(query=query, project=project, limit=limit)
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
def watch_issue(issue_key: str) -> dict:
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
def unwatch_issue(issue_key: str) -> dict:
    """Stop watching an issue.

    Args:
        issue_key: The issue key (e.g., "PROJ-123").

    Returns:
        Success status.
    """
    with get_client() as client:
        client.unwatch_issue(issue_key)
        return {"success": True, "issue_key": issue_key, "watching": False}


def main() -> None:
    """Entry point for MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
