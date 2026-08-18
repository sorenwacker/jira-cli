"""Tests for Confluence configuration resolution."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from jira_cli.config import ConfluenceConfig, load_confluence_config


class TestConfluenceConfig:
    """Tests for ConfluenceConfig model."""

    def test_url_normalization(self) -> None:
        """Trailing slashes are removed from URL."""
        config = ConfluenceConfig(
            url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="token123",
        )

        assert config.url == "https://test.atlassian.net"


class TestLoadConfluenceConfig:
    """Tests for loading Confluence configuration."""

    def test_falls_back_to_jira_env_vars(self) -> None:
        """Confluence reuses Jira environment variables when present."""
        env = {
            "JIRA_URL": "https://env.atlassian.net",
            "JIRA_EMAIL": "env@example.com",
            "JIRA_API_TOKEN": "env-token",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_confluence_config()

        assert config.url == "https://env.atlassian.net"
        assert config.email == "env@example.com"
        assert config.api_token == "env-token"

    def test_confluence_env_vars_take_precedence(self) -> None:
        """Confluence-specific variables override the Jira variables."""
        env = {
            "JIRA_URL": "https://jira.atlassian.net",
            "JIRA_EMAIL": "jira@example.com",
            "JIRA_API_TOKEN": "jira-token",
            "CONFLUENCE_URL": "https://wiki.atlassian.net",
            "CONFLUENCE_EMAIL": "wiki@example.com",
            "CONFLUENCE_API_TOKEN": "wiki-token",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_confluence_config()

        assert config.url == "https://wiki.atlassian.net"
        assert config.email == "wiki@example.com"
        assert config.api_token == "wiki-token"

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Config can be loaded from the shared TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
url = "https://file.atlassian.net"
email = "file@example.com"
api_token = "file-token"
"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = load_confluence_config(config_path=config_file)

        assert config.url == "https://file.atlassian.net"
        assert config.email == "file@example.com"
        assert config.api_token == "file-token"

    def test_missing_config_raises_error(self, tmp_path: Path) -> None:
        """Missing required config raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required"):
                load_confluence_config(config_path=tmp_path / "nonexistent.toml")
