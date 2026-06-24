"""Confluence tools for the MCP server.

The tool functions are defined at module level so they can be unit tested
directly, and registered onto a shared FastMCP instance via ``register``.
"""

from typing import Any

from fastmcp import FastMCP

from jira_cli.config import load_confluence_config
from jira_cli.confluence_client import (
    ConfluenceClient,
    PageCreateParams,
    PageUpdateParams,
)
from jira_cli.confluence_models import Page, Space
from jira_cli.confluence_storage import storage_to_text

__all__ = [
    "confluence_search",
    "create_page",
    "get_page",
    "list_spaces",
    "register",
    "update_page",
]


def get_confluence_client() -> ConfluenceClient:
    """Get a configured Confluence client."""
    return ConfluenceClient(load_confluence_config())


def _page_summary(page: Page) -> dict[str, Any]:
    """Convert a Page to a lightweight dict."""
    return {"id": page.id, "title": page.title, "url": page.url}


def _space_to_dict(space: Space) -> dict[str, Any]:
    """Convert a Space to a dict."""
    return {
        "id": space.id,
        "key": space.key,
        "name": space.name,
        "type": space.type,
    }


def confluence_search(cql: str, limit: int = 25) -> list[dict[str, Any]]:
    """Search Confluence content using CQL.

    Args:
        cql: A Confluence Query Language expression.
        limit: Maximum number of results (default 25).

    Returns:
        List of matching pages with id, title, and url.
    """
    with get_confluence_client() as client:
        pages = client.search(cql, limit=limit)
        return [_page_summary(p) for p in pages]


def get_page(page_id: str) -> dict[str, Any]:
    """Get a Confluence page by ID, including its rendered body.

    Args:
        page_id: The numeric page ID.

    Returns:
        Page details with body rendered to plain text.
    """
    with get_confluence_client() as client:
        page = client.get_page(page_id)
        return {
            "id": page.id,
            "title": page.title,
            "space_id": page.space_id,
            "version": page.version,
            "url": page.url,
            "body": storage_to_text(page.body),
        }


def list_spaces(limit: int = 25) -> list[dict[str, Any]]:
    """List Confluence spaces.

    Args:
        limit: Maximum number of spaces (default 25).

    Returns:
        List of spaces with id, key, name, and type.
    """
    with get_confluence_client() as client:
        return [_space_to_dict(s) for s in client.list_spaces(limit=limit)]


def create_page(
    space_key: str,
    title: str,
    body: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Create a Confluence page from markdown.

    Args:
        space_key: The space key the page belongs to (e.g., "DEV").
        title: The page title.
        body: Page body as markdown.
        parent_id: Optional parent page ID to nest under.

    Returns:
        The created page summary.
    """
    params = PageCreateParams(
        space_key=space_key, title=title, body=body, parent_id=parent_id
    )
    with get_confluence_client() as client:
        return _page_summary(client.create_page(params))


def update_page(
    page_id: str,
    title: str | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """Update a Confluence page's title and/or body.

    Args:
        page_id: The numeric page ID.
        title: New title, or None to keep the existing one.
        body: New body as markdown, or None to keep the existing one.

    Returns:
        The updated page summary.
    """
    params = PageUpdateParams(title=title, body=body)
    with get_confluence_client() as client:
        return _page_summary(client.update_page(page_id, params))


def register(mcp: FastMCP) -> None:
    """Register the Confluence tools on a FastMCP server.

    Args:
        mcp: The FastMCP server instance to register tools on.
    """
    for fn in (
        confluence_search,
        get_page,
        list_spaces,
        create_page,
        update_page,
    ):
        mcp.tool()(fn)
