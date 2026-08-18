"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from jira_cli.config import (
    JiraConfig,
    get_config_path,
    load_config,
    load_writing_guidance,
    save_config,
)


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

        # Only set JIRA_URL, clear others to test partial override
        env = {"JIRA_URL": "https://env.atlassian.net"}
        with patch.dict(os.environ, env, clear=True):
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

    def test_save_config_escapes_special_characters(self, tmp_path: Path) -> None:
        """A token with quotes or backslashes round-trips through save/load."""
        config_file = tmp_path / "config.toml"
        token = 'to"ken\\with"specials'
        config = JiraConfig(
            url="https://test.atlassian.net",
            email="test@example.com",
            api_token=token,
        )

        save_config(config, config_path=config_file)
        with patch.dict(os.environ, {}, clear=True):
            loaded = load_config(config_path=config_file)

        assert loaded.api_token == token

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


class TestLoadWritingGuidance:
    """Tests for the writing guidance override file."""

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """No guidance file means no override."""
        assert load_writing_guidance(guidance_path=tmp_path / "guidance.md") is None

    def test_returns_file_content(self, tmp_path: Path) -> None:
        """The guidance file content is returned stripped."""
        guidance_file = tmp_path / "guidance.md"
        guidance_file.write_text("Write tickets as user stories.\n")

        content = load_writing_guidance(guidance_path=guidance_file)

        assert content == "Write tickets as user stories."

    def test_empty_file_is_treated_as_absent(self, tmp_path: Path) -> None:
        """An empty or whitespace-only file means no override."""
        guidance_file = tmp_path / "guidance.md"
        guidance_file.write_text("  \n")

        assert load_writing_guidance(guidance_path=guidance_file) is None

    def test_default_path_is_next_to_config(self) -> None:
        """The default guidance path lives in the jira-cli config directory."""
        from jira_cli.config import get_guidance_path

        path = get_guidance_path()

        assert path.name == "guidance.md"
        assert path.parent == get_config_path().parent
