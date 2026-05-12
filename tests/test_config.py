"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from jira_cli.config import JiraConfig, get_config_path, load_config, save_config


class TestJiraConfig:
    """Tests for JiraConfig model."""

    def test_create_config(self) -> None:
        """Config can be created with required fields."""
        config = JiraConfig(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token123",
        )

        assert config.url == "https://test.atlassian.net"
        assert config.email == "test@example.com"
        assert config.api_token == "token123"

    def test_url_normalization(self) -> None:
        """Trailing slashes are removed from URL."""
        config = JiraConfig(
            url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="token123",
        )

        assert config.url == "https://test.atlassian.net"


class TestLoadConfig:
    """Tests for loading configuration."""

    def test_load_from_env_vars(self) -> None:
        """Config can be loaded from environment variables."""
        env = {
            "JIRA_URL": "https://env.atlassian.net",
            "JIRA_EMAIL": "env@example.com",
            "JIRA_API_TOKEN": "env-token",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()

        assert config.url == "https://env.atlassian.net"
        assert config.email == "env@example.com"
        assert config.api_token == "env-token"

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Config can be loaded from TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
url = "https://file.atlassian.net"
email = "file@example.com"
api_token = "file-token"
"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = load_config(config_path=config_file)

        assert config.url == "https://file.atlassian.net"
        assert config.email == "file@example.com"
        assert config.api_token == "file-token"

    def test_env_vars_override_file(self, tmp_path: Path) -> None:
        """Environment variables take precedence over config file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
url = "https://file.atlassian.net"
email = "file@example.com"
api_token = "file-token"
"""
        )

        env = {"JIRA_URL": "https://env.atlassian.net"}
        with patch.dict(os.environ, env, clear=False):
            config = load_config(config_path=config_file)

        assert config.url == "https://env.atlassian.net"
        assert config.email == "file@example.com"

    def test_missing_config_raises_error(self, tmp_path: Path) -> None:
        """Missing required config raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required"):
                load_config(config_path=tmp_path / "nonexistent.toml")


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_config(self, tmp_path: Path) -> None:
        """Config can be saved to TOML file."""
        config_file = tmp_path / "config.toml"
        config = JiraConfig(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token123",
        )

        save_config(config, config_path=config_file)

        assert config_file.exists()
        content = config_file.read_text()
        assert "https://test.atlassian.net" in content
        assert "test@example.com" in content
        assert "token123" in content

    def test_save_config_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Save creates parent directories if needed."""
        config_file = tmp_path / "subdir" / "config.toml"
        config = JiraConfig(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token123",
        )

        save_config(config, config_path=config_file)

        assert config_file.exists()


class TestGetConfigPath:
    """Tests for config path resolution."""

    def test_default_config_path(self) -> None:
        """Default config path is in user config directory."""
        path = get_config_path()

        assert path.name == "config.toml"
        assert "jira-cli" in str(path)
