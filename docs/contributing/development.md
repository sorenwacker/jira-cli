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
- `tests/test_dependency_bounds.py`: every declared dependency is bounded below the next major version.
- `tests/test_mcp_instructions.py`: the writing guidance reaches the server instructions and the tool descriptions that depend on it.

## Dependencies

Renovate keeps dependencies current; Dependabot version and security PRs are switched off so the two do not duplicate each other. Dependabot *alerts* stay enabled because Renovate consumes them to raise security updates.

The policy lives in `renovate.json`:

| Update | Handling |
|--------|----------|
| Patch, minor, pin, digest | Opened automatically, merged automatically once CI passes |
| Lock file maintenance | Weekly, merged automatically once CI passes |
| Security fix for an open alert | Raised immediately, labelled `security`, merged automatically once CI passes |
| Major | Opened for manual review, labelled `major` |

Releases must age three days before Renovate proposes them, so a compromised or immediately-yanked release is not pulled in on the day it appears. Security fixes bypass that wait.

Every declared dependency carries an upper bound below the next major (`>=13.0.0,<16`). CI installs with a fresh resolution rather than the lock file, so an unbounded requirement would let a future major break installs while lock-based runs stayed green. Add a bound when adding a dependency; `tests/test_dependency_bounds.py` fails otherwise.

Check the installed set against known advisories with:

```bash
uv run --with pip-audit pip-audit
```

## Workflow

Documentation is updated first, then tests, then the implementation. A branch gets a pull request when pushed. Releases are tag-driven and cut by the repository owner; the documentation site deploys from `main` through GitHub Pages.
