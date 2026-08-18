"""Confluence Cloud API client."""

import base64
from dataclasses import dataclass
from typing import Any, Self

import httpx

from jira_cli.config import ConfluenceConfig
from jira_cli.confluence_models import Page, Space
from jira_cli.confluence_storage import markdown_to_storage

__all__ = ["ConfluenceClient", "PageCreateParams", "PageUpdateParams"]

# Confluence REST API v2 base path for content CRUD.
_V2 = "/wiki/api/v2"
# Confluence REST API v1 search endpoint (no v2 equivalent for CQL).
_SEARCH = "/wiki/rest/api/search"


class ConfluenceClient:
    """Client for interacting with the Confluence Cloud REST API."""

    def __init__(self, config: ConfluenceConfig) -> None:
        """Initialize the Confluence client.

        Args:
            config: Confluence connection configuration.
        """
        self.config = config
        credentials = f"{config.email}:{config.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._client = httpx.Client(
            base_url=config.url,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def list_spaces(self, limit: int = 25) -> list[Space]:
        """List Confluence spaces.

        Args:
            limit: Maximum number of spaces to return.

        Returns:
            List of Space objects.
        """
        response = self._client.get(f"{_V2}/spaces", params={"limit": limit})
        response.raise_for_status()
        results = response.json().get("results", [])
        return [Space.from_api_response(s) for s in results]

    def get_space_by_key(self, key: str) -> Space:
        """Resolve a space key to its Space object.

        Args:
            key: The space key (e.g., "DEV").

        Returns:
            The matching Space.

        Raises:
            ValueError: If no space with the given key exists.
        """
        response = self._client.get(f"{_V2}/spaces", params={"keys": key})
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            msg = f"Space not found: {key}"
            raise ValueError(msg)
        return Space.from_api_response(results[0])

    def get_page(self, page_id: str) -> Page:
        """Fetch a page by ID, including its storage-format body.

        Args:
            page_id: The numeric page ID.

        Returns:
            The Page object.
        """
        response = self._client.get(
            f"{_V2}/pages/{page_id}",
            params={"body-format": "storage"},
        )
        response.raise_for_status()
        return Page.from_api_response(response.json())

    def search(self, cql: str, limit: int = 25) -> list[Page]:
        """Search content using CQL.

        Args:
            cql: A Confluence Query Language expression.
            limit: Maximum number of results.

        Returns:
            List of matching Page objects (without body or version).
        """
        response = self._client.get(_SEARCH, params={"cql": cql, "limit": limit})
        response.raise_for_status()
        results = response.json().get("results", [])
        return [Page.from_search_result(r) for r in results]

    def create_page(self, params: "PageCreateParams") -> Page:
        """Create a new page from markdown.

        Args:
            params: Page creation parameters.

        Returns:
            The created Page.
        """
        space = self.get_space_by_key(params.space_key)
        payload: dict[str, Any] = {
            "spaceId": space.id,
            "status": "current",
            "title": params.title,
            "body": {
                "representation": "storage",
                "value": markdown_to_storage(params.body),
            },
        }
        if params.parent_id:
            payload["parentId"] = params.parent_id
        response = self._client.post(f"{_V2}/pages", json=payload)
        response.raise_for_status()
        return Page.from_api_response(response.json())

    def update_page(self, page_id: str, params: "PageUpdateParams") -> Page:
        """Update a page's title and/or body.

        The current page is fetched first to obtain the version number, which is
        incremented as required by the API.

        Args:
            page_id: The numeric page ID.
            params: Page update parameters.

        Returns:
            The updated Page.
        """
        current = self.get_page(page_id)
        title = params.title if params.title is not None else current.title
        if params.body is not None:
            body = markdown_to_storage(params.body)
        else:
            body = current.body or ""
        payload = {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body},
            "version": {"number": (current.version or 0) + 1},
        }
        response = self._client.put(f"{_V2}/pages/{page_id}", json=payload)
        response.raise_for_status()
        return Page.from_api_response(response.json())

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()


@dataclass
class PageCreateParams:
    """Parameters for creating a page."""

    space_key: str
    title: str
    body: str
    parent_id: str | None = None


@dataclass
class PageUpdateParams:
    """Parameters for updating a page."""

    title: str | None = None
    body: str | None = None
