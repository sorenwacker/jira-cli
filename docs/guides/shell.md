# Interactive Shell

```bash
jira shell
```

The shell models issues as a directory tree: `cd` into an issue, then run issue commands without repeating the key. Commands and comment IDs have tab completion.

## Navigation

| Command | Description |
|---------|-------------|
| `l` / `ls` | At root: list open issues (`-a` includes Done). Inside an issue: show details |
| `list` | List your assigned issues |
| `cd ISSUE-KEY` | Select an issue |
| `cd ..` / `..` | Go back to root |
| `pwd` | Show current issue |
| `search "JQL"` | Search with custom JQL |

## Issue commands

| Command | Description |
|---------|-------------|
| `new PROJECT "Summary"` | Create an issue (`--type TYPE`, `--description`) |
| `cat ISSUE-KEY` | Show issue details from anywhere |
| `cat` / `show` | Show the current issue |
| `edit --summary "new"` | Edit fields (`--priority`, `--labels`, `--description`) |
| `comments` | Show comments |
| `comment "text"` | Add a comment |
| `editcomment ID "text"` | Replace a comment's text |
| `delcomment ID` | Delete a comment |
| `status` | Show available transitions |
| `status "New Status"` | Change status |
| `watch` / `unwatch` | Watch or unwatch the current issue |

## General

| Command | Description |
|---------|-------------|
| `clear` | Clear the screen |
| `h` / `help` | Show help |
| `exit` / `quit` / `q` | Exit |
