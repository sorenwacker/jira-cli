"""Data models for Confluence entities."""

from typing import Any

from pydantic import BaseModel

__all__ = ["Page", "Space"]


class Space(BaseModel):
    """Represents a Confluence space."""

    id: str
    key: str
    name: str
    type: str
    status: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Space":
        """Create a Space from a Confluence API response.

        Args:
            data: Space object from the v2 spaces endpoint.

        Returns:
            Space instance.
        """
        return cls(
            id=str(data["id"]),
            key=data["key"],
            name=data["name"],
            type=data.get("type", ""),
            status=data.get("status", ""),
        )


class Page(BaseModel):
    """Represents a Confluence page."""

    id: str
    title: str
    space_id: str | None = None
    status: str = ""
    version: int | None = None
    body: str | None = None
    url: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Page":
        """Create a Page from a v2 page response.

        Args:
            data: Page object from the v2 pages endpoint.

        Returns:
            Page instance including its storage-format body when present.
        """
        space_id = data.get("spaceId")
        version = data.get("version", {}).get("number")
        body = data.get("body", {}).get("storage", {}).get("value")
        url = data.get("_links", {}).get("webui")
        return cls(
            id=str(data["id"]),
            title=data["title"],
            space_id=str(space_id) if space_id is not None else None,
            status=data.get("status", ""),
            version=version,
            body=body,
            url=url,
        )

    @classmethod
    def from_search_result(cls, data: dict[str, Any]) -> "Page":
        """Create a Page from a v1 search result.

        Args:
            data: A single result from the search endpoint, containing a nested
                ``content`` object.

        Returns:
            Page instance without body or version (not provided by search).
        """
        content = data.get("content", {})
        return cls(
            id=str(content["id"]),
            title=content.get("title", ""),
            status=content.get("status", ""),
            url=data.get("url"),
        )
