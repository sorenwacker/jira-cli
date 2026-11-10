"""Tests that `new` preserves quoted multi-word option values."""

from unittest.mock import MagicMock

import pytest

from jira_cli.shell import JiraShell


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock Jira client."""
    return MagicMock()


@pytest.fixture
def shell(mock_client: MagicMock) -> JiraShell:
    """Shell instance with mock client."""
    return JiraShell(client=mock_client)


class TestDoNewQuoting:
    """Quoted multi-word option values must survive intact."""

    def test_description_with_spaces(
        self, shell: JiraShell, mock_client: MagicMock
    ) -> None:
        shell.do_new('PROJ "my summary" --description "foo bar"')
        params = mock_client.create_issue.call_args[0][0]
        assert params.description == "foo bar"

    def test_description_single_word(
        self, shell: JiraShell, mock_client: MagicMock
    ) -> None:
        shell.do_new('PROJ "my summary" --description foo')
        params = mock_client.create_issue.call_args[0][0]
        assert params.description == "foo"
