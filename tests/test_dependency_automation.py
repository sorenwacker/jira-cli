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


def _merge_step() -> dict:
    workflow: dict = yaml.safe_load(AUTOMERGE.read_text())
    job: dict = workflow["jobs"]["automerge"]
    assert job["if"] == "github.actor == 'dependabot[bot]'"
    step: dict = job["steps"][-1]
    return step


def test_automerge_is_restricted_to_dependabot_and_skips_majors() -> None:
    """The workflow must not merge human PRs or unreviewed major bumps."""
    assert "version-update:semver-major" in _merge_step()["if"]


def test_automerge_waits_for_ci_without_waiting_on_itself() -> None:
    """Watching every check deadlocks: this job is itself one of the checks."""
    run = _merge_step()["run"]
    assert "gh pr checks" in run
    assert 'select(.name != "automerge")' in run
    assert "--watch" not in run
