"""Tests for Jira API client status listing."""

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
