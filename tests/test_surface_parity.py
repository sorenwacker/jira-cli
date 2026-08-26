"""Gate: every capability is exposed on both the CLI and the MCP server."""

import asyncio

import typer

from jira_cli import cli, confluence_cli, mcp

# MCP tool name -> CLI command path. `config` and `shell` are CLI-only by design.
PARITY: dict[str, tuple[str, ...]] = {
    "get_issue": ("jira", "issue", "view"),
    "search_issues": ("jira", "issue", "search"),
    "get_my_issues": ("jira", "issue", "list"),
    "create_issue": ("jira", "issue", "create"),
    "update_issue": ("jira", "issue", "edit"),
    "get_transitions": ("jira", "issue", "move"),
    "transition_issue": ("jira", "issue", "move"),
    "get_comments": ("jira", "issue", "view"),
    "add_comment": ("jira", "issue", "comment", "add"),
    "update_comment": ("jira", "issue", "comment", "edit"),
    "delete_comment": ("jira", "issue", "comment", "delete"),
    "get_projects": ("jira", "project", "list"),
    "get_users": ("jira", "user", "list"),
    "watch_issue": ("jira", "issue", "watch"),
    "unwatch_issue": ("jira", "issue", "unwatch"),
    "delete_issue": ("jira", "issue", "delete"),
    "get_issue_quality_report": ("jira", "issue", "quality"),
    "confluence_search": ("confluence", "search"),
    "get_page": ("confluence", "page"),
    "list_spaces": ("confluence", "space", "list"),
    "create_page": ("confluence", "create"),
    "update_page": ("confluence", "update"),
}
CLI_ONLY = {("jira", "config"), ("jira", "shell"), ("confluence", "config")}
# create_issue covers subtasks too; the CLI splits them into a separate command.
CLI_ALIASES = {("jira", "issue", "create-subtask"): "create_issue"}


def _leaf_commands(name: str, app: typer.Typer) -> set[tuple[str, ...]]:
    """Return every runnable command path of a Typer app.

    Groups are detected by their `commands` mapping rather than by an
    isinstance check: Typer vendors its own copy of click, so its groups are
    not instances of the installed `click.Group`.
    """
    paths: set[tuple[str, ...]] = set()

    def walk(cmd: object, prefix: tuple[str, ...]) -> None:
        subcommands = getattr(cmd, "commands", None)
        if subcommands:
            for sub_name, sub in subcommands.items():
                walk(sub, (*prefix, sub_name))
        else:
            paths.add(prefix)

    walk(typer.main.get_command(app), (name,))
    return paths


def _mcp_tool_names() -> set[str]:
    return {t.name for t in asyncio.run(mcp.mcp.list_tools())}


def test_every_mcp_tool_has_a_cli_command() -> None:
    assert _mcp_tool_names() == set(PARITY)


def test_every_cli_command_has_an_mcp_tool() -> None:
    commands = _leaf_commands("jira", cli.app) | _leaf_commands(
        "confluence", confluence_cli.app
    )
    expected = set(PARITY.values()) | CLI_ONLY | set(CLI_ALIASES)
    assert commands == expected


def test_parity_targets_exist_in_cli() -> None:
    commands = _leaf_commands("jira", cli.app) | _leaf_commands(
        "confluence", confluence_cli.app
    )
    missing = {tool: path for tool, path in PARITY.items() if path not in commands}
    assert not missing


def test_aliases_point_at_registered_tools() -> None:
    assert set(CLI_ALIASES.values()) <= set(PARITY)
