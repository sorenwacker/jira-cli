"""Tests for the confluence CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jira_cli.config import ConfluenceConfig
from jira_cli.confluence_cli import app
from jira_cli.confluence_models import Page, Space

runner = CliRunner()


def mock_config() -> ConfluenceConfig:
    """Mock Confluence configuration."""
    return ConfluenceConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
    )


def mock_page() -> Page:
    """Sample page for testing."""
    return Page(
        id="12345",
        title="Test Page",
        space_id="111",
        status="current",
        version=3,
        body="<p>Body <strong>text</strong></p>",
        url="/spaces/DEV/pages/12345",
    )


def mock_space() -> Space:
    """Sample space for testing."""
    return Space(
        id="111", key="DEV", name="Development", type="global", status="current"
    )


def create_mock_client() -> MagicMock:
    """Create a mock Confluence client with context manager support."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = None
    return client


class TestSpaceList:
    """Tests for space list command."""

    def test_space_list(self) -> None:
        """Lists spaces in a table."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.list_spaces.return_value = [mock_space()]
                cls.return_value = client

                result = runner.invoke(app, ["space", "list"])

        assert result.exit_code == 0
        assert "DEV" in result.stdout


class TestSearch:
    """Tests for search command."""

    def test_search(self) -> None:
        """Searches and shows results."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.search.return_value = [mock_page()]
                cls.return_value = client

                result = runner.invoke(app, ["search", "text ~ 'x'"])

        assert result.exit_code == 0
        assert "12345" in result.stdout
        client.search.assert_called_with("text ~ 'x'", limit=25)


class TestPageRead:
    """Tests for reading a page."""

    def test_page_read_renders_text(self) -> None:
        """Reads a page and renders the body to plain text."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.get_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(app, ["page", "12345"])

        assert result.exit_code == 0
        assert "Body text" in result.stdout
        client.get_page.assert_called_with("12345")

    def test_page_read_raw(self) -> None:
        """The --raw flag shows the storage body."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.get_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(app, ["page", "12345", "--raw"])

        assert result.exit_code == 0
        assert "<strong>" in result.stdout


class TestPageCreate:
    """Tests for creating a page."""

    def test_page_create_inline_body(self) -> None:
        """Creates a page from an inline body."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.create_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(
                    app,
                    ["create", "--space", "DEV", "--title", "T", "--body", "# Heading"],
                )

        assert result.exit_code == 0
        assert "12345" in result.stdout
        params = client.create_page.call_args.args[0]
        assert params.space_key == "DEV"
        assert params.title == "T"
        assert params.body == "# Heading"

    def test_page_create_from_file(self, tmp_path: Path) -> None:
        """Creates a page from a markdown file."""
        md = tmp_path / "notes.md"
        md.write_text("# From file")
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.create_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(
                    app,
                    ["create", "--space", "DEV", "--title", "T", "--file", str(md)],
                )

        assert result.exit_code == 0
        params = client.create_page.call_args.args[0]
        assert params.body == "# From file"


class TestPageUpdate:
    """Tests for updating a page."""

    def test_page_update_title(self) -> None:
        """Updates a page title."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.update_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(app, ["update", "12345", "--title", "New"])

        assert result.exit_code == 0
        page_id = client.update_page.call_args.args[0]
        params = client.update_page.call_args.args[1]
        assert page_id == "12345"
        assert params.title == "New"

    def test_page_update_clears_body_with_empty_string(self) -> None:
        """An explicit empty --body clears the body rather than keeping it."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_cli.ConfluenceClient") as cls:
                client = create_mock_client()
                client.update_page.return_value = mock_page()
                cls.return_value = client

                result = runner.invoke(app, ["update", "12345", "--body", ""])

        assert result.exit_code == 0
        params = client.update_page.call_args.args[1]
        assert params.body == ""


class TestConfig:
    """Tests for the config command."""

    def test_config_show(self) -> None:
        """Shows resolved configuration with redacted token."""
        with patch(
            "jira_cli.confluence_cli.load_confluence_config", return_value=mock_config()
        ):
            result = runner.invoke(app, ["config", "--show"])

        assert result.exit_code == 0
        assert "test.atlassian.net" in result.stdout
        assert "test-token" not in result.stdout
