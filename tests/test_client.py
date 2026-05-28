"""Tests for Jira API client."""

import json

import httpx
import pytest
import respx

from jira_cli.client import JiraClient


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
            return_value=httpx.Response(404, json={"errorMessages": ["Issue not found"]})
        )

        with pytest.raises(httpx.HTTPStatusError):
            jira_client.get_issue("PROJ-999")


class TestJiraClientComments:
    """Tests for comment functionality."""

    @respx.mock
    def test_get_comments(
        self,
        jira_client: JiraClient,
        sample_comments_response: dict,
    ) -> None:
        """Can retrieve comments for an issue."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
            return_value=httpx.Response(200, json=sample_comments_response)
        )

        comments = jira_client.get_comments("PROJ-123")

        assert len(comments) == 2
        assert comments[0].body == "First comment"

    @respx.mock
    def test_add_comment(self, jira_client: JiraClient) -> None:
        """Can add a comment to an issue."""
        respx.post("https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10003",
                    "author": {"displayName": "Test User"},
                    "body": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "New comment"}],
                            }
                        ],
                    },
                    "created": "2024-01-15T13:00:00.000+0000",
                },
            )
        )

        comment = jira_client.add_comment("PROJ-123", "New comment")

        assert comment.id == "10003"
        assert comment.body == "New comment"

    @respx.mock
    def test_update_comment(self, jira_client: JiraClient) -> None:
        """Can update an existing comment."""
        route = respx.put(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment/10001"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "10001",
                    "author": {"displayName": "Test User"},
                    "body": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Updated comment"}],
                            }
                        ],
                    },
                    "created": "2024-01-15T13:00:00.000+0000",
                },
            )
        )

        jira_client.update_comment("PROJ-123", "10001", "Updated comment")

        assert route.called


class TestJiraClientTransitions:
    """Tests for status transition functionality."""

    @respx.mock
    def test_get_transitions(
        self,
        jira_client: JiraClient,
        sample_transitions_response: dict,
    ) -> None:
        """Can retrieve available transitions for an issue."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions").mock(
            return_value=httpx.Response(200, json=sample_transitions_response)
        )

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
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions").mock(
            return_value=httpx.Response(200, json=sample_transitions_response)
        )
        respx.post("https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions").mock(
            return_value=httpx.Response(204)
        )

        result = jira_client.transition_issue("PROJ-123", "In Progress")

        assert result is True

    @respx.mock
    def test_transition_issue_invalid_status(
        self,
        jira_client: JiraClient,
        sample_transitions_response: dict,
    ) -> None:
        """Raises error for invalid transition."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123/transitions").mock(
            return_value=httpx.Response(200, json=sample_transitions_response)
        )

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

        issue_key = jira_client.create_issue(
            project="PROJ",
            summary="New issue",
            issue_type="Task",
            description="Issue description",
        )

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

        issue_key = jira_client.create_issue(
            project="PROJ",
            summary="Minimal issue",
            issue_type="Task",
        )

        assert issue_key == "PROJ-125"
        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["project"]["key"] == "PROJ"
        assert body["fields"]["summary"] == "Minimal issue"
        assert body["fields"]["issuetype"]["name"] == "Task"

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

        issue_key = jira_client.create_issue(
            project="PROJ",
            summary="Subtask summary",
            issue_type="Sub-task",
            parent="PROJ-123",
        )

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

        issue_key = jira_client.create_issue(
            project="PROJ",
            summary="Subtask with details",
            issue_type="Sub-task",
            description="Subtask description",
            parent="PROJ-123",
        )

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

        jira_client.update_issue("PROJ-123", summary="Updated summary")

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["summary"] == "Updated summary"

    @respx.mock
    def test_update_priority(self, jira_client: JiraClient) -> None:
        """Can update issue priority."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        jira_client.update_issue("PROJ-123", priority="High")

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["priority"]["name"] == "High"

    @respx.mock
    def test_update_assignee(self, jira_client: JiraClient) -> None:
        """Can update issue assignee."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        jira_client.update_issue("PROJ-123", assignee="user@example.com")

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["assignee"]["id"] == "user@example.com"

    @respx.mock
    def test_update_labels(self, jira_client: JiraClient) -> None:
        """Can update issue labels."""
        route = respx.put("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
            return_value=httpx.Response(204)
        )

        jira_client.update_issue("PROJ-123", labels=["bug", "urgent"])

        body = json.loads(route.calls[0].request.content)
        assert body["fields"]["labels"] == ["bug", "urgent"]


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
        route = respx.post("https://test.atlassian.net/rest/api/3/issue/PROJ-123/watchers").mock(
            return_value=httpx.Response(204)
        )

        jira_client.watch_issue("PROJ-123")

        assert route.called

    @respx.mock
    def test_unwatch_issue(self, jira_client: JiraClient, jira_config) -> None:
        """Can unwatch an issue."""
        # First get current user
        respx.get("https://test.atlassian.net/rest/api/3/myself").mock(
            return_value=httpx.Response(200, json={"accountId": "abc123"})
        )
        route = respx.delete("https://test.atlassian.net/rest/api/3/issue/PROJ-123/watchers").mock(
            return_value=httpx.Response(204)
        )

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

        users = jira_client.get_users()

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

        users = jira_client.get_users(include_apps=True)

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

        jira_client.get_users(query="john")

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

        jira_client.get_users(limit=10)

        assert "maxResults=10" in str(route.calls[0].request.url)

    @respx.mock
    def test_get_users_assignable_for_project(
        self,
        jira_client: JiraClient,
        sample_users_response: list[dict],
    ) -> None:
        """Can get assignable users for a project."""
        route = respx.get("https://test.atlassian.net/rest/api/3/user/assignable/search").mock(
            return_value=httpx.Response(200, json=sample_users_response)
        )

        users = jira_client.get_users(project="PROJ")

        assert route.called
        assert "project=PROJ" in str(route.calls[0].request.url)
        # Project search returns all users without filtering
        assert len(users) == 4
