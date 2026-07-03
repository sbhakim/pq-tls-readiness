"""Read the CISA .gov domain list.

The CISA `current-federal.csv` / `current-full.csv` files have columns like:

    Domain name, Domain type, Agency, Organization, City, State, ...

We only need the domain name and enough context to assign a tier
(federal vs state/local).
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import Tier

# "Domain type" values that CISA uses for non-federal entries.
_STATE_LOCAL_TYPES = {"state", "local", "county", "city", "tribal", "territory"}


def _tier_for(domain_type: str) -> Tier:
    """Map a CISA 'Domain type' value to our Tier enum."""
    value = domain_type.strip().lower()
    if value == "federal - executive" or value.startswith("federal"):
        return Tier.FEDERAL
    if any(token in value for token in _STATE_LOCAL_TYPES):
        return Tier.STATE_LOCAL
    return Tier.OTHER


def load_domains(csv_path: str | Path) -> list[tuple[str, Tier]]:
    """Return a list of (domain, tier) pairs from a CISA CSV.

    Tolerant of column-name casing and extra columns.
    """
    rows: list[tuple[str, Tier]] = []
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        # Normalize headers so lookups are case-insensitive.
        fields = {name.lower(): name for name in (reader.fieldnames or [])}
        domain_col = fields.get("domain name") or fields.get("domain")
        type_col = fields.get("domain type") or fields.get("type")
        if domain_col is None:
            raise ValueError("CSV has no 'Domain name' column")

        for row in reader:
            domain = (row.get(domain_col) or "").strip().lower()
            if not domain:
                continue
            domain_type = row.get(type_col, "") if type_col else ""
            rows.append((domain, _tier_for(domain_type)))
    return rows
