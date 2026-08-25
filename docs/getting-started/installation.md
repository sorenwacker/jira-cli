# Installation

Requires Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/).

## Global install

```bash
uv tool install git+https://github.com/sorenwacker/jira-cli.git
```

This installs three commands: `jira`, `confluence`, and `jira-mcp`.

## From a clone

```bash
git clone https://github.com/sorenwacker/jira-cli.git
cd jira-cli
uv sync --extra dev
uv run jira --help
```

## See Also

- [Configuration](configuration.md)
