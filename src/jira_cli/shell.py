"""Interactive shell for Jira CLI."""

from __future__ import annotations

import cmd
import shlex
import sys
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jira_cli.display import build_comment_panel, build_issue_content, truncate

__all__ = ["JiraShell"]

if TYPE_CHECKING:
    from jira_cli.client import JiraClient
    from jira_cli.models import Issue

# Check if readline is available (not on Windows by default)
HAS_READLINE = "readline" in sys.modules or sys.platform != "win32"
if HAS_READLINE:
    try:
        import readline
    except ImportError:
        HAS_READLINE = False
        readline = None  # type: ignore[assignment]

console = Console()


def _create_issues_table(issues: list[Issue], title: str) -> Table:
    """Create a Rich table for displaying issues."""
    table = Table(title=title)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Priority")
    table.add_column("Summary")
    for issue in issues:
        summary = truncate(issue.summary, max_len=50)
        table.add_row(issue.key, issue.status, issue.priority or "-", summary)
    return table


# Argument mappings: (flags, key, is_int)
_ARG_MAPPINGS: list[tuple[tuple[str, ...], str, bool]] = [
    (("--status", "-s"), "status", False),
    (("--project", "-p"), "project", False),
    (("--limit", "-l"), "limit", True),
    (("--type", "-t"), "type", False),
    (("--description", "-d"), "description", False),
    (("--summary",), "summary", False),
    (("--priority",), "priority", False),
    (("--labels",), "labels", False),
]


def _parse_shell_args(arg: str) -> dict[str, str | int | None]:
    """Parse shell command arguments."""
    result: dict[str, str | int | None] = {}
    try:
        args = shlex.split(arg)
    except ValueError:
        return result

    i = 0
    while i < len(args):
        matched = False
        for flags, key, is_int in _ARG_MAPPINGS:
            if args[i] in flags and i + 1 < len(args):
                result[key] = int(args[i + 1]) if is_int else args[i + 1]
                i += 2
                matched = True
                break
        if not matched:
            i += 1
    return result


def _strip_quotes(text: str) -> str:
    """Remove surrounding quotes from text."""
    if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
        return text[1:-1]
    return text


