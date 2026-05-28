"""CLI commands for Jira CLI."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jira_cli.client import JiraClient
from jira_cli.config import JiraConfig, load_config, save_config
from jira_cli.shell import JiraShell

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


def get_client() -> JiraClient:
    """Get a configured Jira client."""
    return JiraClient(load_config())


@issue_app.command("list")
def issue_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project key"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of results"),
) -> None:
    """List issues assigned to you."""
    with get_client() as client:
        issues = client.get_my_issues(status=status, project=project, limit=limit)

    if not issues:
        console.print("[yellow]No issues found[/yellow]")
        return

    table = Table(title="My Issues")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Priority")
    table.add_column("Summary")

    for issue in issues:
        table.add_row(
            issue.key,
            issue.status,
            issue.priority or "-",
            issue.summary[:60] + "..." if len(issue.summary) > 60 else issue.summary,
        )

    console.print(table)


@issue_app.command("view")
def issue_view(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comments: bool = typer.Option(False, "--comments", "-c", help="Include comments"),
) -> None:
    """View issue details."""
    with get_client() as client:
        issue = client.get_issue(issue_key)
        issue_comments = client.get_comments(issue_key) if comments else []

    content = Text()
    content.append("Summary: ", style="bold")
    content.append(f"{issue.summary}\n")
    content.append("Status: ", style="bold")
    content.append(f"{issue.status}\n")
    content.append("Priority: ", style="bold")
    content.append(f"{issue.priority or '-'}\n")
    content.append("Assignee: ", style="bold")
    content.append(f"{issue.assignee or 'Unassigned'}\n")
    content.append("Reporter: ", style="bold")
    content.append(f"{issue.reporter or 'Unknown'}\n")
    content.append("Project: ", style="bold")
    content.append(f"{issue.project}\n")
    content.append("Created: ", style="bold")
    content.append(f"{issue.created.strftime('%Y-%m-%d %H:%M')}\n")
    content.append("Updated: ", style="bold")
    content.append(f"{issue.updated.strftime('%Y-%m-%d %H:%M')}\n")

    if issue.description:
        content.append("\nDescription:\n", style="bold")
        content.append(issue.description)

    console.print(Panel(content, title=f"[cyan]{issue.key}[/cyan]"))

    if comments and issue_comments:
        console.print("\n[bold]Comments:[/bold]")
        for c in issue_comments:
            comment_text = Text()
            comment_text.append(f"{c.author}", style="cyan")
            comment_text.append(f" - {c.created.strftime('%Y-%m-%d %H:%M')}", style="dim")
            comment_text.append(f" [id: {c.id}]\n", style="dim")
            comment_text.append(c.body)
            console.print(Panel(comment_text))
    elif comments:
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
        try:
            cfg = load_config()
            console.print(f"[bold]URL:[/bold] {cfg.url}")
            console.print(f"[bold]Email:[/bold] {cfg.email}")
            console.print(f"[bold]API Token:[/bold] {'*' * 20}")
        except ValueError as e:
            console.print(f"[red]Not configured: {e}[/red]")
        return

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
    issue_type: str = typer.Option(
        "Task", "--type", "-t", help="Issue type (Task, Bug, Story, etc.)"
    ),
    description: str | None = typer.Option(None, "--description", "-d", help="Issue description"),
    priority: str | None = typer.Option(
        None, "--priority", "-p", help="Priority (e.g., High, Medium, Low)"
    ),
    labels: str | None = typer.Option(None, "--labels", "-l", help="Comma-separated labels"),
) -> None:
    """Create a new issue."""
    label_list = [label.strip() for label in labels.split(",")] if labels else None

    with get_client() as client:
        issue_key = client.create_issue(
            project=project,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            labels=label_list,
        )

    console.print(f"[green]Created {issue_key}[/green]")


@issue_app.command("create-subtask")
def issue_create_subtask(
    parent_key: str = typer.Argument(..., help="Parent issue key (e.g., PROJ-123)"),
    summary: str = typer.Argument(..., help="Subtask summary"),
    issue_type: str = typer.Option(
        "Sub-task", "--type", "-t", help="Issue type (defaults to Sub-task)"
    ),
    description: str | None = typer.Option(None, "--description", "-d", help="Subtask description"),
    priority: str | None = typer.Option(
        None, "--priority", "-p", help="Priority (e.g., High, Medium, Low)"
    ),
) -> None:
    """Create a subtask under a parent issue."""
    # Extract project key from parent issue key
    project = parent_key.split("-")[0]

    with get_client() as client:
        issue_key = client.create_issue(
            project=project,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            parent=parent_key,
        )

    console.print(f"[green]Created subtask {issue_key} under {parent_key}[/green]")


@issue_app.command("edit")
def issue_edit(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    summary: str | None = typer.Option(None, "--summary", "-s", help="New summary"),
    description: str | None = typer.Option(None, "--description", "-d", help="New description"),
    priority: str | None = typer.Option(None, "--priority", "-p", help="New priority"),
    labels: str | None = typer.Option(None, "--labels", "-l", help="New labels (comma-separated)"),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="New assignee (account ID)"),
) -> None:
    """Edit issue fields."""
    label_list = [label.strip() for label in labels.split(",")] if labels else None

    with get_client() as client:
        client.update_issue(
            issue_key,
            summary=summary,
            description=description,
            priority=priority,
            labels=label_list,
            assignee=assignee,
        )

    console.print(f"[green]Updated {issue_key}[/green]")


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

    table = Table(title="Search Results")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Priority")
    table.add_column("Summary")

    for issue in issues:
        table.add_row(
            issue.key,
            issue.status,
            issue.priority or "-",
            issue.summary[:60] + "..." if len(issue.summary) > 60 else issue.summary,
        )

    console.print(table)


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
            raise typer.Exit()

    with get_client() as client:
        client.delete_issue(issue_key)

    console.print(f"[green]Deleted {issue_key}[/green]")


@app.command()
def shell() -> None:
    """Start interactive shell mode."""
    with get_client() as client:
        jira_shell = JiraShell(client)
        jira_shell.cmdloop()


@user_app.command("list")
def user_list(
    project: str = typer.Option(
        ..., "--project", "-p", help="Project key to list assignable users"
    ),
    query: str | None = typer.Option(None, "--query", "-q", help="Search by name or email"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Maximum number of results"),
) -> None:
    """List users assignable to a project."""
    with get_client() as client:
        users = client.get_users(query=query, project=project, limit=limit)

    if not users:
        console.print("[yellow]No users found[/yellow]")
        return

    table = Table(title=f"Users assignable to {project}")
    table.add_column("Display Name", style="cyan")
    table.add_column("Email")
    table.add_column("Account ID", style="dim")

    for user in users:
        table.add_row(
            user.display_name,
            user.email or "-",
            user.account_id,
        )

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
        table.add_row(
            project.key,
            project.name,
            project.project_type,
        )

    console.print(table)


if __name__ == "__main__":
    app()
