"""Tests for MCP server tools."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from jira_cli.client import IssueCreateParams, IssueUpdateParams, UserSearchParams
from jira_cli.config import JiraConfig
from jira_cli.models import Comment, Issue, Project, Transition, User


def mock_config() -> JiraConfig:
    """Mock configuration."""
    return JiraConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
    )


def mock_issue() -> Issue:
    """Sample issue for testing."""
    return Issue(
        key="PROJ-123",
        summary="Test issue",
        status="To Do",
        assignee="Test User",
        reporter="Reporter User",
        project="PROJ",
        priority="High",
        created=datetime(2024, 1, 15, tzinfo=UTC),
        updated=datetime(2024, 1, 16, tzinfo=UTC),
        description="Test description",
        labels=["bug", "urgent"],
    )


def mock_comment() -> Comment:
    """Sample comment for testing."""
    return Comment(
        id="10001",
        author="Test User",
        body="Test comment",
        created=datetime(2024, 1, 15, 11, 0, tzinfo=UTC),
    )


def mock_transition() -> Transition:
    """Sample transition for testing."""
    return Transition(id="21", name="In Progress")


def mock_project() -> Project:
    """Sample project for testing."""
    return Project(key="PROJ", name="Test Project", project_type="software")


def mock_user() -> User:
    """Sample user for testing."""
    return User(
        account_id="abc123",
        display_name="Test User",
        email="test@example.com",
        active=True,
        account_type="atlassian",
        avatar_url=None,
    )


def create_mock_client() -> MagicMock:
    """Create a mock client that works as context manager."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


class TestGetIssue:
    """Tests for get_issue tool."""

    def test_get_issue(self) -> None:
        """Can get issue details."""
        from jira_cli.mcp import get_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_issue.return_value = mock_issue()
                mock_client_class.return_value = client

                result = get_issue("PROJ-123")

        assert result["key"] == "PROJ-123"
        assert result["summary"] == "Test issue"
        assert result["status"] == "To Do"
        client.get_issue.assert_called_with("PROJ-123")


class TestSearchIssues:
    """Tests for search_issues tool."""

    def test_search_issues(self) -> None:
        """Can search issues with JQL."""
        from jira_cli.mcp import search_issues

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = [mock_issue()]
                mock_client_class.return_value = client

                result = search_issues("project = PROJ")

        assert len(result) == 1
        assert result[0]["key"] == "PROJ-123"
        client.search.assert_called_with("project = PROJ", limit=50)


class TestGetMyIssues:
    """Tests for get_my_issues tool."""

    def test_get_my_issues(self) -> None:
        """Can get assigned issues."""
        from jira_cli.mcp import get_my_issues

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_my_issues.return_value = [mock_issue()]
                mock_client_class.return_value = client

                result = get_my_issues(status="To Do", project="PROJ")

        assert len(result) == 1
        assert result[0]["key"] == "PROJ-123"
        client.get_my_issues.assert_called_with(
            status="To Do", project="PROJ", limit=50
        )


class TestCreateIssue:
    """Tests for create_issue tool."""

    def test_create_issue(self) -> None:
        """Can create a new issue."""
        from jira_cli.mcp import create_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.create_issue.return_value = "PROJ-124"
                mock_client_class.return_value = client

                result = create_issue(
                    project="PROJ",
                    summary="New issue",
                    issue_type="Task",
                    description="Description",
                )

        assert result["key"] == "PROJ-124"
        call_args = client.create_issue.call_args[0][0]
        assert isinstance(call_args, IssueCreateParams)
        assert call_args.project == "PROJ"
        assert call_args.summary == "New issue"

    def test_create_subtask(self) -> None:
        """Can create a subtask."""
        from jira_cli.mcp import create_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.create_issue.return_value = "PROJ-125"
                mock_client_class.return_value = client

                result = create_issue(
                    project="PROJ",
                    summary="Subtask",
                    issue_type="Sub-task",
                    parent="PROJ-123",
                )

        assert result["key"] == "PROJ-125"
        call_args = client.create_issue.call_args[0][0]
        assert call_args.parent == "PROJ-123"


class TestUpdateIssue:
    """Tests for update_issue tool."""

    def test_update_issue(self) -> None:
        """Can update an issue."""
        from jira_cli.mcp import update_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                mock_client_class.return_value = client

                result = update_issue("PROJ-123", summary="Updated summary")

        assert result["success"] is True
        assert result["issue_key"] == "PROJ-123"
        call_args = client.update_issue.call_args[0]
        assert call_args[0] == "PROJ-123"
        assert isinstance(call_args[1], IssueUpdateParams)


class TestGetTransitions:
    """Tests for get_transitions tool."""

    def test_get_transitions(self) -> None:
        """Can get available transitions."""
        from jira_cli.mcp import get_transitions

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_transitions.return_value = [mock_transition()]
                mock_client_class.return_value = client

                result = get_transitions("PROJ-123")

        assert len(result) == 1
        assert result[0]["name"] == "In Progress"


