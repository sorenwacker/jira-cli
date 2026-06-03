"""Configuration management for Jira CLI."""

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator


class JiraConfig(BaseModel):
    """Jira connection configuration."""

    url: str
    email: str
    api_token: str

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        """Remove trailing slashes from URL."""
        return v.rstrip("/")


def get_config_path() -> Path:
    """Get the default configuration file path."""
    config_dir = Path.home() / ".config" / "jira-cli"
    return config_dir / "config.toml"


def _load_file_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from TOML file if it exists."""
    if config_path.exists():
        with config_path.open("rb") as f:
            return tomllib.load(f)
    return {}


def _get_config_values(file_config: dict[str, Any]) -> tuple[str | None, ...]:
    """Get config values from environment or file, env takes precedence."""
    url = os.environ.get("JIRA_URL") or file_config.get("url")
    email = os.environ.get("JIRA_EMAIL") or file_config.get("email")
    api_token = os.environ.get("JIRA_API_TOKEN") or file_config.get("api_token")
    return url, email, api_token


def _validate_required(url: str | None, email: str | None, token: str | None) -> None:
    """Validate that all required config values are present."""
    missing = []
    if not url:
        missing.append("JIRA_URL")
    if not email:
        missing.append("JIRA_EMAIL")
    if not token:
        missing.append("JIRA_API_TOKEN")
    if missing:
        msg = f"Missing required configuration: {', '.join(missing)}"
        raise ValueError(msg)


def load_config(config_path: Path | None = None) -> JiraConfig:
    """Load configuration from file and/or environment variables.

    Environment variables take precedence over file values.

    Args:
        config_path: Path to config file. Defaults to ~/.config/jira-cli/config.toml

    Returns:
        JiraConfig with loaded values.

    Raises:
        ValueError: If required configuration values are missing.
    """
    if config_path is None:
        config_path = get_config_path()

    file_config = _load_file_config(config_path)
    url, email, api_token = _get_config_values(file_config)
    _validate_required(url, email, api_token)

    # After validation, all values are guaranteed to be non-None strings
    return JiraConfig(url=str(url), email=str(email), api_token=str(api_token))


def save_config(config: JiraConfig, config_path: Path | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Path to config file. Defaults to ~/.config/jira-cli/config.toml
    """
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""url = "{config.url}"
email = "{config.email}"
api_token = "{config.api_token}"
"""
    config_path.write_text(content)
