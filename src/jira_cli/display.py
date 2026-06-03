"""Shared display formatting utilities."""

from rich.panel import Panel
from rich.text import Text

from jira_cli.models import Attachment, Comment, Issue

__all__ = [
    "build_comment_panel",
    "build_issue_content",
    "format_size",
    "truncate",
]

_SIZE_UNITS = [(1024**3, "GB"), (1024**2, "MB"), (1024, "KB")]


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for threshold, unit in _SIZE_UNITS:
        if size_bytes >= threshold:
            return f"{size_bytes / threshold:.1f} {unit}"
    return f"{size_bytes} B"


def truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    return text[:max_len] + "..." if len(text) > max_len else text


def build_issue_content(
    issue: Issue,
    *,
    include_attachments: bool = False,
) -> Text:
    """Build Rich Text content for displaying an issue.

    Args:
        issue: The Issue to format.
        include_attachments: Whether to include attachment details.

    Returns:
        Rich Text object with formatted issue content.
    """
    content = Text()
    fields = [
        ("Summary", issue.summary),
        ("Status", issue.status),
        ("Priority", issue.priority or "-"),
        ("Assignee", issue.assignee or "Unassigned"),
        ("Reporter", issue.reporter or "Unknown"),
        ("Project", issue.project),
        ("Created", issue.created.strftime("%Y-%m-%d %H:%M")),
        ("Updated", issue.updated.strftime("%Y-%m-%d %H:%M")),
    ]
    for label, value in fields:
        content.append(f"{label}: ", style="bold")
        content.append(f"{value}\n")

    if issue.description:
        content.append("\nDescription:\n", style="bold")
        content.append(issue.description)

    if include_attachments and issue.attachments:
        _append_attachments(content, issue.attachments)

    return content


def _append_attachments(content: Text, attachments: list[Attachment]) -> None:
    """Append attachment details to content."""
    content.append("\n\nAttachments:\n", style="bold")
    for att in attachments:
        content.append(f"  - {att.filename} ({format_size(att.size)})\n")
        content.append(f"    {att.content_url}\n")


def build_comment_panel(comment: Comment) -> Panel:
    """Build a Rich Panel for displaying a comment.

    Args:
        comment: The Comment to format.

    Returns:
        Rich Panel with formatted comment.
    """
    text = Text()
    text.append(f"{comment.author}", style="cyan")
    text.append(f" - {comment.created.strftime('%Y-%m-%d %H:%M')}", style="dim")
    text.append(f" [id: {comment.id}]\n", style="dim")
    text.append(comment.body)
    return Panel(text)