class JiraShell(cmd.Cmd):  # pylint: disable=too-many-public-methods
    """Interactive shell for managing Jira issues."""

    intro = "Jira interactive shell. Type 'help' for commands, 'quit' to exit."

    def __init__(self, client: JiraClient) -> None:
        """Initialize the shell.

        Args:
            client: Jira API client.
        """
        super().__init__()
        self.client = client
        self.current_issue: str | None = None
        self._issue_cache: list[str] = []
        self._update_prompt()

    def preloop(self) -> None:
        """Set up readline completion."""
        if readline:
            readline.set_completer_delims(" \t\n")

    def _refresh_issue_cache(self) -> None:
        """Refresh the cached list of issue keys."""
        try:
            issues = self.client.get_my_issues(limit=100)
            done = {"done", "closed", "resolved", "cancelled"}
            self._issue_cache = [i.key for i in issues if i.status.lower() not in done]
        except Exception:  # noqa: BLE001 - shell should not crash
            pass

    def complete_cd(
        self,
        text: str,
        line: str,  # noqa: ARG002
        begidx: int,  # noqa: ARG002
        endidx: int,  # noqa: ARG002
    ) -> list[str]:
        """Complete issue keys for cd command."""
        if not self._issue_cache:
            self._refresh_issue_cache()
        return [k for k in self._issue_cache if k.startswith(text.upper())]

    def complete_cat(
        self,
        text: str,
        line: str,
        begidx: int,
        endidx: int,
    ) -> list[str]:
        """Complete issue keys for cat command."""
        return self.complete_cd(text, line, begidx, endidx)

    def complete_show(
        self,
        text: str,
        line: str,
        begidx: int,
        endidx: int,
    ) -> list[str]:
        """Complete issue keys for show command."""
        return self.complete_cd(text, line, begidx, endidx)

    def complete_status(
        self,
        text: str,
        line: str,  # noqa: ARG002
        begidx: int,  # noqa: ARG002
        endidx: int,  # noqa: ARG002
    ) -> list[str]:
        """Complete status transitions."""
        if not self.current_issue:
            return []
        try:
            transitions = self.client.get_transitions(self.current_issue)
        except Exception:  # noqa: BLE001 - completion should not crash
            return []
        lower_text = text.lower()
        return [t.name for t in transitions if t.name.lower().startswith(lower_text)]

    def complete_edit(
        self,
        text: str,
        line: str,  # noqa: ARG002
        begidx: int,  # noqa: ARG002
        endidx: int,  # noqa: ARG002
    ) -> list[str]:
        """Complete edit options."""
        options = ["--summary", "--priority", "--labels", "--description"]
        return [o for o in options if o.startswith(text)]

    def complete_new(
        self,
        text: str,
        line: str,  # noqa: ARG002
        begidx: int,  # noqa: ARG002
        endidx: int,  # noqa: ARG002
    ) -> list[str]:
        """Complete new issue options."""
        options = ["--type", "--description"]
        return [o for o in options if o.startswith(text)]

    def complete_delcomment(
        self,
        text: str,
        line: str,  # noqa: ARG002
        begidx: int,  # noqa: ARG002
        endidx: int,  # noqa: ARG002
    ) -> list[str]:
        """Complete comment IDs for delcomment command."""
        if not self.current_issue:
            return []
        try:
            comments = self.client.get_comments(self.current_issue)
            return [c.id for c in comments if c.id.startswith(text)]
        except Exception:  # noqa: BLE001 - completion should not crash
            return []

    def _update_prompt(self) -> None:
        """Update the prompt based on current state."""
        cyan, green, reset = "\033[36m", "\033[32m", "\033[0m"
        if self.current_issue:
            self.prompt = f"{green}jira{reset}/{cyan}{self.current_issue}{reset}> "
        else:
            self.prompt = f"{green}jira{reset}> "

    def do_list(self, arg: str) -> None:
        """List issues assigned to you."""
        parsed = _parse_shell_args(arg)
        try:
            issues = self.client.get_my_issues(
                status=parsed.get("status"),  # type: ignore[arg-type]
                project=parsed.get("project"),  # type: ignore[arg-type]
                limit=parsed.get("limit", 50),  # type: ignore[arg-type]
            )
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        if not issues:
            console.print("[yellow]No issues found[/yellow]")
            return
        console.print(_create_issues_table(issues, "My Issues"))

    def do_ls(self, arg: str) -> None:
        """List issues or show current issue details."""
        if self.current_issue:
            self._show_issue(self.current_issue)
            if "-a" in arg or "--all" in arg:
                self.do_comments("")
        else:
            self._list_issues(show_all="-a" in arg or "--all" in arg)

    def _list_issues(self, *, show_all: bool) -> None:
        """List issues at root level."""
        try:
            issues = self.client.get_my_issues(limit=50)
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        if not show_all:
            done = {"done", "closed", "resolved", "cancelled"}
            issues = [i for i in issues if i.status.lower() not in done]
        if not issues:
            console.print("[yellow]No issues found[/yellow]")
            return
        console.print(_create_issues_table(issues, "My Issues"))

    def do_l(self, arg: str) -> None:
        """Alias for ls."""
        self.do_ls(arg)

    def do_cd(self, arg: str) -> None:
        """Change to an issue or back."""
        arg = arg.strip()
        if not arg:
            console.print("[yellow]Usage: cd ISSUE-KEY or cd ..[/yellow]")
            return
        if arg == "..":
            self.current_issue = None
            self._update_prompt()
            return
        try:
            self.client.get_issue(arg.upper())
            self.current_issue = arg.upper()
            self._update_prompt()
        except Exception:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Issue not found: {arg}[/red]")

    def do_pwd(self, arg: str) -> None:  # noqa: ARG002
        """Show current issue."""
        if self.current_issue:
            console.print(f"[cyan]{self.current_issue}[/cyan]")
        else:
            console.print("[dim]No issue selected[/dim]")

    def _show_issue(self, issue_key: str) -> None:
        """Display issue details."""
        try:
            issue = self.client.get_issue(issue_key)
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        content = build_issue_content(issue, include_attachments=True)
        console.print(Panel(content, title=f"[cyan]{issue.key}[/cyan]"))

    def do_show(self, arg: str) -> None:
        """Show issue details."""
        issue_key = arg.strip().upper() if arg.strip() else self.current_issue
        if not issue_key:
            console.print("[yellow]Usage: show ISSUE-KEY[/yellow]")
            return
        self._show_issue(issue_key)

    def do_cat(self, arg: str) -> None:
        """Show issue details."""
        self.do_show(arg)

    def do_comments(self, arg: str) -> None:  # noqa: ARG002
        """Show comments for current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        try:
            comments = self.client.get_comments(self.current_issue)
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        if not comments:
            console.print("[dim]No comments[/dim]")
            return
        console.print(f"[bold]Comments for {self.current_issue}:[/bold]")
        for c in comments:
            console.print(build_comment_panel(c))

    def do_comment(self, arg: str) -> None:
        """Add a comment to current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        text = _strip_quotes(arg.strip())
        if not text:
            console.print('[yellow]Usage: comment "your text"[/yellow]')
            return
        try:
            self.client.add_comment(self.current_issue, text)
            console.print(f"[green]Comment added to {self.current_issue}[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_status(self, arg: str) -> None:
        """Show transitions or change status."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        target = _strip_quotes(arg.strip())
        if not target:
            self._show_transitions()
        else:
            self._execute_transition(target)

    def _show_transitions(self) -> None:
        """Show available transitions."""
        try:
            transitions = self.client.get_transitions(self.current_issue)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        console.print(f"[bold]Available transitions for {self.current_issue}:[/bold]")
        for t in transitions:
            console.print(f"  - {t.name}")

    def _execute_transition(self, target: str) -> None:
        """Execute a status transition."""
        try:
            self.client.transition_issue(self.current_issue, target)  # type: ignore[arg-type]
            msg = f"[green]{self.current_issue} transitioned to '{target}'[/green]"
            console.print(msg)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_new(self, arg: str) -> None:
        """Create a new issue."""
        try:
            args = shlex.split(arg)
        except ValueError:
            console.print('[yellow]Usage: new PROJECT "Summary"[/yellow]')
            return
        if len(args) < 2:
            console.print('[yellow]Usage: new PROJECT "Summary"[/yellow]')
            return
        project, summary = args[0], args[1]
        parsed = _parse_shell_args(" ".join(args[2:]))
        self._create_issue(project, summary, parsed)

    def _create_issue(
        self,
        project: str,
        summary: str,
        opts: dict[str, str | int | None],
    ) -> None:
        """Create an issue with given parameters."""
        from jira_cli.client import IssueCreateParams

        params = IssueCreateParams(
            project=project,
            summary=summary,
            issue_type=opts.get("type", "Task"),  # type: ignore[arg-type]
            description=opts.get("description"),  # type: ignore[arg-type]
        )
        try:
            issue_key = self.client.create_issue(params)
            console.print(f"[green]Created {issue_key}[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_edit(self, arg: str) -> None:
        """Edit current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        parsed = _parse_shell_args(arg)
        keys = ("summary", "priority", "labels", "description")
        if not any(parsed.get(k) for k in keys):
            console.print('[yellow]Usage: edit --summary "new"[/yellow]')
            return
        self._update_issue(parsed)

    def _update_issue(self, opts: dict[str, str | int | None]) -> None:
        """Update current issue with given options."""
        from jira_cli.client import IssueUpdateParams

        labels = None
        if opts.get("labels"):
            labels = [label.strip() for label in str(opts["labels"]).split(",")]
        params = IssueUpdateParams(
            summary=opts.get("summary"),  # type: ignore[arg-type]
            priority=opts.get("priority"),  # type: ignore[arg-type]
            labels=labels,
            description=opts.get("description"),  # type: ignore[arg-type]
        )
        try:
            self.client.update_issue(self.current_issue, params)  # type: ignore[arg-type]
            console.print(f"[green]Updated {self.current_issue}[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_search(self, arg: str) -> None:
        """Search with JQL."""
        jql = _strip_quotes(arg.strip())
        if not jql:
            console.print('[yellow]Usage: search "JQL query"[/yellow]')
            return
        try:
            issues = self.client.search(jql)
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")
            return
        if not issues:
            console.print("[yellow]No issues found[/yellow]")
            return
        console.print(_create_issues_table(issues, "Search Results"))

    def do_watch(self, arg: str) -> None:  # noqa: ARG002
        """Watch current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        try:
            self.client.watch_issue(self.current_issue)
            console.print(f"[green]Now watching {self.current_issue}[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_unwatch(self, arg: str) -> None:  # noqa: ARG002
        """Stop watching current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        try:
            self.client.unwatch_issue(self.current_issue)
            console.print(f"[green]Stopped watching {self.current_issue}[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_delcomment(self, arg: str) -> None:
        """Delete a comment."""
        if not self.current_issue:
            console.print("[yellow]No issue selected.[/yellow]")
            return
        comment_id = arg.strip()
        if not comment_id:
            console.print("[yellow]Usage: delcomment COMMENT_ID[/yellow]")
            return
        try:
            self.client.delete_comment(self.current_issue, comment_id)
            console.print(f"[green]Comment {comment_id} deleted[/green]")
        except Exception as e:  # noqa: BLE001 - user-facing error
            console.print(f"[red]Error: {e}[/red]")

    def do_help(self, arg: str) -> None:
        """Show help for commands."""
        if arg:
            super().do_help(arg)
            return
        console.print(_get_help_text())

    def do_h(self, arg: str) -> None:
        """Alias for help."""
        self.do_help(arg)

    def do_clear(self, arg: str) -> None:  # noqa: ARG002
        """Clear the screen."""
        console.clear()

    def do_quit(self, arg: str) -> bool:  # noqa: ARG002
        """Exit the shell."""
        console.print("[dim]Goodbye[/dim]")
        return True

    def do_q(self, arg: str) -> bool:
        """Exit the shell (shortcut)."""
        return self.do_quit(arg)

    def do_exit(self, arg: str) -> bool:
        """Exit the shell."""
        return self.do_quit(arg)

    def do_EOF(self, arg: str) -> bool:
        """Exit on Ctrl+D."""
        console.print()
        return self.do_quit(arg)

    def emptyline(self) -> bool:
        """Do nothing on empty line, return False to continue shell."""
        return False

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        if line.strip() == "..":
            self.do_cd("..")
            return
        console.print(f"[red]Unknown command: {line}[/red]")
        console.print("[dim]Type 'help' for available commands[/dim]")


def _get_help_text() -> str:
    """Get the help text for the shell."""
    return """
[bold]Navigation:[/bold]
  l / ls                  At root: list open issues (-a for all)
  list                    List your assigned issues
  cd ISSUE-KEY            Select an issue (e.g., cd DAT-123)
  cd .. / ..              Go back to root
  pwd                     Show current issue
  search "JQL"            Search with custom JQL

[bold]Issue commands:[/bold]
  new PROJECT "Summary"   Create new issue (--type TYPE)
  cat ISSUE-KEY           Show issue details
  edit --summary "new"    Edit fields (--priority, --labels)
  comments                Show comments
  comment "text"          Add a comment
  delcomment ID           Delete a comment
  status                  Show available transitions
  status "New Status"     Change status
  watch / unwatch         Watch/unwatch current issue

[bold]General:[/bold]
  clear                   Clear the screen
  h / help                Show this help
  exit / quit / q         Exit shell
"""
