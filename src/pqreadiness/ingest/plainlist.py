"""Read a plain ranked domain list (e.g., Tranco: `rank,domain` per line).

Used for the same-instrument general-population baseline: the exact pipeline
that measures the federal population runs unchanged over a public ranking.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import Tier


def load_plain_domains(csv_path: str | Path, limit: int = 0) -> list[tuple[str, Tier, str]]:
    """Return (domain, tier=OTHER, agency="") triples from a rank,domain CSV."""
    rows: list[tuple[str, Tier, str]] = []
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        for line in csv.reader(fh):
            if not line:
                continue
            domain = line[-1].strip().lower()
            if not domain or domain.startswith("#"):
                continue
            rows.append((domain, Tier.OTHER, ""))
            if limit and len(rows) >= limit:
                break
    return rows