class TestTransitionIssue:
    """Tests for transition_issue tool."""

    def test_transition_issue(self) -> None:
        """Can transition an issue."""
        from jira_cli.mcp import transition_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.transition_issue.return_value = True
                mock_client_class.return_value = client

                result = transition_issue("PROJ-123", "In Progress")

        assert result["success"] is True
        assert result["new_status"] == "In Progress"
        client.transition_issue.assert_called_with("PROJ-123", "In Progress")


class TestGetComments:
    """Tests for get_comments tool."""

    def test_get_comments(self) -> None:
        """Can get issue comments."""
        from jira_cli.mcp import get_comments

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_comments.return_value = [mock_comment()]
                mock_client_class.return_value = client

                result = get_comments("PROJ-123")

        assert len(result) == 1
        assert result[0]["body"] == "Test comment"


class TestAddComment:
    """Tests for add_comment tool."""

    def test_add_comment(self) -> None:
        """Can add a comment."""
        from jira_cli.mcp import add_comment

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.add_comment.return_value = mock_comment()
                mock_client_class.return_value = client

                result = add_comment("PROJ-123", "New comment")

        assert result["id"] == "10001"
        client.add_comment.assert_called_with("PROJ-123", "New comment")


class TestGetProjects:
    """Tests for get_projects tool."""

    def test_get_projects(self) -> None:
        """Can get projects."""
        from jira_cli.mcp import get_projects

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_projects.return_value = [mock_project()]
                mock_client_class.return_value = client

                result = get_projects()

        assert len(result) == 1
        assert result[0]["key"] == "PROJ"
        assert result[0]["name"] == "Test Project"


class TestGetUsers:
    """Tests for get_users tool."""

    def test_get_users(self) -> None:
        """Can search users."""
        from jira_cli.mcp import get_users

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.get_users.return_value = [mock_user()]
                mock_client_class.return_value = client

                result = get_users(query="test", project="PROJ")

        assert len(result) == 1
        assert result[0]["display_name"] == "Test User"
        call_args = client.get_users.call_args[0][0]
        assert isinstance(call_args, UserSearchParams)
        assert call_args.query == "test"
        assert call_args.project == "PROJ"


class TestWatchIssue:
    """Tests for watch_issue tool."""

    def test_watch_issue(self) -> None:
        """Can watch an issue."""
        from jira_cli.mcp import watch_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                mock_client_class.return_value = client

                result = watch_issue("PROJ-123")

        assert result["success"] is True
        assert result["watching"] is True
        client.watch_issue.assert_called_with("PROJ-123")


class TestUnwatchIssue:
    """Tests for unwatch_issue tool."""

    def test_unwatch_issue(self) -> None:
        """Can unwatch an issue."""
        from jira_cli.mcp import unwatch_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                mock_client_class.return_value = client

                result = unwatch_issue("PROJ-123")

        assert result["success"] is True
        assert result["watching"] is False
        client.unwatch_issue.assert_called_with("PROJ-123")


class TestDeleteIssue:
    """Tests for delete_issue tool."""

    def test_delete_issue(self) -> None:
        """Can delete an issue."""
        from jira_cli.mcp import delete_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                mock_client_class.return_value = client

                result = delete_issue("PROJ-123")

        assert result["success"] is True
        assert result["deleted"] is True
        client.delete_issue.assert_called_with("PROJ-123")


class TestGetIssueQualityReport:
    """Tests for get_issue_quality_report tool."""

    def test_quality_report_with_project_filter(self) -> None:
        """Can generate quality report filtered by project."""
        from jira_cli.mcp import get_issue_quality_report

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = [mock_issue()]
                mock_client_class.return_value = client

                result = get_issue_quality_report(project="PROJ")

        assert len(result) == 1
        assert result[0]["key"] == "PROJ-123"
        assert "rating" in result[0]
        assert "age" in result[0]
        client.search.assert_called_with("project = PROJ", limit=50)

    def test_quality_report_with_status_filter(self) -> None:
        """Can generate quality report filtered by status."""
        from jira_cli.mcp import get_issue_quality_report

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = [mock_issue()]
                mock_client_class.return_value = client

                get_issue_quality_report(status="To Do")

        client.search.assert_called_with('status = "To Do"', limit=50)

    def test_quality_report_with_jql(self) -> None:
        """Custom JQL overrides project and status filters."""
        from jira_cli.mcp import get_issue_quality_report

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = [mock_issue()]
                mock_client_class.return_value = client

                get_issue_quality_report(
                    jql="assignee = currentUser()",
                    project="IGNORED",
                )

        client.search.assert_called_with("assignee = currentUser()", limit=50)

    def test_quality_report_no_filters(self) -> None:
        """Report without filters uses default ordering."""
        from jira_cli.mcp import get_issue_quality_report

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = []
                mock_client_class.return_value = client

                result = get_issue_quality_report()

        client.search.assert_called_with("ORDER BY created DESC", limit=50)
        assert result == []

    def test_quality_report_with_limit(self) -> None:
        """Limit parameter is passed to search."""
        from jira_cli.mcp import get_issue_quality_report

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                client = create_mock_client()
                client.search.return_value = []
                mock_client_class.return_value = client

                get_issue_quality_report(project="PROJ", limit=10)

        client.search.assert_called_with("project = PROJ", limit=10)
