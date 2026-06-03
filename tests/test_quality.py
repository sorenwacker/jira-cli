"""Tests for issue quality scoring module."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jira_cli.models import Attachment, Issue
from jira_cli.quality import (
    calculate_quality_score,
    format_age,
    generate_quality_report,
)


@dataclass
class IssueParams:  # pylint: disable=too-many-instance-attributes
    """Parameters for creating test issues."""

    key: str = "PROJ-1"
    summary: str = "Test issue"
    description: str | None = None
    labels: list[str] = field(default_factory=list)
    assignee: str | None = None
    priority: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    days_since_update: int = 0
    days_since_created: int = 0


def make_issue(params: IssueParams | None = None, **kwargs: object) -> Issue:
    """Create an Issue with specified attributes for testing."""
    if params is None:
        params = IssueParams(**kwargs)  # type: ignore[arg-type]
    now = datetime.now(UTC)
    return Issue(
        key=params.key,
        summary=params.summary,
        status="To Do",
        assignee=params.assignee,
        reporter="Reporter",
        project="PROJ",
        priority=params.priority,
        created=now - timedelta(days=params.days_since_created),
        updated=now - timedelta(days=params.days_since_update),
        description=params.description,
        attachments=params.attachments,
        labels=params.labels,
    )


class TestCalculateQualityScore:
    """Tests for calculate_quality_score function."""

    def test_empty_issue_minimum_score(self) -> None:
        """Issue with no quality attributes gets minimum score of 1."""
        issue = make_issue(days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 1

    def test_short_description_one_point(self) -> None:
        """Short description (<= 50 chars) adds 1 point."""
        issue = make_issue(description="Short desc", days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 1

    def test_long_description_three_points(self) -> None:
        """Long description (> 50 chars) adds 3 points."""
        long_desc = "This is a detailed description that exceeds fifty characters."
        issue = make_issue(description=long_desc, days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 3

    def test_labels_two_points(self) -> None:
        """Labels add 2 points."""
        issue = make_issue(labels=["bug"], days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 2

    def test_assignee_two_points(self) -> None:
        """Assignee adds 2 points."""
        issue = make_issue(assignee="User", days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 2

    def test_priority_one_point(self) -> None:
        """Priority adds 1 point."""
        issue = make_issue(priority="High", days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 1

    def test_attachments_one_point(self) -> None:
        """Attachments add 1 point."""
        attachment = Attachment(
            id="1",
            filename="file.txt",
            size=100,
            mime_type="text/plain",
            content_url="http://example.com/file",
            author="User",
            created=datetime.now(UTC),
        )
        issue = make_issue(attachments=[attachment], days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 1

    def test_recent_activity_one_point(self) -> None:
        """Recent update (within 30 days) adds 1 point."""
        issue = make_issue(days_since_update=15)
        score = calculate_quality_score(issue)
        assert score == 1

    def test_old_activity_no_points(self) -> None:
        """Old update (>30 days) adds no points."""
        issue = make_issue(days_since_update=31)
        score = calculate_quality_score(issue)
        assert score == 1  # minimum score

    def test_maximum_score(self) -> None:
        """Issue with all quality attributes scores 10."""
        attachment = Attachment(
            id="1",
            filename="file.txt",
            size=100,
            mime_type="text/plain",
            content_url="http://example.com/file",
            author="User",
            created=datetime.now(UTC),
        )
        long_desc = "This is a comprehensive description that exceeds fifty chars."
        issue = make_issue(
            description=long_desc,
            labels=["feature", "priority"],
            assignee="Developer",
            priority="High",
            attachments=[attachment],
            days_since_update=5,
        )
        score = calculate_quality_score(issue)
        assert score == 10

    def test_partial_score(self) -> None:
        """Issue with some quality attributes scores correctly."""
        issue = make_issue(
            description="Detailed issue description that is longer than fifty chars",
            assignee="Developer",
            days_since_update=5,
        )
        # 3 (long desc) + 2 (assignee) + 1 (recent) = 6
        score = calculate_quality_score(issue)
        assert score == 6


class TestFormatAge:
    """Tests for format_age function."""

    def test_today(self) -> None:
        """Same day returns 'today'."""
        now = datetime.now(UTC)
        assert format_age(now) == "today"

    def test_one_day(self) -> None:
        """One day ago returns '1 day'."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        assert format_age(yesterday) == "1 day"

    def test_multiple_days(self) -> None:
        """Multiple days returns 'N days'."""
        five_days = datetime.now(UTC) - timedelta(days=5)
        assert format_age(five_days) == "5 days"

    def test_one_week(self) -> None:
        """7-13 days returns '1 week'."""
        one_week = datetime.now(UTC) - timedelta(days=10)
        assert format_age(one_week) == "1 week"

    def test_multiple_weeks(self) -> None:
        """14-29 days returns 'N weeks'."""
        three_weeks = datetime.now(UTC) - timedelta(days=21)
        assert format_age(three_weeks) == "3 weeks"

    def test_one_month(self) -> None:
        """30-59 days returns '1 month'."""
        one_month = datetime.now(UTC) - timedelta(days=45)
        assert format_age(one_month) == "1 month"

    def test_multiple_months(self) -> None:
        """60-364 days returns 'N months'."""
        six_months = datetime.now(UTC) - timedelta(days=180)
        assert format_age(six_months) == "6 months"

    def test_one_year(self) -> None:
        """365-729 days returns '1 year'."""
        one_year = datetime.now(UTC) - timedelta(days=400)
        assert format_age(one_year) == "1 year"

    def test_multiple_years(self) -> None:
        """730+ days returns 'N years'."""
        three_years = datetime.now(UTC) - timedelta(days=1100)
        assert format_age(three_years) == "3 years"


class TestGenerateQualityReport:
    """Tests for generate_quality_report function."""

    def test_empty_list(self) -> None:
        """Empty issue list returns empty report."""
        report = generate_quality_report([])
        assert report == []

    def test_single_issue(self) -> None:
        """Single issue generates correct report entry."""
        issue = make_issue(
            key="PROJ-123",
            summary="Test summary",
            assignee="User",
            days_since_created=5,
        )
        report = generate_quality_report([issue])

        assert len(report) == 1
        entry = report[0]
        assert entry["key"] == "PROJ-123"
        assert entry["summary"] == "Test summary"
        assert entry["creator"] == "Reporter"
        assert entry["age"] == "5 days"
        assert entry["status"] == "To Do"
        assert entry["rating"] == 3  # assignee(2) + recent activity(1)

    def test_multiple_issues(self) -> None:
        """Multiple issues generate correct report entries."""
        issues = [
            make_issue(key="PROJ-1", summary="First"),
            make_issue(key="PROJ-2", summary="Second"),
        ]
        report = generate_quality_report(issues)

        assert len(report) == 2
        assert report[0]["key"] == "PROJ-1"
        assert report[1]["key"] == "PROJ-2"

    def test_report_includes_all_fields(self) -> None:
        """Report entry contains all expected fields."""
        issue = make_issue()
        report = generate_quality_report([issue])

        entry = report[0]
        assert "key" in entry
        assert "summary" in entry
        assert "creator" in entry
        assert "age" in entry
        assert "status" in entry
        assert "rating" in entry
