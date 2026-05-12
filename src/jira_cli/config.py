"""Configuration management for Jira CLI."""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


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

    # Start with file config if it exists
    file_config: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)

    # Environment variables override file config
    url = os.environ.get("JIRA_URL") or file_config.get("url")
    email = os.environ.get("JIRA_EMAIL") or file_config.get("email")
    api_token = os.environ.get("JIRA_API_TOKEN") or file_config.get("api_token")

    # Validate required fields
    missing = []
    if not url:
        missing.append("JIRA_URL")
    if not email:
        missing.append("JIRA_EMAIL")
    if not api_token:
        missing.append("JIRA_API_TOKEN")

    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    return JiraConfig(url=url, email=email, api_token=api_token)


def save_config(config: JiraConfig, config_path: Path | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Path to config file. Defaults to ~/.config/jira-cli/config.toml
    """
    if config_path is None:
        config_path = get_config_path()

    # Create parent directories if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write TOML format
    content = f"""url = "{config.url}"
email = "{config.email}"
api_token = "{config.api_token}"
"""
    config_path.write_text(content)
