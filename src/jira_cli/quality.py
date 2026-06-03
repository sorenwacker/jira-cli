"""Issue quality scoring and reporting."""

from collections.abc import Callable
from datetime import UTC, datetime

from jira_cli.models import Issue

__all__ = [
    "calculate_quality_score",
    "format_age",
    "generate_quality_report",
]

# Scoring thresholds
DESCRIPTION_MIN_LENGTH = 50
RECENT_ACTIVITY_DAYS = 30

# Time period thresholds (in days)
DAYS_PER_WEEK = 7
TWO_WEEKS = 14
DAYS_PER_MONTH = 30
TWO_MONTHS = 60
DAYS_PER_YEAR = 365
TWO_YEARS = 730


def _score_description(issue: Issue) -> int:
    """Score description: 3 points if >50 chars, 1 point if present but short."""
    if not issue.description:
        return 0
    return 3 if len(issue.description) > DESCRIPTION_MIN_LENGTH else 1


def _score_metadata(issue: Issue) -> int:
    """Score labels, assignee, priority, and attachments."""
    score = 0
    if issue.labels:
        score += 2
    if issue.assignee:
        score += 2
    if issue.priority:
        score += 1
    if issue.attachments:
        score += 1
    return score


def _score_activity(issue: Issue) -> int:
    """Score 1 point if updated in last 30 days."""
    now = datetime.now(UTC)
    days_since_update = (now - issue.updated).days
    return 1 if days_since_update <= RECENT_ACTIVITY_DAYS else 0


def calculate_quality_score(issue: Issue) -> int:
    """Calculate quality score 1-10 for an issue.

    Scoring criteria:
    - Description: +3 if present and >50 chars, +1 if present but short
    - Labels: +2 if has labels
    - Assignee: +2 if assigned
    - Priority: +1 if priority set
    - Attachments: +1 if has attachments
    - Activity: +1 if updated in last 30 days

    Args:
        issue: The Issue to score.

    Returns:
        Quality score from 1 to 10.
    """
    score = _score_description(issue) + _score_metadata(issue) + _score_activity(issue)
    return max(1, score)


def _format_days(days: int) -> str:
    """Format days as human-readable string."""
    if days == 0:
        return "today"
    if days == 1:
        return "1 day"
    return f"{days} days"


def _format_weeks(days: int) -> str:
    """Format weeks from days."""
    if days < TWO_WEEKS:
        return "1 week"
    weeks = days // DAYS_PER_WEEK
    return f"{weeks} weeks"


def _format_months(days: int) -> str:
    """Format months from days."""
    if days < TWO_MONTHS:
        return "1 month"
    months = days // DAYS_PER_MONTH
    return f"{months} months"


def _format_years(days: int) -> str:
    """Format years from days."""
    if days < TWO_YEARS:
        return "1 year"
    years = days // DAYS_PER_YEAR
    return f"{years} years"


# Age formatters: (max_days, formatter_function)
_AGE_FORMATTERS: list[tuple[int, Callable[[int], str]]] = [
    (DAYS_PER_WEEK, _format_days),
    (DAYS_PER_MONTH, _format_weeks),
    (DAYS_PER_YEAR, _format_months),
]


def format_age(created: datetime) -> str:
    """Format issue age as human-readable string.

    Args:
        created: The creation datetime.

    Returns:
        Human-readable age string (e.g., "5 days", "2 weeks", "3 months").
    """
    now = datetime.now(UTC)
    days = (now - created).days

    for max_days, formatter in _AGE_FORMATTERS:
        if days < max_days:
            return formatter(days)
    return _format_years(days)


def generate_quality_report(issues: list[Issue]) -> list[dict[str, str | int | None]]:
    """Generate quality report for a list of issues.

    Args:
        issues: List of Issue objects to analyze.

    Returns:
        List of report entries with key, summary, creator, age, status, rating.
    """
    return [
        {
            "key": issue.key,
            "summary": issue.summary,
            "creator": issue.reporter,
            "age": format_age(issue.created),
            "status": issue.status,
            "rating": calculate_quality_score(issue),
        }
        for issue in issues
    ]
