"""Tests for the Confluence API client."""

import json

import httpx
import respx

from jira_cli.confluence_client import (
    ConfluenceClient,
    PageCreateParams,
    PageUpdateParams,
)

BASE = "https://test.atlassian.net"


class TestListSpaces:
    """Tests for listing spaces."""

    @respx.mock
    def test_list_spaces(
        self,
        confluence_client: ConfluenceClient,
        sample_spaces_response: dict,
    ) -> None:
        """Spaces are listed from the v2 endpoint."""
        respx.get(f"{BASE}/wiki/api/v2/spaces").mock(
            return_value=httpx.Response(200, json=sample_spaces_response)
        )

        spaces = confluence_client.list_spaces()

        assert len(spaces) == 2
        assert spaces[0].key == "DEV"
        assert spaces[0].id == "111"


class TestGetPage:
    """Tests for fetching a page."""

    @respx.mock
    def test_get_page(
        self,
        confluence_client: ConfluenceClient,
        sample_page_response: dict,
    ) -> None:
        """A page is fetched with its storage body."""
        route = respx.get(f"{BASE}/wiki/api/v2/pages/12345").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )

        page = confluence_client.get_page("12345")

        assert page.id == "12345"
        assert page.title == "Test Page"
        assert page.version == 3
        assert page.body is not None
        assert "body-format=storage" in str(route.calls[0].request.url)


class TestSearch:
    """Tests for CQL search."""

    @respx.mock
    def test_search(
        self,
        confluence_client: ConfluenceClient,
        sample_confluence_search_response: dict,
    ) -> None:
        """Search uses the v1 search endpoint with the CQL query."""
        route = respx.get(f"{BASE}/wiki/rest/api/search").mock(
            return_value=httpx.Response(200, json=sample_confluence_search_response)
        )

        pages = confluence_client.search("text ~ 'roadmap'")

        assert len(pages) == 2
        assert pages[0].id == "12345"
        assert pages[0].title == "Test Page"
        assert "cql=" in str(route.calls[0].request.url)


class TestCreatePage:
    """Tests for creating a page."""

    @respx.mock
    def test_create_page_resolves_space_key(
        self,
        confluence_client: ConfluenceClient,
        sample_page_response: dict,
    ) -> None:
        """Create resolves the space key to an ID, then posts the page."""
        respx.get(f"{BASE}/wiki/api/v2/spaces").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "111",
                            "key": "DEV",
                            "name": "Dev",
                            "type": "global",
                            "status": "current",
                        }
                    ]
                },
            )
        )
        create_route = respx.post(f"{BASE}/wiki/api/v2/pages").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )

        params = PageCreateParams(space_key="DEV", title="New", body="# Heading")
        page = confluence_client.create_page(params)

        assert page.id == "12345"
        body = json.loads(create_route.calls[0].request.content)
        assert body["spaceId"] == "111"
        assert body["title"] == "New"
        assert body["body"]["representation"] == "storage"
        assert "<h1>Heading</h1>" in body["body"]["value"]

    @respx.mock
    def test_create_page_with_parent(
        self,
        confluence_client: ConfluenceClient,
        sample_page_response: dict,
    ) -> None:
        """A parent ID is included in the create payload."""
        respx.get(f"{BASE}/wiki/api/v2/spaces").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "111",
                            "key": "DEV",
                            "name": "Dev",
                            "type": "global",
                            "status": "current",
                        }
                    ]
                },
            )
        )
        create_route = respx.post(f"{BASE}/wiki/api/v2/pages").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )

        params = PageCreateParams(
            space_key="DEV", title="Child", body="text", parent_id="999"
        )
        confluence_client.create_page(params)

        body = json.loads(create_route.calls[0].request.content)
        assert body["parentId"] == "999"


class TestUpdatePage:
    """Tests for updating a page."""

    @respx.mock
    def test_update_page_increments_version(
        self,
        confluence_client: ConfluenceClient,
        sample_page_response: dict,
    ) -> None:
        """Update fetches the current page and increments the version."""
        respx.get(f"{BASE}/wiki/api/v2/pages/12345").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )
        update_route = respx.put(f"{BASE}/wiki/api/v2/pages/12345").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )

        params = PageUpdateParams(title="Renamed")
        confluence_client.update_page("12345", params)

        body = json.loads(update_route.calls[0].request.content)
        assert body["title"] == "Renamed"
        assert body["version"]["number"] == 4
        assert body["id"] == "12345"

    @respx.mock
    def test_update_page_keeps_existing_title_when_unset(
        self,
        confluence_client: ConfluenceClient,
        sample_page_response: dict,
    ) -> None:
        """Omitting the title keeps the existing one."""
        respx.get(f"{BASE}/wiki/api/v2/pages/12345").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )
        update_route = respx.put(f"{BASE}/wiki/api/v2/pages/12345").mock(
            return_value=httpx.Response(200, json=sample_page_response)
        )

        params = PageUpdateParams(body="# New body")
        confluence_client.update_page("12345", params)

        body = json.loads(update_route.calls[0].request.content)
        assert body["title"] == "Test Page"
        assert "<h1>New body</h1>" in body["body"]["value"]


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager(self, confluence_client: ConfluenceClient) -> None:
        """Client works as a context manager."""
        with confluence_client as client:
            assert client is confluence_client
