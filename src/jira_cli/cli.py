"""CLI commands for Jira CLI."""

from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jira_cli.client import (
    IssueCreateParams,
    IssueUpdateParams,
    JiraClient,
    UserSearchParams,
)
from jira_cli.config import JiraConfig, load_config, save_config
from jira_cli.display import build_comment_panel, build_issue_content, truncate
from jira_cli.quality import build_quality_jql, generate_quality_report
from jira_cli.shell import JiraShell

__all__ = ["app"]

if TYPE_CHECKING:
    from jira_cli.models import Comment, Issue

app = typer.Typer(
    name="jira",
    help="CLI tool for managing Jira Cloud issues.",
    no_args_is_help=True,
)

issue_app = typer.Typer(
    name="issue",
    help="Issue management commands.",
    no_args_is_help=True,
)

comment_app = typer.Typer(
    name="comment",
    help="Comment management commands.",
    no_args_is_help=True,
)

user_app = typer.Typer(
    name="user",
    help="User management commands.",
    no_args_is_help=True,
)

project_app = typer.Typer(
    name="project",
    help="Project management commands.",
    no_args_is_help=True,
)

app.add_typer(issue_app, name="issue")
app.add_typer(user_app, name="user")
app.add_typer(project_app, name="project")
issue_app.add_typer(comment_app, name="comment")

console = Console()


def _parse_csv_list(value: str | None) -> list[str] | None:
    """Parse a comma-separated string into a list of stripped items."""
    if not value:
        return None
    return [item.strip() for item in value.split(",")]


def _create_issue_table(issues: list["Issue"], title: str) -> Table:
    """Create a Rich table for displaying issues."""
    table = Table(title=title)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Priority")
    table.add_column("Summary")

    for issue in issues:
        summary = truncate(issue.summary, max_len=60)
        table.add_row(issue.key, issue.status, issue.priority or "-", summary)

    return table


def get_client() -> JiraClient:
    """Get a configured Jira client."""
    return JiraClient(load_config())


@issue_app.command("list")
def issue_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project key"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
) -> None:
    """List issues assigned to you."""
    with get_client() as client:
        issues = client.get_my_issues(status=status, project=project, limit=limit)

    if not issues:
        console.print("[yellow]No issues found[/yellow]")
        return

    console.print(_create_issue_table(issues, "My Issues"))


@issue_app.command("view")
def issue_view(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comments: bool = typer.Option(False, "--comments", "-c", help="Include comments"),
) -> None:
    """View issue details."""
    with get_client() as client:
        issue = client.get_issue(issue_key)
        issue_comments = client.get_comments(issue_key) if comments else []

    content = build_issue_content(issue)
    console.print(Panel(content, title=f"[cyan]{issue.key}[/cyan]"))
    _print_comments(issue_comments, comments)


def _print_comments(comments: list["Comment"], show: bool) -> None:
    """Print comments if requested."""
    if not show:
        return
    if comments:
        console.print("\n[bold]Comments:[/bold]")
        for c in comments:
            console.print(build_comment_panel(c))
    else:
        console.print("\n[dim]No comments[/dim]")


@comment_app.command("add")
def comment_add(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    body: str = typer.Argument(..., help="Comment text"),
) -> None:
    """Add a comment to an issue."""
    with get_client() as client:
        client.add_comment(issue_key, body)

    console.print(f"[green]Comment added to {issue_key}[/green]")


@comment_app.command("edit")
def comment_edit(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comment_id: str = typer.Argument(..., help="Comment ID"),
    body: str = typer.Argument(..., help="New comment text"),
) -> None:
    """Edit an existing comment."""
    with get_client() as client:
        client.update_comment(issue_key, comment_id, body)

    console.print(f"[green]Comment updated on {issue_key}[/green]")


@comment_app.command("delete")
def comment_delete(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comment_id: str = typer.Argument(..., help="Comment ID"),
) -> None:
    """Delete a comment."""
    with get_client() as client:
        client.delete_comment(issue_key, comment_id)

    console.print(f"[green]Comment deleted from {issue_key}[/green]")


