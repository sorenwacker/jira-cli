"""Data models for Jira entities."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

__all__ = [
    "Attachment",
    "Comment",
    "Issue",
    "Project",
    "Transition",
    "User",
]


def _parse_jira_datetime(value: str) -> datetime:
    """Parse Jira API datetime string to datetime object."""
    return datetime.fromisoformat(value.replace("+0000", "+00:00"))


def _get_display_name(fields: dict[str, Any], field_name: str) -> str | None:
    """Extract display name from a nested field."""
    field_data = fields.get(field_name)
    return field_data.get("displayName") if field_data else None


def _get_nested_name(fields: dict[str, Any], field_name: str) -> str | None:
    """Extract 'name' from a nested field."""
    field_data = fields.get(field_name)
    return field_data.get("name") if field_data else None


class Attachment(BaseModel):
    """Represents a Jira attachment."""

    id: str
    filename: str
    size: int
    mime_type: str
    content_url: str
    author: str
    created: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Attachment":
        """Create an Attachment from Jira API response."""
        return cls(
            id=data["id"],
            filename=data["filename"],
            size=data["size"],
            mime_type=data["mimeType"],
            content_url=data["content"],
            author=data["author"]["displayName"],
            created=_parse_jira_datetime(data["created"]),
        )


class Issue(BaseModel):
    """Represents a Jira issue."""

    key: str
    summary: str
    status: str
    assignee: str | None
    reporter: str | None
    project: str
    priority: str | None
    created: datetime
    updated: datetime
    due_date: date | None = None
    description: str | None
    attachments: list[Attachment] = []
    labels: list[str] = []
    components: list[str] = []
    fix_versions: list[str] = []

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Issue":
        """Create an Issue from Jira API response."""
        fields = data["fields"]
        raw_attachments = fields.get("attachment", [])
        attachments = [Attachment.from_api_response(a) for a in raw_attachments]

        return cls(
            key=data["key"],
            summary=fields["summary"],
            status=fields["status"]["name"],
            assignee=_get_display_name(fields, "assignee"),
            reporter=_get_display_name(fields, "reporter"),
            project=fields["project"]["key"],
            priority=_get_nested_name(fields, "priority"),
            created=_parse_jira_datetime(fields["created"]),
            updated=_parse_jira_datetime(fields["updated"]),
            due_date=fields.get("duedate"),
            description=_extract_text_from_adf(fields.get("description")),
            attachments=attachments,
            labels=fields.get("labels", []),
            components=[c["name"] for c in fields.get("components", []) or []],
            fix_versions=[v["name"] for v in fields.get("fixVersions", []) or []],
        )


class Comment(BaseModel):
    """Represents a Jira comment."""

    id: str
    author: str
    body: str
    created: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Comment":
        """Create a Comment from Jira API response."""
        body = _extract_text_from_adf(data.get("body")) or ""

        return cls(
            id=data["id"],
            author=data["author"]["displayName"],
            body=body,
            created=_parse_jira_datetime(data["created"]),
        )


class Transition(BaseModel):
    """Represents a Jira status transition."""

    id: str
    name: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Transition":
        """Create a Transition from Jira API response."""
        return cls(
            id=data["id"],
            name=data["name"],
        )


class Project(BaseModel):
    """Represents a Jira project."""

    key: str
    name: str
    project_type: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Project":
        """Create a Project from Jira API response."""
        return cls(
            key=data["key"],
            name=data["name"],
            project_type=data.get("projectTypeKey", ""),
        )


class User(BaseModel):
    """Represents a Jira user."""

    account_id: str
    display_name: str
    email: str | None
    active: bool
    account_type: str
    avatar_url: str | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "User":
        """Create a User from Jira API response."""
        avatar_url = None
        if data.get("avatarUrls"):
            avatar_url = data["avatarUrls"].get("48x48")

        return cls(
            account_id=data["accountId"],
            display_name=data.get("displayName", ""),
            email=data.get("emailAddress"),
            active=data.get("active", True),
            account_type=data.get("accountType", "atlassian"),
            avatar_url=avatar_url,
        )


_ADF_BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading",
        "blockquote",
        "codeBlock",
        "bulletList",
        "orderedList",
        "listItem",
        "rule",
        "panel",
    }
)


def _extract_adf_node_text(node: dict[str, Any]) -> str:
    """Recursively extract text from a single ADF node.

    Block-level children are separated by a newline so distinct paragraphs and
    list items do not run together, mirroring the Confluence renderer.
    """
    if node.get("type") == "text":
        text = node.get("text", "")
        return str(text) if text else ""
    content: list[dict[str, Any]] = node.get("content", [])
    parts: list[str] = []
    for child in content:
        child_text = _extract_adf_node_text(child)
        if child.get("type") in _ADF_BLOCK_TYPES and not child_text.endswith("\n"):
            child_text += "\n"
        parts.append(child_text)
    return "".join(parts)


def _extract_text_from_adf(adf: dict[str, Any] | None) -> str | None:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if adf is None:
        return None
    text = _extract_adf_node_text(adf)
    return text.strip() or None
