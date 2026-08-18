"""Jira API client."""

import base64
from dataclasses import dataclass
from typing import Any, Self

import httpx

from jira_cli.adf import markdown_to_adf
from jira_cli.config import JiraConfig
from jira_cli.models import Comment, Issue, Project, Status, Transition, User

__all__ = [
    "IssueCreateParams",
    "IssueUpdateParams",
    "JiraClient",
    "UserSearchParams",
]

ISSUE_FIELDS = [
    "summary",
    "status",
    "assignee",
    "project",
    "priority",
    "created",
    "updated",
    "description",
    "attachment",
    "labels",
    "reporter",
    "components",
    "fixVersions",
    "duedate",
]


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
        jql = self._build_my_issues_jql(status, project)
        return self._search_issues(jql, limit)

    def _build_my_issues_jql(
        self,
        status: str | None,
        project: str | None,
    ) -> str:
        """Build JQL query for my issues."""
        jql_parts = ["assignee = currentUser()"]
        if status:
            jql_parts.append(f'status = "{status}"')
        if project:
            jql_parts.append(f"project = {project}")
        return " AND ".join(jql_parts)

    def _search_issues(self, jql: str, limit: int) -> list[Issue]:
        """Execute a JQL search, paging until the limit or last page is reached."""
        issues: list[Issue] = []
        next_token: str | None = None
        while len(issues) < limit:
            body: dict[str, Any] = {
                "jql": jql,
                "maxResults": limit - len(issues),
                "fields": ISSUE_FIELDS,
            }
            if next_token:
                body["nextPageToken"] = next_token
            response = self._client.post("/rest/api/3/search/jql", json=body)
            response.raise_for_status()
            data = response.json()
            page = data.get("issues", [])
            issues.extend(Issue.from_api_response(issue) for issue in page)
            next_token = data.get("nextPageToken")
            if not page or data.get("isLast", True) or not next_token:
                break
        return issues[:limit]

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
            body: The comment text (supports markdown formatting).

        Returns:
            The created Comment object.
        """
        response = self._client.post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json={"body": markdown_to_adf(body)},
        )
        response.raise_for_status()
        return Comment.from_api_response(response.json())

    def update_comment(self, issue_key: str, comment_id: str, body: str) -> None:
        """Update an existing comment.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            comment_id: The comment ID.
            body: The new comment text (supports markdown formatting).
        """
        response = self._client.put(
            f"/rest/api/3/issue/{issue_key}/comment/{comment_id}",
            json={"body": markdown_to_adf(body)},
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

    def get_statuses(self) -> list[Status]:
        """Get all ticket statuses defined in the Jira instance.

        Returns:
            List of Status objects.
        """
        response = self._client.get("/rest/api/3/status")
        response.raise_for_status()
        return [Status.from_api_response(s) for s in response.json()]

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
        transition = self._find_transition(issue_key, transition_name)
        self._execute_transition(issue_key, transition.id)
        return True

    def _find_transition(self, issue_key: str, name: str) -> Transition:
        """Find a transition by name."""
        transitions = self.get_transitions(issue_key)
        for t in transitions:
            if t.name.lower() == name.lower():
                return t
        available = [t.name for t in transitions]
        msg = f"Invalid transition '{name}'. Available: {', '.join(available)}"
        raise ValueError(msg)

    def _execute_transition(self, issue_key: str, transition_id: str) -> None:
        """Execute a transition on an issue."""
        response = self._client.post(
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )
        response.raise_for_status()

    def create_issue(self, params: "IssueCreateParams") -> str:
        """Create a new issue or subtask.

        Args:
            params: Issue creation parameters.

        Returns:
            The created issue key (e.g., "PROJ-123").
        """
        fields = self._build_create_fields(params)
        response = self._client.post("/rest/api/3/issue", json={"fields": fields})
        response.raise_for_status()
        key: str = response.json()["key"]
        return key

    def _build_create_fields(self, params: "IssueCreateParams") -> dict[str, Any]:
        """Build fields dict for issue creation."""
        fields: dict[str, Any] = {
            "project": {"key": params.project},
            "summary": params.summary,
            "issuetype": {"name": params.issue_type},
        }
        if params.parent:
            fields["parent"] = {"key": params.parent}
        if params.description:
            fields["description"] = markdown_to_adf(params.description)
        if params.priority:
            fields["priority"] = {"name": params.priority}
        if params.labels:
            fields["labels"] = params.labels
        if params.assignee:
            fields["assignee"] = {"id": params.assignee}
        fields.update(_build_metadata_fields(params))
        return fields

    def update_issue(self, issue_key: str, params: "IssueUpdateParams") -> bool:
        """Update an issue's fields.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            params: Issue update parameters.

        Returns:
            True if a change was sent, False if no fields were provided.
        """
        fields = self._build_update_fields(params)
        if not fields:
            return False
        response = self._client.put(
            f"/rest/api/3/issue/{issue_key}",
            json={"fields": fields},
        )
        response.raise_for_status()
        return True

    def _build_update_fields(self, params: "IssueUpdateParams") -> dict[str, Any]:
        """Build fields dict for issue update."""
        fields: dict[str, Any] = {}
        if params.summary is not None:
            fields["summary"] = params.summary
        if params.description is not None:
            fields["description"] = markdown_to_adf(params.description)
        if params.priority is not None:
            fields["priority"] = {"name": params.priority}
        if params.labels is not None:
            fields["labels"] = params.labels
        if params.assignee is not None:
            fields["assignee"] = {"id": params.assignee}
        fields.update(_build_metadata_fields(params))
        return fields

    def search(self, jql: str, limit: int = 50) -> list[Issue]:
        """Search issues with custom JQL.

        Args:
            jql: JQL query string.
            limit: Maximum number of results.

        Returns:
            List of Issue objects.
        """
        return self._search_issues(jql, limit)

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
        account_id = self._get_current_user_id()
        response = self._client.delete(
            f"/rest/api/3/issue/{issue_key}/watchers",
            params={"accountId": account_id},
        )
        response.raise_for_status()

    def _get_current_user_id(self) -> str:
        """Get the current user's account ID."""
        response = self._client.get("/rest/api/3/myself")
        response.raise_for_status()
        account_id: str = response.json()["accountId"]
        return account_id

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
            comment_id: The comment ID.
        """
        url = f"/rest/api/3/issue/{issue_key}/comment/{comment_id}"
        response = self._client.delete(url)
        response.raise_for_status()

    def delete_issue(self, issue_key: str) -> None:
        """Delete an issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123").
        """
        response = self._client.delete(f"/rest/api/3/issue/{issue_key}")
        response.raise_for_status()

    def get_users(self, params: "UserSearchParams") -> list[User]:
        """Search for users.

        Args:
            params: User search parameters.

        Returns:
            List of User objects.
        """
        all_users: list[User] = []
        start_at = 0
        page_size = min(params.limit, 1000)
        endpoint = self._get_users_endpoint(params.project)

        while len(all_users) < params.limit:
            page = self._fetch_users_page(endpoint, params, start_at, page_size)
            if not page:
                break
            users = self._filter_users(page, params)
            all_users.extend(users)
            if len(all_users) >= params.limit or len(page) < page_size:
                break
            start_at += page_size

        return all_users[: params.limit]

    def _get_users_endpoint(self, project: str | None) -> str:
        """Get the appropriate users endpoint."""
        if project:
            return "/rest/api/3/user/assignable/search"
        return "/rest/api/3/users/search"

    def _fetch_users_page(
        self,
        endpoint: str,
        params: "UserSearchParams",
        start_at: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Fetch a page of users from the API."""
        request_params: dict[str, str | int] = {
            "maxResults": page_size,
            "startAt": start_at,
        }
        if params.query:
            request_params["query"] = params.query
        if params.project:
            request_params["project"] = params.project
        response = self._client.get(endpoint, params=request_params)
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    def _filter_users(
        self,
        page_data: list[dict[str, Any]],
        params: "UserSearchParams",
    ) -> list[User]:
        """Filter and convert user data to User objects."""
        users = []
        for user_data in page_data:
            user = User.from_api_response(user_data)
            should_skip = (
                not params.project
                and not params.include_apps
                and (user.account_type != "atlassian" or not user.email)
            )
            if should_skip:
                continue
            users.append(user)
        return users

    def get_projects(self) -> list[Project]:
        """Get all projects visible to the current user.

        Returns:
            List of Project objects.
        """
        response = self._client.get("/rest/api/3/project")
        response.raise_for_status()
        return [Project.from_api_response(p) for p in response.json()]

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()


