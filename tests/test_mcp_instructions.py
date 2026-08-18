"""Tests for MCP server instructions and writing guidance."""

from unittest.mock import MagicMock, patch

from tests.test_mcp import create_mock_client, mock_config


class TestBuildInstructions:
    """The server instructions list the instance's ticket statuses."""

    @staticmethod
    def _client_with_instance_metadata() -> MagicMock:
        from jira_cli.models import IssueType, Status

        client = create_mock_client()
        client.get_statuses.return_value = [
            Status(name="To Do", category="To Do"),
            Status(name="In Review", category="In Progress"),
            Status(name="Done", category="Done"),
            Status(name="Done", category="Done"),
        ]
        client.get_issue_types.return_value = [
            IssueType(name="Task", subtask=False),
            IssueType(name="Story", subtask=False),
            IssueType(name="Story", subtask=False),
            IssueType(name="Sub-task", subtask=True),
        ]
        return client

    def test_instructions_include_statuses_by_category(self) -> None:
        """Fetched statuses appear in the instructions grouped by category."""
        from jira_cli.mcp import DEFAULT_WRITING_GUIDANCE, build_instructions

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.load_writing_guidance", return_value=None):
                with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                    mock_client_class.return_value = (
                        self._client_with_instance_metadata()
                    )

                    instructions = build_instructions()

        assert DEFAULT_WRITING_GUIDANCE in instructions
        assert "transition_issue" in instructions
        assert "In Progress: In Review" in instructions
        assert "Done: Done" in instructions
        assert "Done, Done" not in instructions

    def test_instructions_include_issue_types(self) -> None:
        """Fetched issue types appear deduplicated, subtask types marked."""
        from jira_cli.mcp import build_instructions

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.load_writing_guidance", return_value=None):
                with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                    mock_client_class.return_value = (
                        self._client_with_instance_metadata()
                    )

                    instructions = build_instructions()

        assert "create_issue" in instructions
        assert "Task, Story" in instructions
        assert "Story, Story" not in instructions
        assert "Subtask types: Sub-task" in instructions

    def test_instructions_report_unfetched_instance_metadata(self) -> None:
        """A fetch failure is reported as not checked, not as an error."""
        import httpx

        from jira_cli.mcp import DEFAULT_WRITING_GUIDANCE, build_instructions

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch("jira_cli.mcp.load_writing_guidance", return_value=None):
                with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                    client = create_mock_client()
                    client.get_statuses.side_effect = httpx.ConnectError("down")
                    mock_client_class.return_value = client

                    instructions = build_instructions()

        assert DEFAULT_WRITING_GUIDANCE in instructions
        assert "statuses and issue types could not be fetched" in instructions
        assert "get_transitions" in instructions

    def test_configured_guidance_replaces_default(self) -> None:
        """A guidance file overrides the default writing guidance."""
        from jira_cli.mcp import DEFAULT_WRITING_GUIDANCE, build_instructions

        with patch("jira_cli.mcp.load_config", return_value=mock_config()):
            with patch(
                "jira_cli.mcp.load_writing_guidance",
                return_value="Custom team convention.",
            ):
                with patch("jira_cli.mcp.JiraClient") as mock_client_class:
                    mock_client_class.return_value = (
                        self._client_with_instance_metadata()
                    )

                    instructions = build_instructions()

        assert instructions.startswith("Custom team convention.")
        assert DEFAULT_WRITING_GUIDANCE not in instructions
        assert "transition_issue" in instructions

    def test_main_applies_built_instructions(self) -> None:
        """Startup sets the built instructions on the server before running."""
        from jira_cli import mcp as mcp_module

        original = mcp_module.mcp.instructions
        try:
            with patch.object(
                mcp_module, "build_instructions", return_value="built text"
            ):
                with patch.object(mcp_module.mcp, "run") as mock_run:
                    mcp_module.main()

            assert mcp_module.mcp.instructions == "built text"
            mock_run.assert_called_once()
        finally:
            mcp_module.mcp.instructions = original


class TestIssueWritingGuidance:
    """The server tells LLM clients how Jira and Confluence text must be written."""

    REQUIRED_PHRASES = (
        "plain English",
        "markdown tables",
        "Context",
        "Goal",
        "Scope",
        "Acceptance criteria",
    )

    def test_server_instructions_state_writing_convention(self) -> None:
        """Server-level instructions describe the writing convention."""
        from jira_cli.mcp import mcp

        assert mcp.instructions is not None
        for phrase in self.REQUIRED_PHRASES:
            assert phrase in mcp.instructions
        assert "Confluence pages" in mcp.instructions

    def test_page_tool_descriptions_state_writing_convention(self) -> None:
        """create_page and update_page tool descriptions carry the convention."""
        from jira_cli.confluence_mcp import create_page, update_page

        for tool in (create_page, update_page):
            doc = tool.__doc__ or ""
            assert "plain English" in doc
            assert "markdown tables" in doc

    def test_issue_tool_descriptions_refer_to_server_instructions(self) -> None:
        """The issue tools defer to the (possibly configured) server instructions."""
        from jira_cli.mcp import create_issue, update_issue

        for tool in (create_issue, update_issue):
            doc = tool.__doc__ or ""
            assert "writing conventions" in doc
            assert "server instructions" in doc
            assert "markdown tables" in doc
