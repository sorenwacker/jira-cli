"""CLI commands for managing Confluence Cloud pages."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jira_cli.config import load_confluence_config
from jira_cli.confluence_client import (
    ConfluenceClient,
    PageCreateParams,
    PageUpdateParams,
)
from jira_cli.confluence_models import Page, Space
from jira_cli.confluence_storage import storage_to_text

__all__ = ["app"]

app = typer.Typer(
    name="confluence",
    help="CLI tool for managing Confluence Cloud pages.",
    no_args_is_help=True,
)

space_app = typer.Typer(
    name="space",
    help="Space commands.",
    no_args_is_help=True,
)
app.add_typer(space_app, name="space")

console = Console()


def get_client() -> ConfluenceClient:
    """Get a configured Confluence client."""
    return ConfluenceClient(load_confluence_config())


def _resolve_body(body: str | None, file: str | None) -> str:
    """Resolve page body from an inline string or a file path."""
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    return body or ""


def _page_table(pages: list[Page], title: str) -> Table:
    """Build a table of pages."""
    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title")
    for page in pages:
        table.add_row(page.id, page.title)
    return table


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show resolved configuration"),
) -> None:
    """Show the resolved Confluence configuration."""
    if not show:
        console.print(
            "Confluence reuses the Jira configuration. "
            "Run 'jira config' to set credentials, or use --show to view them."
        )
        return
    try:
        cfg = load_confluence_config()
        console.print(f"[bold]URL:[/bold] {cfg.url}")
        console.print(f"[bold]Email:[/bold] {cfg.email}")
        console.print(f"[bold]API Token:[/bold] {'*' * 20}")
    except ValueError as e:
        console.print(f"[red]Not configured: {e}[/red]")


@app.command()
def search(
    cql: str = typer.Argument(..., help="CQL query string"),
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum results"),
) -> None:
    """Search content using CQL."""
    with get_client() as client:
        pages = client.search(cql, limit=limit)

    if not pages:
        console.print("[yellow]No results found[/yellow]")
        return

    console.print(_page_table(pages, "Search Results"))


@space_app.command("list")
def space_list(
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum results"),
) -> None:
    """List Confluence spaces."""
    with get_client() as client:
        spaces: list[Space] = client.list_spaces(limit=limit)

    if not spaces:
        console.print("[yellow]No spaces found[/yellow]")
        return

    table = Table(title="Spaces")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="dim")
    for space in spaces:
        table.add_row(space.key, space.name, space.type)

    console.print(table)


@app.command()
def page(
    page_id: str = typer.Argument(..., help="Numeric page ID"),
    raw: bool = typer.Option(False, "--raw", help="Show raw storage-format body"),
) -> None:
    """Read a page by ID."""
    with get_client() as client:
        result = client.get_page(page_id)

    if raw:
        console.print(result.body or "")
        return

    console.print(
        Panel(storage_to_text(result.body), title=f"[cyan]{result.title}[/cyan]")
    )


@app.command()
def create(
    space: str = typer.Option(..., "--space", "-s", help="Space key"),
    title: str = typer.Option(..., "--title", "-t", help="Page title"),
    body: str | None = typer.Option(None, "--body", "-b", help="Markdown body"),
    file: str | None = typer.Option(None, "--file", "-f", help="Markdown file path"),
    parent: str | None = typer.Option(None, "--parent", help="Parent page ID"),
) -> None:
    """Create a page from markdown."""
    params = PageCreateParams(
        space_key=space,
        title=title,
        body=_resolve_body(body, file),
        parent_id=parent,
    )
    with get_client() as client:
        created = client.create_page(params)

    console.print(f"[green]Created page {created.id}: {created.title}[/green]")


@app.command()
def update(
    page_id: str = typer.Argument(..., help="Numeric page ID"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    body: str | None = typer.Option(None, "--body", "-b", help="New markdown body"),
    file: str | None = typer.Option(None, "--file", "-f", help="Markdown file path"),
) -> None:
    """Update a page's title and/or body."""
    new_body = _resolve_body(body, file) if (body or file) else None
    params = PageUpdateParams(title=title, body=new_body)
    with get_client() as client:
        updated = client.update_page(page_id, params)

    console.print(f"[green]Updated page {updated.id}: {updated.title}[/green]")


if __name__ == "__main__":
    app()