@issue_app.command("move")
def issue_move(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    target: str | None = typer.Argument(None, help="Target status to transition to"),
) -> None:
    """View available transitions or change issue status."""
    with get_client() as client:
        if target is None:
            transitions = client.get_transitions(issue_key)
            console.print(f"[bold]Available transitions for {issue_key}:[/bold]")
            for t in transitions:
                console.print(f"  - {t.name}")
        else:
            client.transition_issue(issue_key, target)
            console.print(f"[green]{issue_key} transitioned to '{target}'[/green]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
) -> None:
    """Configure Jira credentials."""
    if show:
        _show_config()
        return
    _prompt_and_save_config()


def _show_config() -> None:
    """Show current configuration."""
    try:
        cfg = load_config()
        console.print(f"[bold]URL:[/bold] {cfg.url}")
        console.print(f"[bold]Email:[/bold] {cfg.email}")
        console.print(f"[bold]API Token:[/bold] {'*' * 20}")
    except ValueError as e:
        console.print(f"[red]Not configured: {e}[/red]")


def _prompt_and_save_config() -> None:
    """Prompt for and save configuration."""
    url = typer.prompt("Jira URL (e.g., https://yourcompany.atlassian.net)")
    email = typer.prompt("Email")
    api_token = typer.prompt("API Token", hide_input=True)

    cfg = JiraConfig(url=url, email=email, api_token=api_token)
    save_config(cfg)
    console.print("[green]Configuration saved[/green]")


@issue_app.command("create")
def issue_create(
    project: str = typer.Argument(..., help="Project key (e.g., PROJ)"),
    summary: str = typer.Argument(..., help="Issue summary/title"),
    issue_type: str = typer.Option("Task", "--type", "-t", help="Issue type"),
    description: str | None = typer.Option(None, "--description", "-d"),
    priority: str | None = typer.Option(None, "--priority", "-p"),
    labels: str | None = typer.Option(None, "--labels", "-l", help="CSV labels"),
    reporter: str | None = typer.Option(None, "--reporter", help="Account ID"),
    components: str | None = typer.Option(None, "--components", help="CSV names"),
    fix_versions: str | None = typer.Option(None, "--fix-versions", help="CSV names"),
    due_date: str | None = typer.Option(None, "--due-date", help="YYYY-MM-DD"),
) -> None:
    """Create a new issue."""
    params = IssueCreateParams(
        project=project,
        summary=summary,
        issue_type=issue_type,
        description=description,
        priority=priority,
        labels=_parse_csv_list(labels),
        reporter=reporter,
        components=_parse_csv_list(components),
        fix_versions=_parse_csv_list(fix_versions),
        due_date=due_date,
    )
    with get_client() as client:
        issue_key = client.create_issue(params)

    console.print(f"[green]Created {issue_key}[/green]")


@issue_app.command("create-subtask")
def issue_create_subtask(
    parent_key: str = typer.Argument(..., help="Parent issue key (e.g., PROJ-123)"),
    summary: str = typer.Argument(..., help="Subtask summary"),
    issue_type: str = typer.Option("Sub-task", "--type", "-t", help="Issue type"),
    description: str | None = typer.Option(None, "--description", "-d"),
    priority: str | None = typer.Option(None, "--priority", "-p"),
) -> None:
    """Create a subtask under a parent issue."""
    project = parent_key.split("-", maxsplit=1)[0]
    params = IssueCreateParams(
        project=project,
        summary=summary,
        issue_type=issue_type,
        description=description,
        priority=priority,
        parent=parent_key,
    )
    with get_client() as client:
        issue_key = client.create_issue(params)

    console.print(f"[green]Created subtask {issue_key} under {parent_key}[/green]")


