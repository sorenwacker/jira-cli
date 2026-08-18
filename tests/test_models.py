"""Tests for Jira data models."""

from datetime import date

from jira_cli.models import (
    Attachment,
    Comment,
    Issue,
    Status,
    Transition,
    _extract_text_from_adf,
)


def _paragraph(text: str) -> dict:
    """Build an ADF paragraph node with a single text run."""
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _doc(*blocks: dict) -> dict:
    """Wrap block nodes in an ADF doc."""
    return {"type": "doc", "version": 1, "content": list(blocks)}


class TestExtractTextFromAdf:
    """Tests for _extract_text_from_adf block handling."""

    def test_none_returns_none(self) -> None:
        """A missing ADF document yields None."""
        assert _extract_text_from_adf(None) is None

    def test_single_paragraph_has_no_trailing_newline(self) -> None:
        """A single paragraph extracts to its text only."""
        assert _extract_text_from_adf(_doc(_paragraph("First."))) == "First."

    def test_blocks_separated_by_newline(self) -> None:
        """Distinct block nodes are separated, not concatenated."""
        adf = _doc(_paragraph("First."), _paragraph("Second."))
        assert _extract_text_from_adf(adf) == "First.\nSecond."

    def test_list_items_separated(self) -> None:
        """Bullet list items each render on their own line."""
        adf = _doc(
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [_paragraph("one")]},
                    {"type": "listItem", "content": [_paragraph("two")]},
                ],
            }
        )
        assert _extract_text_from_adf(adf) == "one\ntwo"


class TestIssue:
    """Tests for Issue model."""

    def test_from_api_response(self, sample_issue_response: dict) -> None:
        """Issue can be created from Jira API response."""
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.key == "PROJ-123"
        assert issue.summary == "Test issue summary"
        assert issue.status == "To Do"
        assert issue.assignee == "Test User"
        assert issue.reporter == "Reporter User"
        assert issue.project == "PROJ"
        assert issue.priority == "Medium"
        assert issue.description == "Issue description"
        assert issue.labels == ["bug", "high-priority"]

    def test_from_api_response_no_assignee(self, sample_issue_response: dict) -> None:
        """Issue handles missing assignee."""
        sample_issue_response["fields"]["assignee"] = None
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.assignee is None

    def test_from_api_response_no_reporter(self, sample_issue_response: dict) -> None:
        """Issue handles missing reporter."""
        sample_issue_response["fields"]["reporter"] = None
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.reporter is None

    def test_from_api_response_no_description(
        self, sample_issue_response: dict
    ) -> None:
        """Issue handles missing description."""
        sample_issue_response["fields"]["description"] = None
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.description is None

    def test_from_api_response_no_priority(self, sample_issue_response: dict) -> None:
        """Issue handles missing priority."""
        sample_issue_response["fields"]["priority"] = None
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.priority is None

    def test_from_api_response_no_labels(self, sample_issue_response: dict) -> None:
        """Issue handles missing labels field."""
        del sample_issue_response["fields"]["labels"]
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.labels == []

    def test_from_api_response_empty_labels(self, sample_issue_response: dict) -> None:
        """Issue handles empty labels array."""
        sample_issue_response["fields"]["labels"] = []
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.labels == []

    def test_from_api_response_metadata_fields(
        self, sample_issue_response: dict
    ) -> None:
        """Issue parses components, fix versions, and due date."""
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.components == ["API", "UI"]
        assert issue.fix_versions == ["1.2.0"]
        assert issue.due_date == date(2024, 2, 1)

    def test_from_api_response_no_metadata_fields(
        self, sample_issue_response: dict
    ) -> None:
        """Issue handles missing components, fix versions, and due date."""
        del sample_issue_response["fields"]["components"]
        del sample_issue_response["fields"]["fixVersions"]
        sample_issue_response["fields"]["duedate"] = None
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.components == []
        assert issue.fix_versions == []
        assert issue.due_date is None


class TestStatus:
    """Tests for Status model."""

    def test_from_api_response(self) -> None:
        """Status parses name and category."""
        status = Status.from_api_response(
            {"name": "In Review", "statusCategory": {"name": "In Progress"}}
        )

        assert status.name == "In Review"
        assert status.category == "In Progress"

    def test_from_api_response_no_category(self) -> None:
        """Status handles missing statusCategory."""
        status = Status.from_api_response({"name": "Odd"})

        assert status.name == "Odd"
        assert status.category == ""


class TestComment:
    """Tests for Comment model."""

    def test_from_api_response(self, sample_comments_response: dict) -> None:
        """Comment can be created from Jira API response."""
        comment_data = sample_comments_response["comments"][0]
        comment = Comment.from_api_response(comment_data)

        assert comment.id == "10001"
        assert comment.author == "Test User"
        assert comment.body == "First comment"

    def test_from_api_response_list(self, sample_comments_response: dict) -> None:
        """Multiple comments can be parsed."""
        comments = [
            Comment.from_api_response(c) for c in sample_comments_response["comments"]
        ]

        assert len(comments) == 2
        assert comments[0].body == "First comment"
        assert comments[1].body == "Second comment"


class TestTransition:
    """Tests for Transition model."""

    def test_from_api_response(self, sample_transitions_response: dict) -> None:
        """Transition can be created from Jira API response."""
        transition_data = sample_transitions_response["transitions"][1]
        transition = Transition.from_api_response(transition_data)

        assert transition.id == "21"
        assert transition.name == "In Progress"

    def test_from_api_response_list(self, sample_transitions_response: dict) -> None:
        """Multiple transitions can be parsed."""
        transitions = [
            Transition.from_api_response(t)
            for t in sample_transitions_response["transitions"]
        ]

        assert len(transitions) == 3
        assert [t.name for t in transitions] == ["To Do", "In Progress", "Done"]


class TestAttachment:
    """Tests for Attachment model."""

    def test_from_api_response(self, sample_attachment_response: list[dict]) -> None:
        """Attachment can be created from Jira API response."""
        attachment = Attachment.from_api_response(sample_attachment_response[0])

        assert attachment.id == "10001"
        assert attachment.filename == "screenshot.png"
        assert attachment.size == 251000
        assert attachment.mime_type == "image/png"
        assert (
            attachment.content_url
            == "https://test.atlassian.net/secure/attachment/10001/screenshot.png"
        )
        assert attachment.author == "Test User"

    def test_from_api_response_list(
        self, sample_attachment_response: list[dict]
    ) -> None:
        """Multiple attachments can be parsed."""
        attachments = [
            Attachment.from_api_response(a) for a in sample_attachment_response
        ]

        assert len(attachments) == 2
        assert attachments[0].filename == "screenshot.png"
        assert attachments[1].filename == "data.csv"


class TestIssueAttachments:
    """Tests for Issue model attachment handling."""

    def test_issue_with_attachments(self, sample_issue_response: dict) -> None:
        """Issue correctly parses attachments."""
        issue = Issue.from_api_response(sample_issue_response)

        assert len(issue.attachments) == 2
        assert issue.attachments[0].filename == "screenshot.png"
        assert issue.attachments[1].filename == "data.csv"

    def test_issue_no_attachments(self, sample_issue_response: dict) -> None:
        """Issue handles missing attachments field."""
        sample_issue_response["fields"]["attachment"] = []
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.attachments == []

    def test_issue_attachments_field_missing(self, sample_issue_response: dict) -> None:
        """Issue handles when attachment field is not present."""
        del sample_issue_response["fields"]["attachment"]
        issue = Issue.from_api_response(sample_issue_response)

        assert issue.attachments == []
