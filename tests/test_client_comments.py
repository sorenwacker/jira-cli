"""Tests for Jira API client comment operations."""

import httpx
import respx

from jira_cli.client import JiraClient


class TestJiraClientComments:
    """Tests for comment functionality."""

    @respx.mock
    def test_get_comments(
        self,
        jira_client: JiraClient,
        sample_comments_response: dict,
    ) -> None:
        """Can retrieve comments for an issue."""
        respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
            return_value=httpx.Response(200, json=sample_comments_response)
        )

        comments = jira_client.get_comments("PROJ-123")

        assert len(comments) == 2
        assert comments[0].body == "First comment"

    @respx.mock
    def test_add_comment(self, jira_client: JiraClient) -> None:
        """Can add a comment to an issue."""
        respx.post("https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "10003",
                    "author": {"displayName": "Test User"},
                    "body": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "New comment"}],
                            }
                        ],
                    },
                    "created": "2024-01-15T13:00:00.000+0000",
                },
            )
        )

        comment = jira_client.add_comment("PROJ-123", "New comment")

        assert comment.id == "10003"
        assert comment.body == "New comment"

    @respx.mock
    def test_update_comment(self, jira_client: JiraClient) -> None:
        """Can update an existing comment."""
        route = respx.put(
            "https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment/10001"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "10001",
                    "author": {"displayName": "Test User"},
                    "body": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Updated comment"}
                                ],
                            }
                        ],
                    },
                    "created": "2024-01-15T13:00:00.000+0000",
                },
            )
        )

        jira_client.update_comment("PROJ-123", "10001", "Updated comment")

        assert route.called
