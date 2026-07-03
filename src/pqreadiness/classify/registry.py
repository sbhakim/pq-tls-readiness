"""Load the identifier registries from YAML.

The registries are the single source of truth for "which group/signature is
classical vs PQ". Keeping them in YAML (not code) means updating for a new
standard is a config change, not a code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class GroupEntry:
    name: str
    aliases: list[str]
    klass: str


@dataclass
class SignatureEntry:
    name: str
    match: list[str]
    klass: str


class Registry:
    """Holds the parsed group and signature tables plus fast lookups."""

    def __init__(self, groups: list[GroupEntry], signatures: list[SignatureEntry]) -> None:
        self.groups = groups
        self.signatures = signatures
        # Pre-build a lowercase alias -> class map for O(1) group lookups.
        self._group_index: dict[str, str] = {}
        for entry in groups:
            for token in [entry.name, *entry.aliases]:
                self._group_index[token.lower()] = entry.klass

    def group_class(self, raw: str | None) -> str | None:
        """Return the class for a negotiated group name, or None if unknown."""
        if not raw:
            return None
        return self._group_index.get(raw.lower())

    def signature_class(self, raw: str | None) -> str | None:
        """Return the class for a certificate signature algorithm, or None.

        Matching is substring-based on a normalized form because OpenSSL prints
        signature names in several styles.
        """
        if not raw:
            return None
        norm = raw.lower().replace(" ", "").replace("_", "")
        for entry in self.signatures:
            if any(token.replace("_", "") in norm for token in entry.match):
                return entry.klass
        return None


def load_registry(groups_path: str | Path, signatures_path: str | Path) -> Registry:
    """Build a Registry from the two YAML files."""
    groups_raw = yaml.safe_load(Path(groups_path).read_text())["groups"]
    sigs_raw = yaml.safe_load(Path(signatures_path).read_text())["signatures"]

    groups = [
        GroupEntry(name=g["name"], aliases=g.get("aliases", []), klass=g["class"])
        for g in groups_raw
    ]
    signatures = [
        SignatureEntry(name=s["name"], match=s["match"], klass=s["class"])
        for s in sigs_raw
    ]
    return Registry(groups=groups, signatures=signatures)
