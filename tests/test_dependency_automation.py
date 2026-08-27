"""Gate: dependency updates stay automated through GitHub-native config."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
AUTOMERGE = ROOT / ".github" / "workflows" / "dependabot-automerge.yml"


def _dependabot_config() -> dict:
    config: dict = yaml.safe_load(DEPENDABOT.read_text())
    return config


def test_dependabot_covers_every_ecosystem_in_use() -> None:
    """A manifest with no Dependabot entry is never updated by anything."""
    ecosystems = {u["package-ecosystem"] for u in _dependabot_config()["updates"]}
    expected = set()
    if (ROOT / "pyproject.toml").exists():
        expected.add("uv")
    if list((ROOT / ".github" / "workflows").glob("*.yml")):
        expected.add("github-actions")
    assert expected <= ecosystems


def test_every_update_entry_has_a_schedule() -> None:
    """Without a schedule Dependabot cannot decide when to run."""
    for update in _dependabot_config()["updates"]:
        assert update["schedule"]["interval"]


def test_automerge_is_restricted_to_dependabot_and_skips_majors() -> None:
    """The workflow must not merge human PRs or unreviewed major bumps."""
    workflow: dict = yaml.safe_load(AUTOMERGE.read_text())
    job = workflow["jobs"]["automerge"]
    assert job["if"] == "github.actor == 'dependabot[bot]'"
    merge_step = job["steps"][-1]
    assert "version-update:semver-major" in merge_step["if"]
    assert "--watch" in merge_step["run"]
