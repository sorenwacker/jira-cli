"""Gate: every declared dependency is bounded below the next major version."""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
UPPER_BOUND_OPERATORS = {"<", "<=", "==", "===", "~="}


def _declared_requirements() -> dict[str, list[str]]:
    """Return every declared requirement, grouped by where it is declared."""
    data = tomllib.loads(PYPROJECT.read_text())
    project = data["project"]
    groups: dict[str, list[str]] = {"dependencies": project["dependencies"]}
    for name, specs in project.get("optional-dependencies", {}).items():
        groups[f"optional-dependencies.{name}"] = specs
    for name, specs in data.get("dependency-groups", {}).items():
        groups[f"dependency-groups.{name}"] = specs
    return groups


def _is_bounded(spec: str) -> bool:
    """Whether a requirement forbids the next major release."""
    return any(s.operator in UPPER_BOUND_OPERATORS for s in Requirement(spec).specifier)


def test_every_dependency_has_an_upper_bound() -> None:
    """An unbounded requirement lets a future major break fresh installs."""
    unbounded = {
        f"{group}: {spec}"
        for group, specs in _declared_requirements().items()
        for spec in specs
        if not _is_bounded(spec)
    }
    assert not unbounded


def test_requirements_are_parseable() -> None:
    """Guards the gate itself against a malformed requirement string."""
    groups = _declared_requirements()
    assert groups["dependencies"]
    for specs in groups.values():
        for spec in specs:
            assert Requirement(spec).name
