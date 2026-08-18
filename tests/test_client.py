"""Tests for Jira API client."""

import json

import httpx
import pytest
import respx

from jira_cli.client import (
    IssueCreateParams,
    IssueUpdateParams,
    JiraClient,
    UserSearchParams,
)
from jira_cli.config import JiraConfig


class TestJiraClientSearch:
    """Tests for issue search functionality."""

    @respx.mock
    def test_get_my_issues(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Can retrieve issues assigned to current user."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        issues = jira_client.get_my_issues()

        assert len(issues) == 1
        assert issues[0].key == "PROJ-123"
        body = json.loads(route.calls[0].request.content)
        assert "assignee = currentUser()" in body["jql"]
        for field in ("components", "fixVersions", "duedate"):
            assert field in body["fields"]

    @respx.mock
    def test_search_follows_next_page_token(
        self, jira_client: JiraClient, sample_search_response: dict
    ) -> None:
        """Search pages over nextPageToken until the last page."""
        first = {**sample_search_response, "nextPageToken": "tok", "isLast": False}
        last = {**sample_search_response, "isLast": True}
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            side_effect=[
                httpx.Response(200, json=first),
                httpx.Response(200, json=last),
            ]
        )
        issues = jira_client.search("project = PROJ", limit=50)
        assert len(issues) == 2
        assert route.call_count == 2
        assert json.loads(route.calls[1].request.content)["nextPageToken"] == "tok"

    @respx.mock
    def test_get_my_issues_with_status_filter(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Can filter issues by status."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        issues = jira_client.get_my_issues(status="In Progress")

        assert len(issues) == 1
        body = json.loads(route.calls[0].request.content)
        assert 'status = "In Progress"' in body["jql"]

    @respx.mock
    def test_get_my_issues_with_project_filter(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Can filter issues by project."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        issues = jira_client.get_my_issues(project="PROJ")

        assert len(issues) == 1
        body = json.loads(route.calls[0].request.content)
        assert "project = PROJ" in body["jql"]

    @respx.mock
    def test_get_my_issues_with_limit(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Can limit number of results."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        jira_client.get_my_issues(limit=5)

        body = json.loads(route.calls[0].request.content)
        assert body["maxResults"] == 5


class TestJiraClientGetIssue:
    """Tests for getting single issue."""

    @respx.mock
    def test_get_issue(
        self,
        jira_client: JiraClient,
        sample_issue_response: dict,
    ) -> None:
        """Can retrieve a single issue by key."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(200, json=sample_issue_response)
        )

        issue = jira_client.get_issue("PROJ-123")

        assert issue.key == "PROJ-123"
        assert issue.summary == "Test issue summary"

    @respx.mock
    def test_get_issue_not_found(self, jira_client: JiraClient) -> None:
        """Raises error for non-existent issue."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-999").mock(
            return_value=httpx.Response(
                404, json={"errorMessages": ["Issue not found"]}
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            jira_client.get_issue("PROJ-999")


class TestJiraClientTransitions:
    """Tests for status transition functionality."""

    @respx.mock
    def test_get_transitions(
        self,
        jira_client: JiraClient,
        sample_transitions_response: dict,
    ) -> None:
        """Can retrieve available transitions for an issue."""
        respx.get(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
        ).mock(return_value=httpx.Response(200, json=sample_transitions_response))

        transitions = jira_client.get_transitions("PROJ-123")

        assert len(transitions) == 3
        assert transitions[1].name == "In Progress"

    @respx.mock
    def test_transition_issue(
        self,
        jira_client: JiraClient,
        sample_transitions_response: dict,
    ) -> None:
        """Can transition an issue to a new status."""
        respx.get(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
        ).mock(return_value=httpx.Response(200, json=sample_transitions_response))
        respx.post(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
        ).mock(return_value=httpx.Response(204))

        result = jira_client.transition_issue("PROJ-123", "In Progress")

        assert result is True

    @respx.mock
    def test_transition_issue_invalid_status(
        self,
        jira_client: JiraClient,
        sample_transitions_response: dict,
    ) -> None:
        """Raises error for invalid transition."""
        respx.get(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
        ).mock(return_value=httpx.Response(200, json=sample_transitions_response))

        with pytest.raises(ValueError, match="Invalid transition"):
            jira_client.transition_issue("PROJ-123", "Invalid Status")


class TestJiraClientCreateIssue:
    """Tests for issue creation."""

    @respx.mock
    def test_create_issue(self, jira_client: JiraClient) -> None:
        """Can create a new issue."""
        respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10001",
                    "key": "PROJ-124",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10001",
                },
            )
        )

        params = IssueCreateParams(
            project="PROJ",
            summary="New issue",
            issue_type="Task",
            description="Issue description",
        )
        issue_key = jira_client.create_issue(params)

        assert issue_key == "PROJ-124"

    @respx.mock
    def test_create_issue_minimal(self, jira_client: JiraClient) -> None:
        """Can create issue with minimal fields."""
        route = respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10001",
                    "key": "PROJ-125",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10001",
                },
            )
        )

        params = IssueCreateParams(
            project="PROJ",
            summary="Minimal issue",
            issue_type="Task",
        )
        issue_key = jira_client.create_issue(params)

        assert issue_key == "PROJ-125"
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["project"]["key"] == "PROJ"
        assert body["fields"]["summary"] == "Minimal issue"
        assert body["fields"]["issuetype"]["name"] == "Task"

    @respx.mock
    def test_create_issue_with_metadata_fields(self, jira_client: JiraClient) -> None:
        """Create sends reporter, components, fix versions, and due date."""
        route = respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10001",
                    "key": "PROJ-128",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10001",
                },
            )
        )

        params = IssueCreateParams(
            project="PROJ",
            summary="Full metadata",
            reporter="account-123",
            components=["API", "UI"],
            fix_versions=["1.2.0"],
            due_date="2024-02-01",
        )
        jira_client.create_issue(params)

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["reporter"]["id"] == "account-123"
        assert body["fields"]["components"] == [{"name": "API"}, {"name": "UI"}]
        assert body["fields"]["fixVersions"] == [{"name": "1.2.0"}]
        assert body["fields"]["duedate"] == "2024-02-01"

    @respx.mock
    def test_create_subtask(self, jira_client: JiraClient) -> None:
        """Can create a subtask under a parent issue."""
        route = respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10002",
                    "key": "PROJ-126",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10002",
                },
            )
        )

        params = IssueCreateParams(
            project="PROJ",
            summary="Subtask summary",
            issue_type="Sub-task",
            parent="PROJ-123",
        )
        issue_key = jira_client.create_issue(params)

        assert issue_key == "PROJ-126"
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["parent"]["key"] == "PROJ-123"
        assert body["fields"]["issuetype"]["name"] == "Sub-task"

    @respx.mock
    def test_create_subtask_with_description(self, jira_client: JiraClient) -> None:
        """Can create a subtask with description."""
        route = respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10003",
                    "key": "PROJ-127",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10003",
                },
            )
        )

        params = IssueCreateParams(
            project="PROJ",
            summary="Subtask with details",
            issue_type="Sub-task",
            description="Subtask description",
            parent="PROJ-123",
        )
        issue_key = jira_client.create_issue(params)

        assert issue_key == "PROJ-127"
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["parent"]["key"] == "PROJ-123"
        assert "description" in body["fields"]


