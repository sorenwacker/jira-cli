"""Tests for Jira API client instance metadata listing (statuses, issue types)."""

import httpx
import respx

from jira_cli.client import JiraClient


class TestJiraClientStatuses:
    """Tests for instance status listing."""

    @respx.mock
    def test_get_statuses(self, jira_client: JiraClient) -> None:
        """Can list the statuses defined in the instance."""
        respx.get("https://test.atlassian.net/rest/api/3/status").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"name": "To Do", "statusCategory": {"name": "To Do"}},
                    {"name": "In Review", "statusCategory": {"name": "In Progress"}},
                ],
            )
        )

        statuses = jira_client.get_statuses()

        assert [(s.name, s.category) for s in statuses] == [
            ("To Do", "To Do"),
            ("In Review", "In Progress"),
        ]


class TestJiraClientIssueTypes:
    """Tests for instance issue type listing."""

    @respx.mock
    def test_get_issue_types(self, jira_client: JiraClient) -> None:
        """Can list the issue types defined in the instance."""
        respx.get("https://test.atlassian.net/rest/api/3/issuetype").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"name": "Task", "subtask": False},
                    {"name": "Story", "subtask": False},
                    {"name": "Sub-task", "subtask": True},
                ],
            )
        )

        issue_types = jira_client.get_issue_types()

        assert [(t.name, t.subtask) for t in issue_types] == [
            ("Task", False),
            ("Story", False),
            ("Sub-task", True),
        ]
