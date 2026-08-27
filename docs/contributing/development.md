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
- `tests/test_dependency_automation.py`: Dependabot covers every ecosystem in the repo and the automerge workflow stays restricted to non-major Dependabot PRs.
- `tests/test_mcp_instructions.py`: the writing guidance reaches the server instructions and the tool descriptions that depend on it.

## Dependencies

Dependabot keeps dependencies current. It is native to GitHub, so there is no third-party app to install: `.github/dependabot.yml` is the whole configuration.

| Update | Handling |
|--------|----------|
| Patch and minor, Python and Actions | Grouped into one weekly PR per ecosystem, merged automatically once CI passes |
| Security fix for an open alert | Raised as soon as the advisory lands, merged automatically once CI passes |
| Major | Opened on its own for manual review |

`.github/workflows/dependabot-automerge.yml` performs the merge. It runs only for pull requests opened by `dependabot[bot]`, skips major updates, waits for the CI run to finish with `gh pr checks --watch --fail-fast`, and only then squashes. Waiting on the checks rather than enabling GitHub auto-merge is deliberate: `main` carries no required status checks, so auto-merge would land the PR without waiting for anything.

Every declared dependency carries an upper bound below the next major (`>=13.0.0,<16`). CI installs with a fresh resolution rather than the lock file, so an unbounded requirement would let a future major break installs while lock-based runs stayed green. Add a bound when adding a dependency; `tests/test_dependency_bounds.py` fails otherwise.

Check the installed set against known advisories with:

```bash
uv run --with pip-audit pip-audit
```

Refresh every locked version at once with `uv lock --upgrade`, then run the gates before committing.

## Code scanning

CodeQL analyses the Python sources on every push to `main`, on every pull request, and weekly, using the `security-and-quality` query suite. Findings appear under the repository's Security tab rather than as a failing check, so a new alert does not block a merge. `.github/workflows/codeql.yml` holds the configuration.

## Workflow

Documentation is updated first, then tests, then the implementation. A branch gets a pull request when pushed. Releases are tag-driven and cut by the repository owner; the documentation site deploys from `main` through GitHub Pages.
