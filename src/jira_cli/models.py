"""Data models for Jira entities."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
            created=datetime.fromisoformat(data["created"].replace("+0000", "+00:00")),
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
    description: str | None
    attachments: list[Attachment] = []

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Issue":
        """Create an Issue from Jira API response."""
        fields = data["fields"]

        # Extract assignee display name
        assignee = None
        if fields.get("assignee"):
            assignee = fields["assignee"].get("displayName")

        # Extract reporter display name
        reporter = None
        if fields.get("reporter"):
            reporter = fields["reporter"].get("displayName")

        # Extract priority name
        priority = None
        if fields.get("priority"):
            priority = fields["priority"].get("name")

        # Extract description text from ADF format
        description = _extract_text_from_adf(fields.get("description"))

        # Extract attachments
        attachments = [
            Attachment.from_api_response(a)
            for a in fields.get("attachment", [])
        ]

        return cls(
            key=data["key"],
            summary=fields["summary"],
            status=fields["status"]["name"],
            assignee=assignee,
            reporter=reporter,
            project=fields["project"]["key"],
            priority=priority,
            created=datetime.fromisoformat(fields["created"].replace("+0000", "+00:00")),
            updated=datetime.fromisoformat(fields["updated"].replace("+0000", "+00:00")),
            description=description,
            attachments=attachments,
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
            created=datetime.fromisoformat(data["created"].replace("+0000", "+00:00")),
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


def _extract_text_from_adf(adf: dict[str, Any] | None) -> str | None:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if adf is None:
        return None

    def extract_content(node: dict[str, Any]) -> str:
        """Recursively extract text from ADF nodes."""
        if node.get("type") == "text":
            return node.get("text", "")

        content = node.get("content", [])
        return "".join(extract_content(child) for child in content)

    return extract_content(adf) or None