@issue_app.command("edit")
def issue_edit(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    summary: str | None = typer.Option(None, "--summary", "-s"),
    description: str | None = typer.Option(None, "--description", "-d"),
    priority: str | None = typer.Option(None, "--priority", "-p"),
    labels: str | None = typer.Option(None, "--labels", "-l"),
    assignee: str | None = typer.Option(None, "--assignee", "-a"),
    reporter: str | None = typer.Option(None, "--reporter", help="Account ID"),
    components: str | None = typer.Option(None, "--components", help="CSV names"),
    fix_versions: str | None = typer.Option(None, "--fix-versions", help="CSV names"),
    due_date: str | None = typer.Option(None, "--due-date", help="YYYY-MM-DD"),
) -> None:
    """Edit issue fields."""
    params = IssueUpdateParams(
        summary=summary,
        description=description,
        priority=priority,
        labels=_parse_csv_list(labels),
        assignee=assignee,
        reporter=reporter,
        components=_parse_csv_list(components),
        fix_versions=_parse_csv_list(fix_versions),
        due_date=due_date,
    )
    with get_client() as client:
        changed = client.update_issue(issue_key, params)

    if changed:
        console.print(f"[green]Updated {issue_key}[/green]")
    else:
        console.print(f"[yellow]No fields to update for {issue_key}[/yellow]")


@issue_app.command("search")
def issue_search(
    jql: str = typer.Argument(..., help="JQL query string"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum results"),
) -> None:
    """Search issues with JQL."""
    with get_client() as client:
        issues = client.search(jql, limit=limit)

    if not issues:
        console.print("[yellow]No issues found[/yellow]")
        return

    console.print(_create_issue_table(issues, "Search Results"))


@issue_app.command("watch")
def issue_watch(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
) -> None:
    """Watch an issue."""
    with get_client() as client:
        client.watch_issue(issue_key)

    console.print(f"[green]Now watching {issue_key}[/green]")


@issue_app.command("unwatch")
def issue_unwatch(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
) -> None:
    """Stop watching an issue."""
    with get_client() as client:
        client.unwatch_issue(issue_key)

    console.print(f"[green]Stopped watching {issue_key}[/green]")


@issue_app.command("delete")
def issue_delete(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an issue permanently."""
    if not force:
        confirm = typer.confirm(f"Delete {issue_key}? This cannot be undone")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit()  # noqa: RSE102 - typer.Exit requires instantiation

    with get_client() as client:
        client.delete_issue(issue_key)

    console.print(f"[green]Deleted {issue_key}[/green]")


@issue_app.command("quality")
def issue_quality(
    project: str | None = typer.Option(None, "--project", "-p", help="Project key"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    jql: str | None = typer.Option(
        None, "--jql", help="Custom JQL (overrides filters)"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Max issues to analyze"),
) -> None:
    """Score issues on completeness (1-10)."""
    with get_client() as client:
        issues = client.search(build_quality_jql(project, status, jql), limit=limit)

    if not issues:
        console.print("[yellow]No issues found[/yellow]")
        return

    table = Table(title="Issue Quality")
    for column in ("Key", "Summary", "Creator", "Age", "Status", "Rating"):
        table.add_column(column)
    for row in generate_quality_report(issues):
        table.add_row(
            str(row["key"]),
            truncate(str(row["summary"]), 50),
            str(row["creator"] or ""),
            str(row["age"]),
            str(row["status"]),
            f"{row['rating']}/10",
        )
    console.print(table)


@app.command()
def shell() -> None:
    """Start interactive shell mode."""
    with get_client() as client:
        jira_shell = JiraShell(client)
        jira_shell.cmdloop()


@user_app.command("list")
def user_list(
    project: str = typer.Option(..., "--project", "-p", help="Project key"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search by name"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Maximum results"),
) -> None:
    """List users assignable to a project."""
    params = UserSearchParams(query=query, project=project, limit=limit)
    with get_client() as client:
        users = client.get_users(params)

    if not users:
        console.print("[yellow]No users found[/yellow]")
        return

    table = Table(title=f"Users assignable to {project}")
    table.add_column("Display Name", style="cyan")
    table.add_column("Email")
    table.add_column("Account ID", style="dim")

    for user in users:
        table.add_row(user.display_name, user.email or "-", user.account_id)

    console.print(table)


@project_app.command("list")
def project_list() -> None:
    """List all projects."""
    with get_client() as client:
        projects = client.get_projects()

    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return

    table = Table(title="Projects")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="dim")

    for project in projects:
        table.add_row(project.key, project.name, project.project_type)

    console.print(table)


if __name__ == "__main__":
    app()
