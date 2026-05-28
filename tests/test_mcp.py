"""Tests for MCP server tools."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from jira_cli.config import JiraConfig
from jira_cli.models import Comment, Issue, Project, Transition, User


@pytest.fixture
def mock_config() -> JiraConfig:
    """Mock configuration."""
    return JiraConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
    )


@pytest.fixture
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
    )


@pytest.fixture
def mock_comment() -> Comment:
    """Sample comment for testing."""
    return Comment(
        id="10001",
        author="Test User",
        body="Test comment",
        created=datetime(2024, 1, 15, 11, 0, tzinfo=UTC),
    )


@pytest.fixture
def mock_transition() -> Transition:
    """Sample transition for testing."""
    return Transition(id="21", name="In Progress")


@pytest.fixture
def mock_project() -> Project:
    """Sample project for testing."""
    return Project(key="PROJ", name="Test Project", project_type="software")


@pytest.fixture
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
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


class TestGetIssue:
    """Tests for get_issue tool."""

    def test_get_issue(self, mock_config: JiraConfig, mock_issue: Issue) -> None:
        """Can get issue details."""
        from jira_cli.mcp import get_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_issue.return_value = mock_issue
                mock_client_class.return_value = mock_client

                result = get_issue("PROJ-123")

        assert result["key"] == "PROJ-123"
        assert result["summary"] == "Test issue"
        assert result["status"] == "To Do"
        mock_client.get_issue.assert_called_with("PROJ-123")


class TestSearchIssues:
    """Tests for search_issues tool."""

    def test_search_issues(self, mock_config: JiraConfig, mock_issue: Issue) -> None:
        """Can search issues with JQL."""
        from jira_cli.mcp import search_issues

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.search.return_value = [mock_issue]
                mock_client_class.return_value = mock_client

                result = search_issues("project = PROJ")

        assert len(result) == 1
        assert result[0]["key"] == "PROJ-123"
        mock_client.search.assert_called_with("project = PROJ", limit=50)


class TestGetMyIssues:
    """Tests for get_my_issues tool."""

    def test_get_my_issues(self, mock_config: JiraConfig, mock_issue: Issue) -> None:
        """Can get assigned issues."""
        from jira_cli.mcp import get_my_issues

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_my_issues.return_value = [mock_issue]
                mock_client_class.return_value = mock_client

                result = get_my_issues(status="To Do", project="PROJ")

        assert len(result) == 1
        assert result[0]["key"] == "PROJ-123"
        mock_client.get_my_issues.assert_called_with(status="To Do", project="PROJ", limit=50)


class TestCreateIssue:
    """Tests for create_issue tool."""

    def test_create_issue(self, mock_config: JiraConfig) -> None:
        """Can create a new issue."""
        from jira_cli.mcp import create_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.create_issue.return_value = "PROJ-124"
                mock_client_class.return_value = mock_client

                result = create_issue(
                    project="PROJ",
                    summary="New issue",
                    issue_type="Task",
                    description="Description",
                )

        assert result["key"] == "PROJ-124"
        mock_client.create_issue.assert_called_with(
            project="PROJ",
            summary="New issue",
            issue_type="Task",
            description="Description",
            priority=None,
            labels=None,
            parent=None,
        )

    def test_create_subtask(self, mock_config: JiraConfig) -> None:
        """Can create a subtask."""
        from jira_cli.mcp import create_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.create_issue.return_value = "PROJ-125"
                mock_client_class.return_value = mock_client

                result = create_issue(
                    project="PROJ",
                    summary="Subtask",
                    issue_type="Sub-task",
                    parent="PROJ-123",
                )

        assert result["key"] == "PROJ-125"
        mock_client.create_issue.assert_called_with(
            project="PROJ",
            summary="Subtask",
            issue_type="Sub-task",
            description=None,
            priority=None,
            labels=None,
            parent="PROJ-123",
        )


class TestUpdateIssue:
    """Tests for update_issue tool."""

    def test_update_issue(self, mock_config: JiraConfig) -> None:
        """Can update an issue."""
        from jira_cli.mcp import update_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = update_issue("PROJ-123", summary="Updated summary")

        assert result["success"] is True
        assert result["issue_key"] == "PROJ-123"
        mock_client.update_issue.assert_called_once()


class TestGetTransitions:
    """Tests for get_transitions tool."""

    def test_get_transitions(self, mock_config: JiraConfig, mock_transition: Transition) -> None:
        """Can get available transitions."""
        from jira_cli.mcp import get_transitions

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_transitions.return_value = [mock_transition]
                mock_client_class.return_value = mock_client

                result = get_transitions("PROJ-123")

        assert len(result) == 1
        assert result[0]["name"] == "In Progress"


class TestTransitionIssue:
    """Tests for transition_issue tool."""

    def test_transition_issue(self, mock_config: JiraConfig) -> None:
        """Can transition an issue."""
        from jira_cli.mcp import transition_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.transition_issue.return_value = True
                mock_client_class.return_value = mock_client

                result = transition_issue("PROJ-123", "In Progress")

        assert result["success"] is True
        assert result["new_status"] == "In Progress"
        mock_client.transition_issue.assert_called_with("PROJ-123", "In Progress")


class TestGetComments:
    """Tests for get_comments tool."""

    def test_get_comments(self, mock_config: JiraConfig, mock_comment: Comment) -> None:
        """Can get issue comments."""
        from jira_cli.mcp import get_comments

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_comments.return_value = [mock_comment]
                mock_client_class.return_value = mock_client

                result = get_comments("PROJ-123")

        assert len(result) == 1
        assert result[0]["body"] == "Test comment"


class TestAddComment:
    """Tests for add_comment tool."""

    def test_add_comment(self, mock_config: JiraConfig, mock_comment: Comment) -> None:
        """Can add a comment."""
        from jira_cli.mcp import add_comment

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.add_comment.return_value = mock_comment
                mock_client_class.return_value = mock_client

                result = add_comment("PROJ-123", "New comment")

        assert result["id"] == "10001"
        mock_client.add_comment.assert_called_with("PROJ-123", "New comment")


class TestGetProjects:
    """Tests for get_projects tool."""

    def test_get_projects(self, mock_config: JiraConfig, mock_project: Project) -> None:
        """Can get projects."""
        from jira_cli.mcp import get_projects

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_projects.return_value = [mock_project]
                mock_client_class.return_value = mock_client

                result = get_projects()

        assert len(result) == 1
        assert result[0]["key"] == "PROJ"
        assert result[0]["name"] == "Test Project"


class TestGetUsers:
    """Tests for get_users tool."""

    def test_get_users(self, mock_config: JiraConfig, mock_user: User) -> None:
        """Can search users."""
        from jira_cli.mcp import get_users

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_users.return_value = [mock_user]
                mock_client_class.return_value = mock_client

                result = get_users(query="test", project="PROJ")

        assert len(result) == 1
        assert result[0]["display_name"] == "Test User"
        mock_client.get_users.assert_called_with(query="test", project="PROJ", limit=50)


class TestWatchIssue:
    """Tests for watch_issue tool."""

    def test_watch_issue(self, mock_config: JiraConfig) -> None:
        """Can watch an issue."""
        from jira_cli.mcp import watch_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = watch_issue("PROJ-123")

        assert result["success"] is True
        assert result["watching"] is True
        mock_client.watch_issue.assert_called_with("PROJ-123")


class TestUnwatchIssue:
    """Tests for unwatch_issue tool."""

    def test_unwatch_issue(self, mock_config: JiraConfig) -> None:
        """Can unwatch an issue."""
        from jira_cli.mcp import unwatch_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = unwatch_issue("PROJ-123")

        assert result["success"] is True
        assert result["watching"] is False
        mock_client.unwatch_issue.assert_called_with("PROJ-123")


class TestDeleteIssue:
    """Tests for delete_issue tool."""

    def test_delete_issue(self, mock_config: JiraConfig) -> None:
        """Can delete an issue."""
        from jira_cli.mcp import delete_issue

        with patch("jira_cli.mcp.load_config", return_value=mock_config):
            with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = delete_issue("PROJ-123")

        assert result["success"] is True
        assert result["deleted"] is True
        mock_client.delete_issue.assert_called_with("PROJ-123")
