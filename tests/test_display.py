"""Tests for display formatting utilities."""

from datetime import UTC, datetime

from jira_cli.display import (
    build_comment_panel,
    build_issue_content,
    format_size,
    truncate,
)
from jira_cli.models import Attachment, Comment, Issue


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert format_size(3 * 1024 * 1024 * 1024) == "3.0 GB"


class TestTruncate:
    """Tests for truncate function."""

    def test_short_text_unchanged(self):
        assert truncate("hello", max_len=10) == "hello"

    def test_long_text_truncated(self):
        assert truncate("hello world", max_len=5) == "hello..."

    def test_exact_length_unchanged(self):
        assert truncate("hello", max_len=5) == "hello"


class TestBuildIssueContent:
    """Tests for build_issue_content function."""

    def test_basic_issue(self):
        issue = Issue(
            key="PROJ-1",
            summary="Test issue",
            status="To Do",
            assignee="Alice",
            reporter="Bob",
            project="PROJ",
            priority="High",
            created=datetime(2024, 1, 15, tzinfo=UTC),
            updated=datetime(2024, 1, 16, tzinfo=UTC),
            description="Test description",
            attachments=[],
            labels=[],
        )
        content = build_issue_content(issue)
        text = content.plain

        assert "Test issue" in text
        assert "To Do" in text
        assert "Alice" in text
        assert "Test description" in text

    def test_issue_without_description(self):
        issue = Issue(
            key="PROJ-1",
            summary="Test issue",
            status="To Do",
            assignee=None,
            reporter=None,
            project="PROJ",
            priority=None,
            created=datetime(2024, 1, 15, tzinfo=UTC),
            updated=datetime(2024, 1, 16, tzinfo=UTC),
            description=None,
            attachments=[],
            labels=[],
        )
        content = build_issue_content(issue)
        text = content.plain

        assert "Unassigned" in text
        assert "Description" not in text

    def test_issue_with_attachments(self):
        attachment = Attachment(
            id="1",
            filename="test.pdf",
            size=1024 * 1024,
            mime_type="application/pdf",
            content_url="https://example.com/test.pdf",
            author="Alice",
            created=datetime(2024, 1, 15, tzinfo=UTC),
        )
        issue = Issue(
            key="PROJ-1",
            summary="Test issue",
            status="To Do",
            assignee=None,
            reporter=None,
            project="PROJ",
            priority=None,
            created=datetime(2024, 1, 15, tzinfo=UTC),
            updated=datetime(2024, 1, 16, tzinfo=UTC),
            description=None,
            attachments=[attachment],
            labels=[],
        )
        content = build_issue_content(issue, include_attachments=True)
        text = content.plain

        assert "Attachments" in text
        assert "test.pdf" in text
        assert "1.0 MB" in text

    def test_issue_without_attachments_flag(self):
        attachment = Attachment(
            id="1",
            filename="test.pdf",
            size=1024,
            mime_type="application/pdf",
            content_url="https://example.com/test.pdf",
            author="Alice",
            created=datetime(2024, 1, 15, tzinfo=UTC),
        )
        issue = Issue(
            key="PROJ-1",
            summary="Test issue",
            status="To Do",
            assignee=None,
            reporter=None,
            project="PROJ",
            priority=None,
            created=datetime(2024, 1, 15, tzinfo=UTC),
            updated=datetime(2024, 1, 16, tzinfo=UTC),
            description=None,
            attachments=[attachment],
            labels=[],
        )
        content = build_issue_content(issue, include_attachments=False)
        text = content.plain

        assert "Attachments" not in text


class TestBuildCommentPanel:
    """Tests for build_comment_panel function."""

    def test_builds_panel(self):
        from rich.text import Text

        comment = Comment(
            id="123",
            author="Alice",
            body="This is a comment",
            created=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        )
        panel = build_comment_panel(comment)

        assert panel is not None
        # Panel contains a Text renderable
        renderable = panel.renderable
        assert isinstance(renderable, Text)
        text = renderable.plain
        assert "Alice" in text
        assert "This is a comment" in text
        assert "123" in text