class TestJiraClientUpdateIssue:
    """Tests for issue updates."""

    @respx.mock
    def test_update_summary(self, jira_client: JiraClient) -> None:
        """Can update issue summary."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        params = IssueUpdateParams(summary="Updated summary")
        result = jira_client.update_issue("PROJ-123", params)
        assert result is True
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["summary"] == "Updated summary"

    def test_update_issue_returns_false_when_no_fields(
        self, jira_client: JiraClient
    ) -> None:
        """An update with no fields reports no change and sends no request."""
        assert jira_client.update_issue("PROJ-123", IssueUpdateParams()) is False

    @respx.mock
    def test_update_priority(self, jira_client: JiraClient) -> None:
        """Can update issue priority."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        params = IssueUpdateParams(priority="High")
        jira_client.update_issue("PROJ-123", params)

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["priority"]["name"] == "High"

    @respx.mock
    def test_update_assignee(self, jira_client: JiraClient) -> None:
        """Can update issue assignee."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        params = IssueUpdateParams(assignee="user@example.com")
        jira_client.update_issue("PROJ-123", params)

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["assignee"]["id"] == "user@example.com"

    @respx.mock
    def test_update_labels(self, jira_client: JiraClient) -> None:
        """Can update issue labels."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        params = IssueUpdateParams(labels=["bug", "urgent"])
        jira_client.update_issue("PROJ-123", params)

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["labels"] == ["bug", "urgent"]

    @respx.mock
    def test_update_metadata_fields(self, jira_client: JiraClient) -> None:
        """Update sends reporter, components, fix versions, and due date."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        params = IssueUpdateParams(
            reporter="account-123",
            components=["API"],
            fix_versions=["1.2.0", "1.3.0"],
            due_date="2024-02-01",
        )
        result = jira_client.update_issue("PROJ-123", params)

        assert result is True
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["reporter"]["id"] == "account-123"
        assert body["fields"]["components"] == [{"name": "API"}]
        assert body["fields"]["fixVersions"] == [
            {"name": "1.2.0"},
            {"name": "1.3.0"},
        ]
        assert body["fields"]["duedate"] == "2024-02-01"


class TestJiraClientCustomSearch:
    """Tests for custom JQL search."""

    @respx.mock
    def test_search_jql(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Can search with custom JQL."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        issues = jira_client.search("project = PROJ AND status = Open")

        assert len(issues) == 1
        body = json.loads(route.calls[0].request.content)
        assert body["jql"] == "project = PROJ AND status = Open"


class TestJiraClientWatch:
    """Tests for watch/unwatch functionality."""

    @respx.mock
    def test_watch_issue(self, jira_client: JiraClient) -> None:
        """Can watch an issue."""
        route = respx.post(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/watchers"
        ).mock(return_value=httpx.Response(204))

        jira_client.watch_issue("PROJ-123")

        assert route.called

    @respx.mock
    def test_unwatch_issue(
        self,
        jira_client: JiraClient,
        jira_config: JiraConfig,  # noqa: ARG002
    ) -> None:
        """Can unwatch an issue."""
        respx.get("https://test.atlassian.net/rest/api/3/myself").mock(
            return_value=httpx.Response(200, json={"accountId": "abc123"})
        )
        route = respx.delete(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/watchers"
        ).mock(return_value=httpx.Response(204))

        jira_client.unwatch_issue("PROJ-123")

        assert route.called


class TestJiraClientDeleteComment:
    """Tests for comment deletion."""

    @respx.mock
    def test_delete_comment(self, jira_client: JiraClient) -> None:
        """Can delete a comment."""
        route = respx.delete(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment/10001"
        ).mock(return_value=httpx.Response(204))

        jira_client.delete_comment("PROJ-123", "10001")

        assert route.called


class TestJiraClientDeleteIssue:
    """Tests for issue deletion."""

    @respx.mock
    def test_delete_issue(self, jira_client: JiraClient) -> None:
        """Can delete an issue."""
        route = respx.delete(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123"
        ).mock(return_value=httpx.Response(204))

        jira_client.delete_issue("PROJ-123")

        assert route.called


class TestJiraClientAuth:
    """Tests for authentication."""

    @respx.mock
    def test_auth_header_is_set(
        self,
        jira_client: JiraClient,
        sample_search_response: dict,
    ) -> None:
        """Requests include Basic auth header."""
        route = respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(200, json=sample_search_response)
        )

        jira_client.get_my_issues()

        auth_header = route.calls[0].request.headers.get("Authorization")
        assert auth_header is not None
        assert auth_header.startswith("Basic ")

    @respx.mock
    def test_unauthorized_raises_error(self, jira_client: JiraClient) -> None:
        """Unauthorized response raises error."""
        respx.post("https://test.atlassian.net/rest/api/3/search/jql").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            jira_client.get_my_issues()


class TestJiraClientProjects:
    """Tests for project listing functionality."""

    @respx.mock
    def test_get_projects(
        self,
        jira_client: JiraClient,
        sample_projects_response: list[dict],
    ) -> None:
        """Can retrieve projects."""
        respx.get("https://test.atlassian.net/rest/api/3/project").mock(
            return_value=httpx.Response(200, json=sample_projects_response)
        )

        projects = jira_client.get_projects()

        assert len(projects) == 2
        assert projects[0].key == "DAT"
        assert projects[0].name == "Data Project"
        assert projects[0].project_type == "software"


class TestJiraClientUsers:
    """Tests for user search functionality."""

    @respx.mock
    def test_get_users_filters_apps_and_no_email_by_default(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Filters out app accounts and users without emails by default."""
        respx.get("https://test.atlassian.net/rest/api/3/users/search").mock(
            return_value=httpx.Response(200, json=sample_users_response)
        )

        params = UserSearchParams()
        users = jira_client.get_users(params)

        assert len(users) == 2
        assert all(u.account_type == "atlassian" for u in users)
        assert all(u.email is not None for u in users)
        assert users[0].account_id == "abc123"
        assert users[0].display_name == "John Doe"

    @respx.mock
    def test_get_users_include_apps(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Can include app accounts and users without emails when requested."""
        respx.get("https://test.atlassian.net/rest/api/3/users/search").mock(
            return_value=httpx.Response(200, json=sample_users_response)
        )

        params = UserSearchParams(include_apps=True)
        users = jira_client.get_users(params)

        assert len(users) == 4
        assert any(u.account_type == "app" for u in users)
        assert any(u.email is None for u in users)

    @respx.mock
    def test_get_users_with_query(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Can search users with query string."""
        route = respx.get("https://test.atlassian.net/rest/api/3/users/search").mock(
            return_value=httpx.Response(200, json=sample_users_response)
        )

        params = UserSearchParams(query="john")
        jira_client.get_users(params)

        assert "query=john" in str(route.calls[0].request.url)

    @respx.mock
    def test_get_users_with_limit(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Can limit number of user results."""
        route = respx.get("https://test.atlassian.net/rest/api/3/users/search").mock(
            return_value=httpx.Response(200, json=sample_users_response)
        )

        params = UserSearchParams(limit=10)
        jira_client.get_users(params)

        assert "maxResults=10" in str(route.calls[0].request.url)

    @respx.mock
    def test_get_users_assignable_for_project(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Can get assignable users for a project."""
        route = respx.get(
            "https://test.atlassian.net/rest/api/3/user/assignable/search"
        ).mock(return_value=httpx.Response(200, json=sample_users_response))

        params = UserSearchParams(project="PROJ")
        users = jira_client.get_users(params)

        assert route.called
        assert "project=PROJ" in str(route.calls[0].request.url)
        assert len(users) == 4
