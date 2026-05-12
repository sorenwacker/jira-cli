"""Tests for CLI commands."""

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from jira_cli.cli import app
from jira_cli.models import Issue, Comment, Transition
from jira_cli.config import JiraConfig


runner = CliRunner()


@pytest.fixture
def mock_config() -> JiraConfig:
    """Mock configuration."""
    return JiraConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
    )


@pytest.fixture
def mock_issues() -> list[Issue]:
    """Sample issues for testing."""
    return [
        Issue(
            key="PROJ-123",
            summary="First test issue",
            status="To Do",
            assignee="Test User",
            reporter="Reporter User",
            project="PROJ",
            priority="High",
            created=datetime(2024, 1, 15, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 16, tzinfo=timezone.utc),
            description="Description of first issue",
        ),
        Issue(
            key="PROJ-456",
            summary="Second test issue",
            status="In Progress",
            assignee="Test User",
            reporter="Another Reporter",
            project="PROJ",
            priority="Medium",
            created=datetime(2024, 1, 14, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
            description=None,
        ),
    ]


@pytest.fixture
def mock_comments() -> list[Comment]:
    """Sample comments for testing."""
    return [
        Comment(
            id="10001",
            author="Test User",
            body="First comment",
            created=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
        ),
        Comment(
            id="10002",
            author="Another User",
            body="Second comment",
            created=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def mock_transitions() -> list[Transition]:
    """Sample transitions for testing."""
    return [
        Transition(id="11", name="To Do"),
        Transition(id="21", name="In Progress"),
        Transition(id="31", name="Done"),
    ]


def create_mock_client() -> MagicMock:
    """Create a mock client that works as context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


class TestListCommand:
    """Tests for 'jira issue list' command."""

    def test_list_issues(self, mock_config: JiraConfig, mock_issues: list[Issue]) -> None:
        """List command displays assigned issues."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_my_issues.return_value = mock_issues
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "list"])

        assert result.exit_code == 0
        assert "PROJ-123" in result.output
        assert "First test issue" in result.output
        assert "PROJ-456" in result.output

    def test_list_issues_with_status_filter(
        self, mock_config: JiraConfig, mock_issues: list[Issue]
    ) -> None:
        """List command can filter by status."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_my_issues.return_value = [mock_issues[1]]
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "list", "--status", "In Progress"])

        assert result.exit_code == 0
        mock_client.get_my_issues.assert_called_with(
            status="In Progress", project=None, limit=50
        )

    def test_list_issues_with_project_filter(
        self, mock_config: JiraConfig, mock_issues: list[Issue]
    ) -> None:
        """List command can filter by project."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_my_issues.return_value = mock_issues
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "list", "--project", "PROJ"])

        assert result.exit_code == 0
        mock_client.get_my_issues.assert_called_with(
            status=None, project="PROJ", limit=50
        )

    def test_list_no_issues(self, mock_config: JiraConfig) -> None:
        """List command handles no issues gracefully."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_my_issues.return_value = []
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "list"])

        assert result.exit_code == 0
        assert "No issues found" in result.output


class TestViewCommand:
    """Tests for 'jira issue view' command."""

    def test_view_issue(
        self, mock_config: JiraConfig, mock_issues: list[Issue]
    ) -> None:
        """View command displays issue details."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_issue.return_value = mock_issues[0]
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "view", "PROJ-123"])

        assert result.exit_code == 0
        assert "PROJ-123" in result.output
        assert "First test issue" in result.output
        assert "To Do" in result.output

    def test_view_issue_with_comments(
        self,
        mock_config: JiraConfig,
        mock_issues: list[Issue],
        mock_comments: list[Comment],
    ) -> None:
        """View command can include comments."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_issue.return_value = mock_issues[0]
                mock_client.get_comments.return_value = mock_comments
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "view", "PROJ-123", "--comments"])

        assert result.exit_code == 0
        assert "First comment" in result.output
        assert "Second comment" in result.output


class TestCommentCommand:
    """Tests for 'jira issue comment' commands."""

    def test_add_comment(
        self, mock_config: JiraConfig, mock_comments: list[Comment]
    ) -> None:
        """Comment add command adds a comment."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.add_comment.return_value = mock_comments[0]
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    app, ["issue", "comment", "add", "PROJ-123", "This is my comment"]
                )

        assert result.exit_code == 0
        mock_client.add_comment.assert_called_with("PROJ-123", "This is my comment")
        assert "Comment added" in result.output

    def test_edit_comment(
        self, mock_config: JiraConfig
    ) -> None:
        """Comment edit command updates a comment."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    app, ["issue", "comment", "edit", "PROJ-123", "10001", "Updated text"]
                )

        assert result.exit_code == 0
        mock_client.update_comment.assert_called_with("PROJ-123", "10001", "Updated text")
        assert "Comment updated" in result.output

    def test_delete_comment(
        self, mock_config: JiraConfig
    ) -> None:
        """Comment delete command deletes a comment."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client_class.return_value = mock_client

                result = runner.invoke(
                    app, ["issue", "comment", "delete", "PROJ-123", "10001"]
                )

        assert result.exit_code == 0
        mock_client.delete_comment.assert_called_with("PROJ-123", "10001")
        assert "Comment deleted" in result.output


class TestMoveCommand:
    """Tests for 'jira issue move' command."""

    def test_list_transitions(
        self, mock_config: JiraConfig, mock_transitions: list[Transition]
    ) -> None:
        """Move command without target shows available transitions."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.get_transitions.return_value = mock_transitions
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "move", "PROJ-123"])

        assert result.exit_code == 0
        assert "To Do" in result.output
        assert "In Progress" in result.output
        assert "Done" in result.output

    def test_transition_issue(
        self, mock_config: JiraConfig, mock_transitions: list[Transition]
    ) -> None:
        """Move command with target transitions the issue."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            with patch("jira_cli.cli.JiraClient") as mock_client_class:
                mock_client = create_mock_client()
                mock_client.transition_issue.return_value = True
                mock_client_class.return_value = mock_client

                result = runner.invoke(app, ["issue", "move", "PROJ-123", "In Progress"])

        assert result.exit_code == 0
        mock_client.transition_issue.assert_called_with("PROJ-123", "In Progress")
        assert "transitioned" in result.output.lower() or "In Progress" in result.output


class TestConfigCommand:
    """Tests for 'jira config' command."""

    def test_config_show(self, mock_config: JiraConfig) -> None:
        """Config --show displays current config (redacted)."""
        with patch("jira_cli.cli.load_config", return_value=mock_config):
            result = runner.invoke(app, ["config", "--show"])

        assert result.exit_code == 0
        assert "test.atlassian.net" in result.output
        assert "test@example.com" in result.output
        # Token should be redacted
        assert "test-token" not in result.output

    def test_config_interactive(self) -> None:
        """Config command prompts for input."""
        with patch("jira_cli.cli.save_config") as mock_save:
            result = runner.invoke(
                app,
                ["config"],
                input="https://new.atlassian.net\nnew@example.com\nnew-token\n",
            )

        assert result.exit_code == 0
        mock_save.assert_called_once()
        saved_config = mock_save.call_args[0][0]
        assert saved_config.url == "https://new.atlassian.net"
        assert saved_config.email == "new@example.com"
        assert saved_config.api_token == "new-token"
