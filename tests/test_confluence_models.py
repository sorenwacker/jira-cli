"""Tests for Confluence data models."""

from jira_cli.confluence_models import Page


class TestPageFromApiResponse:
    """Tests for Page.from_api_response null handling."""

    def test_full_response(self) -> None:
        """A complete response populates every field."""
        page = Page.from_api_response(
            {
                "id": 123,
                "title": "Doc",
                "spaceId": 9,
                "status": "current",
                "version": {"number": 4},
                "body": {"storage": {"value": "<p>hi</p>"}},
                "_links": {"webui": "/spaces/DEV/pages/123/Doc"},
            }
        )
        assert page.version == 4
        assert page.body == "<p>hi</p>"
        assert page.url == "/spaces/DEV/pages/123/Doc"

    def test_null_nested_objects_do_not_crash(self) -> None:
        """Explicit JSON null for nested objects is treated as absent."""
        page = Page.from_api_response(
            {
                "id": 123,
                "title": "Doc",
                "version": None,
                "body": None,
                "_links": None,
            }
        )
        assert page.version is None
        assert page.body is None
        assert page.url is None

    def test_null_storage_does_not_crash(self) -> None:
        """A present body with null storage is treated as absent."""
        page = Page.from_api_response(
            {"id": 1, "title": "Doc", "body": {"storage": None}}
        )
        assert page.body is None


class TestPageFromSearchResult:
    """Tests for Page.from_search_result."""

    def test_missing_optional_fields_use_defaults(self) -> None:
        """Absent title and status fall back to empty strings."""
        page = Page.from_search_result({"content": {"id": 7}, "url": "/x"})
        assert page.id == "7"
        assert page.title == ""
        assert page.status == ""
        assert page.url == "/x"
