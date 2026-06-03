"""Tests for interactive shell."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from jira_cli.models import Comment, Issue, Transition
from jira_cli.shell import JiraShell


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock Jira client."""
    return MagicMock()


@pytest.fixture
def mock_issues() -> list[Issue]:
    """Sample issues."""
    return [
        Issue(
            key="DAT-123",
            summary="Test issue",
            status="To Do",
            assignee="Test User",
            reporter="Reporter User",
            project="DAT",
            priority="Medium",
            created=datetime(2024, 1, 15, tzinfo=UTC),
            updated=datetime(2024, 1, 16, tzinfo=UTC),
            description="Test description",
        ),
    ]


@pytest.fixture
def shell(mock_client: MagicMock) -> JiraShell:
    """Shell instance with mock client."""
    return JiraShell(client=mock_client)


class TestShellNavigation:
    """Tests for shell navigation commands."""

    def test_cd_into_issue(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Can cd into an issue."""
        mock_client.get_issue.return_value = mock_issues[0]

        shell.do_cd("DAT-123")

        assert shell.current_issue == "DAT-123"

    def test_cd_back(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Can cd back with '..'."""
        mock_client.get_issue.return_value = mock_issues[0]
        shell.do_cd("DAT-123")

        shell.do_cd("..")

        assert shell.current_issue is None

    def test_pwd_no_issue(self, shell: JiraShell) -> None:
        """Pwd shows no issue selected."""
        shell.do_pwd("")

        assert shell.current_issue is None

    def test_pwd_with_issue(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Pwd shows current issue."""
        mock_client.get_issue.return_value = mock_issues[0]
        shell.do_cd("DAT-123")

        shell.do_pwd("")

        assert shell.current_issue == "DAT-123"

    def test_prompt_changes(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Prompt reflects current issue."""
        assert "jira" in shell.prompt
        assert "DAT-123" not in shell.prompt

        mock_client.get_issue.return_value = mock_issues[0]
        shell.do_cd("DAT-123")

        assert "jira" in shell.prompt
        assert "DAT-123" in shell.prompt


class TestShellCommands:
    """Tests for shell action commands."""

    def test_list_issues(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """List shows issues."""
        mock_client.get_my_issues.return_value = mock_issues

        shell.do_list("")

        mock_client.get_my_issues.assert_called_once()

    def test_show_requires_issue_or_arg(self, shell: JiraShell) -> None:
        """Show without arg or current issue prints usage."""
        shell.do_show("")
        # Should print usage, not crash

    def test_show_displays_issue(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Show displays current issue."""
        mock_client.get_issue.return_value = mock_issues[0]
        shell.do_cd("DAT-123")

        shell.do_show("")

        # get_issue called twice: once for cd, once for show
        assert mock_client.get_issue.call_count == 2

    def test_cat_with_issue_key_from_root(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Cat ISSUE-KEY works from root without cd."""
        mock_client.get_issue.return_value = mock_issues[0]

        shell.do_cat("DAT-123")

        mock_client.get_issue.assert_called_with("DAT-123")
        assert shell.current_issue is None  # Didn't cd into it

    def test_ls_inside_issue_shows_details(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Ls inside an issue shows issue details."""
        mock_client.get_issue.return_value = mock_issues[0]
        shell.do_cd("DAT-123")
        mock_client.get_issue.reset_mock()
        mock_client.get_issue.return_value = mock_issues[0]

        shell.do_ls("")

        # ls inside issue calls get_issue, not get_my_issues
        mock_client.get_issue.assert_called_with("DAT-123")
        mock_client.get_my_issues.assert_not_called()

    def test_ls_at_root_lists_issues(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Ls at root lists all issues."""
        mock_client.get_my_issues.return_value = mock_issues

        shell.do_ls("")

        mock_client.get_my_issues.assert_called_once()

    def test_comment_requires_issue(self, shell: JiraShell) -> None:
        """Comment requires being in an issue."""
        shell.do_comment("test comment")
        # Should print error, not crash

    def test_comment_adds_comment(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Comment adds to current issue."""
        mock_client.get_issue.return_value = mock_issues[0]
        mock_client.add_comment.return_value = Comment(
            id="1", author="Test", body="test", created=datetime.now(UTC)
        )
        shell.do_cd("DAT-123")

        shell.do_comment("test comment")

        mock_client.add_comment.assert_called_with("DAT-123", "test comment")

    def test_status_shows_transitions(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Status without arg shows transitions."""
        mock_client.get_issue.return_value = mock_issues[0]
        mock_client.get_transitions.return_value = [
            Transition(id="1", name="Done"),
            Transition(id="2", name="In Progress"),
        ]
        shell.do_cd("DAT-123")

        shell.do_status("")

        mock_client.get_transitions.assert_called_with("DAT-123")

    def test_status_transitions_issue(
        self, shell: JiraShell, mock_client: MagicMock, mock_issues: list[Issue]
    ) -> None:
        """Status with arg transitions issue."""
        mock_client.get_issue.return_value = mock_issues[0]
        mock_client.transition_issue.return_value = True
        shell.do_cd("DAT-123")

        shell.do_status("Done")

        mock_client.transition_issue.assert_called_with("DAT-123", "Done")


class TestShellExit:
    """Tests for shell exit."""

    def test_quit_exits(self, shell: JiraShell) -> None:
        """Quit returns True to exit."""
        result = shell.do_quit("")
        assert result is True

    def test_q_exits(self, shell: JiraShell) -> None:
        """Q returns True to exit."""
        result = shell.do_q("")
        assert result is True

    def test_eof_exits(self, shell: JiraShell) -> None:
        """EOF (Ctrl+D) returns True to exit."""
        result = shell.do_EOF("")
        assert result is True
