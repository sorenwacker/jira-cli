"""Interactive shell for Jira CLI."""

import cmd
import shlex

try:
    import readline
except ImportError:
    readline = None  # type: ignore

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jira_cli.client import JiraClient

console = Console()


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class JiraShell(cmd.Cmd):
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
        self._issue_cache: list[str] = []  # Cache issue keys for completion
        self._update_prompt()

    def preloop(self) -> None:
        """Set up readline completion."""
        if readline:
            readline.set_completer_delims(" \t\n")

    def _refresh_issue_cache(self) -> None:
        """Refresh the cached list of issue keys (excluding done/closed)."""
        try:
            issues = self.client.get_my_issues(limit=100)
            done_statuses = {"done", "closed", "resolved", "cancelled"}
            self._issue_cache = [i.key for i in issues if i.status.lower() not in done_statuses]
        except Exception:
            pass

    def complete_cd(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete issue keys for cd command."""
        if not self._issue_cache:
            self._refresh_issue_cache()
        text_upper = text.upper()
        return [k for k in self._issue_cache if k.startswith(text_upper)]

    def complete_cat(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete issue keys for cat command."""
        return self.complete_cd(text, line, begidx, endidx)

    def complete_show(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete issue keys for show command."""
        return self.complete_cd(text, line, begidx, endidx)

    def complete_status(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete status transitions."""
        if not self.current_issue:
            return []
        try:
            transitions = self.client.get_transitions(self.current_issue)
            return [t.name for t in transitions if t.name.lower().startswith(text.lower())]
        except Exception:
            return []

    def complete_edit(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete edit options."""
        options = ["--summary", "--priority", "--labels", "--description"]
        return [o for o in options if o.startswith(text)]

    def complete_new(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete new issue options."""
        # Could add project completion here
        options = ["--type", "--description"]
        return [o for o in options if o.startswith(text)]

    def complete_delcomment(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """Complete comment IDs for delcomment command."""
        if not self.current_issue:
            return []
        try:
            comments = self.client.get_comments(self.current_issue)
            return [c.id for c in comments if c.id.startswith(text)]
        except Exception:
            return []

    def _update_prompt(self) -> None:
        """Update the prompt based on current state."""
        # ANSI color codes
        cyan = "\033[36m"
        green = "\033[32m"
        reset = "\033[0m"

        if self.current_issue:
            self.prompt = f"{green}jira{reset}/{cyan}{self.current_issue}{reset}> "
        else:
            self.prompt = f"{green}jira{reset}> "

    def do_list(self, arg: str) -> None:
        """List issues assigned to you. Usage: list [--status STATUS] [--project PROJECT]"""
        # Parse arguments
        status = None
        project = None
        limit = 50

        try:
            args = shlex.split(arg)
            i = 0
            while i < len(args):
                if args[i] in ("--status", "-s") and i + 1 < len(args):
                    status = args[i + 1]
                    i += 2
                elif args[i] in ("--project", "-p") and i + 1 < len(args):
                    project = args[i + 1]
                    i += 2
                elif args[i] in ("--limit", "-l") and i + 1 < len(args):
                    limit = int(args[i + 1])
                    i += 2
                else:
                    i += 1
        except (ValueError, IndexError):
            pass

        try:
            issues = self.client.get_my_issues(status=status, project=project, limit=limit)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

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
                issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary,
            )

        console.print(table)

    def do_ls(self, arg: str) -> None:
        """List issues or show current issue details. Use -a to show all/comments."""
        if self.current_issue:
            # Inside an issue - show its details
            self._show_issue(self.current_issue)
            # If -a, also show comments
            if "-a" in arg or "--all" in arg:
                self.do_comments("")
            return
        else:
            # At root - list issues
            show_all = "-a" in arg or "--all" in arg

            try:
                issues = self.client.get_my_issues(limit=50)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return

            # Filter out Done/closed unless -a
            if not show_all:
                done_statuses = {"done", "closed", "resolved", "cancelled"}
                issues = [i for i in issues if i.status.lower() not in done_statuses]

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
                    issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary,
                )

            console.print(table)

    def do_l(self, arg: str) -> None:
        """Alias for ls."""
        self.do_ls(arg)

    def do_cd(self, arg: str) -> None:
        """Change to an issue or back. Usage: cd ISSUE-KEY or cd .."""
        arg = arg.strip()

        if not arg:
            console.print("[yellow]Usage: cd ISSUE-KEY or cd ..[/yellow]")
            return

        if arg == "..":
            self.current_issue = None
            self._update_prompt()
            return

        # Validate issue exists
        try:
            self.client.get_issue(arg.upper())
            self.current_issue = arg.upper()
            self._update_prompt()
        except Exception:
            console.print(f"[red]Issue not found: {arg}[/red]")

    def do_pwd(self, arg: str) -> None:
        """Show current issue."""
        if self.current_issue:
            console.print(f"[cyan]{self.current_issue}[/cyan]")
        else:
            console.print("[dim]No issue selected[/dim]")

    def _show_issue(self, issue_key: str) -> None:
        """Display issue details."""
        try:
            issue = self.client.get_issue(issue_key)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

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

        if issue.attachments:
            content.append("\n\nAttachments:\n", style="bold")
            for att in issue.attachments:
                content.append(
                    f"  - {att.filename} ({_format_size(att.size)})\n    {att.content_url}\n"
                )

        console.print(Panel(content, title=f"[cyan]{issue.key}[/cyan]"))

    def do_show(self, arg: str) -> None:
        """Show issue details. Usage: show [ISSUE-KEY]"""
        issue_key = arg.strip().upper() if arg.strip() else self.current_issue
        if not issue_key:
            console.print("[yellow]Usage: show ISSUE-KEY or cd into an issue first[/yellow]")
            return
        self._show_issue(issue_key)

    def do_cat(self, arg: str) -> None:
        """Show issue details. Usage: cat [ISSUE-KEY]"""
        self.do_show(arg)

    def do_comments(self, arg: str) -> None:
        """Show comments for current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        try:
            comments = self.client.get_comments(self.current_issue)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

        if not comments:
            console.print("[dim]No comments[/dim]")
            return

        console.print(f"[bold]Comments for {self.current_issue}:[/bold]")
        for c in comments:
            comment_text = Text()
            comment_text.append(f"{c.author}", style="cyan")
            comment_text.append(f" - {c.created.strftime('%Y-%m-%d %H:%M')}", style="dim")
            comment_text.append(f" [id: {c.id}]\n", style="dim")
            comment_text.append(c.body)
            console.print(Panel(comment_text))

    def do_comment(self, arg: str) -> None:
        """Add a comment to current issue. Usage: comment "your comment text" """
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        # Handle quoted text
        text = arg.strip()
        if not text:
            console.print('[yellow]Usage: comment "your comment text"[/yellow]')
            return

        # Remove surrounding quotes if present
        if (text.startswith('"') and text.endswith('"')) or (
            text.startswith("'") and text.endswith("'")
        ):
            text = text[1:-1]

        try:
            self.client.add_comment(self.current_issue, text)
            console.print(f"[green]Comment added to {self.current_issue}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_status(self, arg: str) -> None:
        """Show transitions or change status. Usage: status [NEW_STATUS]"""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        target = arg.strip()

        if not target:
            # Show available transitions
            try:
                transitions = self.client.get_transitions(self.current_issue)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return

            console.print(f"[bold]Available transitions for {self.current_issue}:[/bold]")
            for t in transitions:
                console.print(f"  - {t.name}")
        else:
            # Perform transition
            # Remove quotes if present
            if (target.startswith('"') and target.endswith('"')) or (
                target.startswith("'") and target.endswith("'")
            ):
                target = target[1:-1]

            try:
                self.client.transition_issue(self.current_issue, target)
                console.print(f"[green]{self.current_issue} transitioned to '{target}'[/green]")
            except ValueError as e:
                console.print(f"[red]{e}[/red]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    def do_new(self, arg: str) -> None:
        """Create a new issue. Usage: new PROJECT "Summary" [--type TYPE] [--description "desc"]"""
        try:
            args = shlex.split(arg)
        except ValueError:
            console.print('[yellow]Usage: new PROJECT "Summary" [--type TYPE][/yellow]')
            return

        if len(args) < 2:
            console.print('[yellow]Usage: new PROJECT "Summary" [--type TYPE][/yellow]')
            return

        project = args[0]
        summary = args[1]
        issue_type = "Task"
        description = None

        i = 2
        while i < len(args):
            if args[i] in ("--type", "-t") and i + 1 < len(args):
                issue_type = args[i + 1]
                i += 2
            elif args[i] in ("--description", "-d") and i + 1 < len(args):
                description = args[i + 1]
                i += 2
            else:
                i += 1

        try:
            issue_key = self.client.create_issue(
                project=project,
                summary=summary,
                issue_type=issue_type,
                description=description,
            )
            console.print(f"[green]Created {issue_key}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_edit(self, arg: str) -> None:
        """Edit current issue. Usage: edit [--summary "new"] [--priority High] [--labels "a,b"]"""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        try:
            args = shlex.split(arg)
        except ValueError:
            console.print("[red]Invalid arguments[/red]")
            return

        summary = None
        priority = None
        labels = None
        description = None

        i = 0
        while i < len(args):
            if args[i] in ("--summary", "-s") and i + 1 < len(args):
                summary = args[i + 1]
                i += 2
            elif args[i] in ("--priority", "-p") and i + 1 < len(args):
                priority = args[i + 1]
                i += 2
            elif args[i] in ("--labels", "-l") and i + 1 < len(args):
                labels = [label.strip() for label in args[i + 1].split(",")]
                i += 2
            elif args[i] in ("--description", "-d") and i + 1 < len(args):
                description = args[i + 1]
                i += 2
            else:
                i += 1

        if not any([summary, priority, labels, description]):
            console.print(
                '[yellow]Usage: edit --summary "new" --priority High --labels "a,b"[/yellow]'
            )
            return

        try:
            self.client.update_issue(
                self.current_issue,
                summary=summary,
                priority=priority,
                labels=labels,
                description=description,
            )
            console.print(f"[green]Updated {self.current_issue}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_search(self, arg: str) -> None:
        """Search with JQL. Usage: search "project = PROJ AND status = Open" """
        jql = arg.strip()
        if not jql:
            console.print('[yellow]Usage: search "JQL query"[/yellow]')
            return

        # Remove surrounding quotes if present
        if (jql.startswith('"') and jql.endswith('"')) or (
            jql.startswith("'") and jql.endswith("'")
        ):
            jql = jql[1:-1]

        try:
            issues = self.client.search(jql)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

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
                issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary,
            )

        console.print(table)

    def do_watch(self, arg: str) -> None:
        """Watch current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        try:
            self.client.watch_issue(self.current_issue)
            console.print(f"[green]Now watching {self.current_issue}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_unwatch(self, arg: str) -> None:
        """Stop watching current issue."""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        try:
            self.client.unwatch_issue(self.current_issue)
            console.print(f"[green]Stopped watching {self.current_issue}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_delcomment(self, arg: str) -> None:
        """Delete a comment. Usage: delcomment COMMENT_ID"""
        if not self.current_issue:
            console.print("[yellow]No issue selected. Use 'cd ISSUE-KEY' first.[/yellow]")
            return

        comment_id = arg.strip()
        if not comment_id:
            console.print("[yellow]Usage: delcomment COMMENT_ID[/yellow]")
            return

        try:
            self.client.delete_comment(self.current_issue, comment_id)
            console.print(f"[green]Comment {comment_id} deleted[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_help(self, arg: str) -> None:
        """Show help for commands."""
        if arg:
            # Show help for specific command
            super().do_help(arg)
            return

        help_text = """
[bold]Navigation:[/bold]
  l / ls                  At root: list open issues (-a for all). Inside: show details (-a +comments)
  list                    List your assigned issues
  cd ISSUE-KEY            Select an issue (e.g., cd DAT-123)
  cd .. / ..              Go back to root
  pwd                     Show current issue
  search "JQL"            Search with custom JQL

[bold]Issue commands:[/bold]
  new PROJECT "Summary"   Create new issue (--type TYPE)
  cat ISSUE-KEY           Show issue details (works from anywhere)
  cat / show              Show current issue details (when inside issue)
  edit --summary "new"    Edit fields (--priority, --labels, --description)
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
        console.print(help_text)

    def do_h(self, arg: str) -> None:
        """Alias for help."""
        self.do_help(arg)

    def do_clear(self, arg: str) -> None:
        """Clear the screen."""
        console.clear()

    def do_quit(self, arg: str) -> bool:
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
        console.print()  # Newline after ^D
        return self.do_quit(arg)

    def emptyline(self) -> None:
        """Do nothing on empty line."""
        pass

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        # Handle .. as cd ..
        if line.strip() == "..":
            self.do_cd("..")
            return

        console.print(f"[red]Unknown command: {line}[/red]")
        console.print("[dim]Type 'help' for available commands[/dim]")
