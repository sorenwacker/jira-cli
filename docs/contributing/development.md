# Development

```bash
git clone https://github.com/sorenwacker/jira-cli.git
cd jira-cli
uv sync --extra dev
uv run pre-commit install
```

## Makefile targets

| Target | Action |
|--------|--------|
| `make dev` | Start the interactive shell against your configured instance |
| `make test` | Run the test suite |
| `make lint` | Run every pre-commit hook on all files |
| `make docs` | Serve this documentation with hot reload |
| `make docs-build` | Build the static site into `site/` |

## Gates

Every commit passes ruff (lint and format), mypy, vulture, pylint, a function-length check, and pytest through pre-commit. Two tests encode project rules rather than behavior:

- `tests/test_surface_parity.py`: every MCP tool has a CLI command and vice versa.
- `tests/test_mcp_instructions.py`: the writing guidance reaches the server instructions and the tool descriptions that depend on it.

## Workflow

Documentation is updated first, then tests, then the implementation. A branch gets a pull request when pushed. Releases are tag-driven and cut by the repository owner; the documentation site deploys from `main` through GitHub Pages.
