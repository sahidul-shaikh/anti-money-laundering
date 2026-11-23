"""What the build leaves behind for the next one.

This is the whole argument. A delivery that produces an agent and a repository
has produced one agent. A delivery that produces an agent and a library has
produced the ability to make the next one cheaper. The counter here is the
only evidence for that claim, so it has to be honest: an asset is inherited
only if it was already on disk before this build started.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Kept apart from the previous product's library so the compounding
# counters can never pick up assets this factory did not create.
ROOT = Path(__file__).resolve().parents[2] / "library" / "aml"


@dataclass
class Library:
    """Skills, patterns and controls that persist between builds."""

    root: Path = ROOT
    created: list[str] = field(default_factory=list)
    inherited: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def begin_build(self) -> None:
        """Reset the per-build tallies. Two builds must not share a count."""
        self.created = []
        self.inherited = []

    def path_for(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def acquire(self, name: str, body: dict) -> tuple[dict, bool]:
        """Return the asset and whether it already existed.

        Existing assets are read, not overwritten: the second product uses
        what the first left, rather than quietly rewriting it.
        """
        path = self.path_for(name)
        if path.exists():
            self.inherited.append(name)
            return json.loads(path.read_text()), True
        path.write_text(json.dumps(body, indent=2))
        self.created.append(name)
        return body, False

    def skill(self, name: str) -> str:
        """The procedural knowledge for one discipline, from the library.

        A skill is content, not a label. Missing is an error worth raising:
        a phase that declares a skill it cannot load is misconfigured.
        """
        path = self.root / "skills" / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"no skill {name!r} in {path.parent}")
        return path.read_text(encoding="utf-8")

    def skills_for(self, names) -> dict[str, str]:
        return {name: self.skill(name) for name in names}

    def summary(self) -> dict:
        total = len(self.created) + len(self.inherited)
        return {
            "created": len(self.created),
            "inherited": len(self.inherited),
            "total": total,
            "reuse_rate": round(len(self.inherited) / total, 4) if total else 0.0,
            "created_names": sorted(self.created),
            "inherited_names": sorted(self.inherited),
            "on_disk": len(list(self.root.glob("*.json"))),
            "skills_on_disk": len(list((self.root / "skills").glob("*.md"))),
        }
