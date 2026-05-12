"""Jira API client."""

import base64

import httpx

from jira_cli.config import JiraConfig
from jira_cli.models import Comment, Issue, Transition


class JiraClient:
    """Client for interacting with Jira Cloud REST API."""

    def __init__(self, config: JiraConfig) -> None:
        """Initialize the Jira client.

        Args:
            config: Jira connection configuration.
        """
        self.config = config
        self._client = httpx.Client(
            base_url=config.url,
            headers=self._build_headers(),
            timeout=30.0,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        credentials = f"{self.config.email}:{self.config.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_my_issues(
        self,
        status: str | None = None,
        project: str | None = None,
        limit: int = 50,
    ) -> list[Issue]:
        """Get issues assigned to the current user.

        Args:
            status: Filter by status name (e.g., "In Progress").
            project: Filter by project key (e.g., "PROJ").
            limit: Maximum number of results.

        Returns:
            List of Issue objects.
        """
        # Build JQL query
        jql_parts = ["assignee = currentUser()"]

        if status:
            jql_parts.append(f'status = "{status}"')

        if project:
            jql_parts.append(f"project = {project}")

        jql = " AND ".join(jql_parts)

        # Build request body (POST required for Jira Cloud search)
        body = {
            "jql": jql,
            "maxResults": limit,
            "fields": [
                "summary",
                "status",
                "assignee",
                "project",
                "priority",
                "created",
                "updated",
                "description",
                "attachment",
            ],
        }

        response = self._client.post("/rest/api/3/search/jql", json=body)
        response.raise_for_status()

        data = response.json()
        return [Issue.from_api_response(issue) for issue in data["issues"]]

    def get_issue(self, issue_key: str) -> Issue:
        """Get a single issue by key.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").

        Returns:
            Issue object.

        Raises:
            httpx.HTTPStatusError: If the issue is not found.
        """
        response = self._client.get(f"/rest/api/3/issue/{issue_key}")
        response.raise_for_status()

        return Issue.from_api_response(response.json())

    def get_comments(self, issue_key: str) -> list[Comment]:
        """Get comments for an issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").

        Returns:
            List of Comment objects.
        """
        response = self._client.get(f"/rest/api/3/issue/{issue_key}/comment")
        response.raise_for_status()

        data = response.json()
        return [Comment.from_api_response(c) for c in data["comments"]]

    def add_comment(self, issue_key: str, body: str) -> Comment:
        """Add a comment to an issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            body: The comment text.

        Returns:
            The created Comment object.
        """
        # Jira Cloud uses Atlassian Document Format (ADF)
        adf_body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }

        response = self._client.post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json=adf_body,
        )
        response.raise_for_status()

        return Comment.from_api_response(response.json())

    def update_comment(self, issue_key: str, comment_id: str, body: str) -> None:
        """Update an existing comment.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            comment_id: The comment ID.
            body: The new comment text.
        """
        adf_body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }

        response = self._client.put(
            f"/rest/api/3/issue/{issue_key}/comment/{comment_id}",
            json=adf_body,
        )
        response.raise_for_status()

    def get_transitions(self, issue_key: str) -> list[Transition]:
        """Get available transitions for an issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").

        Returns:
            List of available Transition objects.
        """
        response = self._client.get(f"/rest/api/3/issue/{issue_key}/transitions")
        response.raise_for_status()

        data = response.json()
        return [Transition.from_api_response(t) for t in data["transitions"]]

    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition an issue to a new status.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            transition_name: The name of the target transition/status.

        Returns:
            True if successful.

        Raises:
            ValueError: If the transition name is not valid.
        """
        # Get available transitions
        transitions = self.get_transitions(issue_key)

        # Find matching transition
        transition = None
        for t in transitions:
            if t.name.lower() == transition_name.lower():
                transition = t
                break

        if transition is None:
            available = [t.name for t in transitions]
            raise ValueError(
                f"Invalid transition '{transition_name}'. " f"Available: {', '.join(available)}"
            )

        # Perform transition
        response = self._client.post(
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition.id}},
        )
        response.raise_for_status()

        return True

    def create_issue(
        self,
        project: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> str:
        """Create a new issue.

        Args:
            project: Project key (e.g., "PROJ").
            summary: Issue summary/title.
            issue_type: Issue type (e.g., "Task", "Bug", "Story").
            description: Issue description (optional).
            priority: Priority name (optional).
            labels: List of labels (optional).
            assignee: Assignee account ID or email (optional).

        Returns:
            The created issue key (e.g., "PROJ-123").
        """
        fields: dict = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

        if priority:
            fields["priority"] = {"name": priority}

        if labels:
            fields["labels"] = labels

        if assignee:
            fields["assignee"] = {"id": assignee}

        response = self._client.post("/rest/api/3/issue", json={"fields": fields})
        response.raise_for_status()

        return response.json()["key"]

    def update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> None:
        """Update an issue's fields.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            summary: New summary (optional).
            description: New description (optional).
            priority: New priority name (optional).
            labels: New labels list (optional).
            assignee: New assignee account ID (optional).
        """
        fields: dict = {}

        if summary is not None:
            fields["summary"] = summary

        if description is not None:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

        if priority is not None:
            fields["priority"] = {"name": priority}

        if labels is not None:
            fields["labels"] = labels

        if assignee is not None:
            fields["assignee"] = {"id": assignee}

        if not fields:
            return

        response = self._client.put(
            f"/rest/api/3/issue/{issue_key}",
            json={"fields": fields},
        )
        response.raise_for_status()

    def search(self, jql: str, limit: int = 50) -> list[Issue]:
        """Search issues with custom JQL.

        Args:
            jql: JQL query string.
            limit: Maximum number of results.

        Returns:
            List of Issue objects.
        """
        body = {
            "jql": jql,
            "maxResults": limit,
            "fields": [
                "summary",
                "status",
                "assignee",
                "project",
                "priority",
                "created",
                "updated",
                "description",
                "attachment",
            ],
        }

        response = self._client.post("/rest/api/3/search/jql", json=body)
        response.raise_for_status()

        data = response.json()
        return [Issue.from_api_response(issue) for issue in data["issues"]]

    def watch_issue(self, issue_key: str) -> None:
        """Add current user as watcher.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
        """
        response = self._client.post(f"/rest/api/3/issue/{issue_key}/watchers")
        response.raise_for_status()

    def unwatch_issue(self, issue_key: str) -> None:
        """Remove current user as watcher.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
        """
        # Get current user's account ID
        me_response = self._client.get("/rest/api/3/myself")
        me_response.raise_for_status()
        account_id = me_response.json()["accountId"]

        response = self._client.delete(
            f"/rest/api/3/issue/{issue_key}/watchers",
            params={"accountId": account_id},
        )
        response.raise_for_status()

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            comment_id: The comment ID.
        """
        response = self._client.delete(f"/rest/api/3/issue/{issue_key}/comment/{comment_id}")
        response.raise_for_status()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "JiraClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
