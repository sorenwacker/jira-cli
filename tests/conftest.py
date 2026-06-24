"""Pytest fixtures for jira-cli tests."""

import pytest

from jira_cli.client import JiraClient
from jira_cli.config import ConfluenceConfig, JiraConfig
from jira_cli.confluence_client import ConfluenceClient


@pytest.fixture
def jira_config() -> JiraConfig:
    """Sample Jira configuration for testing."""
    return JiraConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token-123",
    )


@pytest.fixture
def jira_client(jira_config: JiraConfig) -> JiraClient:
    """Jira client configured for testing."""
    return JiraClient(config=jira_config)


@pytest.fixture
def confluence_config() -> ConfluenceConfig:
    """Sample Confluence configuration for testing."""
    return ConfluenceConfig(
        url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token-123",
    )


@pytest.fixture
def confluence_client(confluence_config: ConfluenceConfig) -> ConfluenceClient:
    """Confluence client configured for testing."""
    return ConfluenceClient(config=confluence_config)


@pytest.fixture
def sample_spaces_response() -> dict:
    """Sample Confluence API response for listing spaces."""
    return {
        "results": [
            {
                "id": "111",
                "key": "DEV",
                "name": "Development",
                "type": "global",
                "status": "current",
            },
            {
                "id": "222",
                "key": "DOCS",
                "name": "Documentation",
                "type": "global",
                "status": "current",
            },
        ],
        "_links": {},
    }


@pytest.fixture
def sample_page_response() -> dict:
    """Sample Confluence API response for a single page."""
    return {
        "id": "12345",
        "status": "current",
        "title": "Test Page",
        "spaceId": "111",
        "version": {"number": 3},
        "body": {
            "storage": {
                "representation": "storage",
                "value": "<p>Page <strong>body</strong> text</p>",
            }
        },
        "_links": {"webui": "/spaces/DEV/pages/12345/Test+Page"},
    }


@pytest.fixture
def sample_confluence_search_response() -> dict:
    """Sample Confluence API response for CQL search."""
    return {
        "results": [
            {
                "content": {
                    "id": "12345",
                    "type": "page",
                    "status": "current",
                    "title": "Test Page",
                },
                "url": "/spaces/DEV/pages/12345/Test+Page",
            },
            {
                "content": {
                    "id": "67890",
                    "type": "page",
                    "status": "current",
                    "title": "Another Page",
                },
                "url": "/spaces/DEV/pages/67890/Another+Page",
            },
        ],
        "_links": {},
    }


@pytest.fixture
def sample_attachment_response() -> list[dict]:
    """Sample Jira API response for attachments."""
    return [
        {
            "id": "10001",
            "filename": "screenshot.png",
            "size": 251000,
            "mimeType": "image/png",
            "content": "https://test.atlassian.net/secure/attachment/10001/screenshot.png",
            "author": {"displayName": "Test User"},
            "created": "2024-01-15T11:00:00.000+0000",
        },
        {
            "id": "10002",
            "filename": "data.csv",
            "size": 1250000,
            "mimeType": "text/csv",
            "content": "https://test.atlassian.net/secure/attachment/10002/data.csv",
            "author": {"displayName": "Another User"},
            "created": "2024-01-15T12:00:00.000+0000",
        },
    ]


@pytest.fixture
def sample_issue_response(sample_attachment_response: list[dict]) -> dict:
    """Sample Jira API response for a single issue."""
    return {
        "key": "PROJ-123",
        "fields": {
            "summary": "Test issue summary",
            "status": {"name": "To Do"},
            "assignee": {
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            "reporter": {
                "displayName": "Reporter User",
                "emailAddress": "reporter@example.com",
            },
            "project": {"key": "PROJ", "name": "Test Project"},
            "priority": {"name": "Medium"},
            "created": "2024-01-15T10:30:00.000+0000",
            "updated": "2024-01-16T14:20:00.000+0000",
            "description": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Issue description"}],
                    }
                ],
            },
            "attachment": sample_attachment_response,
            "labels": ["bug", "high-priority"],
        },
    }


@pytest.fixture
def sample_search_response(sample_issue_response: dict) -> dict:
    """Sample Jira API response for search."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [sample_issue_response],
    }


@pytest.fixture
def sample_comments_response() -> dict:
    """Sample Jira API response for comments."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 2,
        "comments": [
            {
                "id": "10001",
                "author": {"displayName": "Test User"},
                "body": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "First comment"}],
                        }
                    ],
                },
                "created": "2024-01-15T11:00:00.000+0000",
            },
            {
                "id": "10002",
                "author": {"displayName": "Another User"},
                "body": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Second comment"}],
                        }
                    ],
                },
                "created": "2024-01-15T12:00:00.000+0000",
            },
        ],
    }


@pytest.fixture
def sample_transitions_response() -> dict:
    """Sample Jira API response for transitions."""
    return {
        "transitions": [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
    }


@pytest.fixture
def sample_projects_response() -> list[dict]:
    """Sample Jira API response for projects."""
    return [
        {
            "key": "DAT",
            "name": "Data Project",
            "projectTypeKey": "software",
        },
        {
            "key": "DEV",
            "name": "Development",
            "projectTypeKey": "software",
        },
    ]


def _user_john() -> dict:
    """Test user: John Doe with email."""
    return {
        "accountId": "abc123",
        "displayName": "John Doe",
        "emailAddress": "john@example.com",
        "active": True,
        "accountType": "atlassian",
        "avatarUrls": {"48x48": "https://avatar.example.com/john.png"},
    }


def _user_jane() -> dict:
    """Test user: Jane Smith with email."""
    return {
        "accountId": "def456",
        "displayName": "Jane Smith",
        "emailAddress": "jane@example.com",
        "active": True,
        "accountType": "atlassian",
        "avatarUrls": {"48x48": "https://avatar.example.com/jane.png"},
    }


def _user_no_email() -> dict:
    """Test user: No email."""
    return {
        "accountId": "ghi789",
        "displayName": "No Email User",
        "active": True,
        "accountType": "atlassian",
        "avatarUrls": {"48x48": "https://avatar.example.com/noemail.png"},
    }


def _user_bot() -> dict:
    """Test user: Automation bot (app type)."""
    return {
        "accountId": "app789",
        "displayName": "Automation Bot",
        "active": True,
        "accountType": "app",
        "avatarUrls": {"48x48": "https://avatar.example.com/bot.png"},
    }


@pytest.fixture
def sample_users_response() -> list[dict]:
    """Sample Jira API response for user search."""
    return [_user_john(), _user_jane(), _user_no_email(), _user_bot()]
