"""Tests for Confluence MCP tools."""

from unittest.mock import MagicMock, patch

from jira_cli.config import ConfluenceConfig
from jira_cli.confluence_models import Page, Space


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
        body="<p>Body text</p>",
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


class TestConfluenceSearch:
    """Tests for confluence_search tool."""

    def test_search(self) -> None:
        """Can search content with CQL."""
        from jira_cli.confluence_mcp import confluence_search

        with patch(
            "jira_cli.confluence_mcp.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_mcp.ConfluenceClient") as cls:
                client = create_mock_client()
                client.search.return_value = [mock_page()]
                cls.return_value = client

                result = confluence_search("text ~ 'x'")

        assert len(result) == 1
        assert result[0]["id"] == "12345"
        client.search.assert_called_with("text ~ 'x'", limit=25)


class TestGetPage:
    """Tests for get_page tool."""

    def test_get_page(self) -> None:
        """Can get a page with its rendered body."""
        from jira_cli.confluence_mcp import get_page

        with patch(
            "jira_cli.confluence_mcp.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_mcp.ConfluenceClient") as cls:
                client = create_mock_client()
                client.get_page.return_value = mock_page()
                cls.return_value = client

                result = get_page("12345")

        assert result["id"] == "12345"
        assert result["title"] == "Test Page"
        assert result["body"] == "Body text"
        client.get_page.assert_called_with("12345")


class TestListSpaces:
    """Tests for list_spaces tool."""

    def test_list_spaces(self) -> None:
        """Can list spaces."""
        from jira_cli.confluence_mcp import list_spaces

        with patch(
            "jira_cli.confluence_mcp.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_mcp.ConfluenceClient") as cls:
                client = create_mock_client()
                client.list_spaces.return_value = [mock_space()]
                cls.return_value = client

                result = list_spaces()

        assert len(result) == 1
        assert result[0]["key"] == "DEV"


class TestCreatePage:
    """Tests for create_page tool."""

    def test_create_page(self) -> None:
        """Can create a page from markdown."""
        from jira_cli.confluence_mcp import create_page

        with patch(
            "jira_cli.confluence_mcp.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_mcp.ConfluenceClient") as cls:
                client = create_mock_client()
                client.create_page.return_value = mock_page()
                cls.return_value = client

                result = create_page("DEV", "Title", "# Heading")

        assert result["id"] == "12345"
        assert client.create_page.called


class TestUpdatePage:
    """Tests for update_page tool."""

    def test_update_page(self) -> None:
        """Can update a page."""
        from jira_cli.confluence_mcp import update_page

        with patch(
            "jira_cli.confluence_mcp.load_confluence_config", return_value=mock_config()
        ):
            with patch("jira_cli.confluence_mcp.ConfluenceClient") as cls:
                client = create_mock_client()
                client.update_page.return_value = mock_page()
                cls.return_value = client

                result = update_page("12345", title="New")

        assert result["id"] == "12345"
        assert client.update_page.called
