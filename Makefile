.PHONY: dev test lint docs docs-build

dev:
	uv run jira shell

test:
	uv run pytest

lint:
	uv run pre-commit run --all-files

docs:
	uv run zensical serve

docs-build:
	uv run zensical build