@dataclass
class IssueCreateParams:  # pylint: disable=too-many-instance-attributes
    """Parameters for creating an issue."""

    project: str
    summary: str
    issue_type: str = "Task"
    description: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    assignee: str | None = None
    parent: str | None = None
    reporter: str | None = None
    components: list[str] | None = None
    fix_versions: list[str] | None = None
    due_date: str | None = None


@dataclass
class IssueUpdateParams:  # pylint: disable=too-many-instance-attributes
    """Parameters for updating an issue."""

    summary: str | None = None
    description: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    assignee: str | None = None
    reporter: str | None = None
    components: list[str] | None = None
    fix_versions: list[str] | None = None
    due_date: str | None = None


def _build_metadata_fields(
    params: "IssueCreateParams | IssueUpdateParams",
) -> dict[str, Any]:
    """Build the metadata fields shared by issue creation and update."""
    fields: dict[str, Any] = {}
    if params.reporter is not None:
        fields["reporter"] = {"id": params.reporter}
    if params.components is not None:
        fields["components"] = [{"name": c} for c in params.components]
    if params.fix_versions is not None:
        fields["fixVersions"] = [{"name": v} for v in params.fix_versions]
    if params.due_date is not None:
        fields["duedate"] = params.due_date
    return fields


@dataclass
class UserSearchParams:
    """Parameters for searching users."""

    query: str | None = None
    project: str | None = None
    limit: int = 1000
    include_apps: bool = False
