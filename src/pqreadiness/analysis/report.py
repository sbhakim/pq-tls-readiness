"""Render aggregated numbers as plain-text tables for the console / logs."""

from __future__ import annotations

import pandas as pd

from .aggregate import by_hosting, by_tier, domain_level_gap, kex_vs_auth_gap
from .statistics import Proportion


def _fmt(p: Proportion) -> str:
    """Format a proportion as 'rate% (low–high, n=total)'."""
    return f"{p.rate * 100:5.1f}%  [{p.low * 100:4.1f}–{p.high * 100:4.1f}]  n={p.total}"


def summarize(df: pd.DataFrame) -> str:
    """Build a human-readable summary of the whole result set."""
    lines: list[str] = []

    lines.append("=== Overall: key exchange vs authentication (endpoints) ===")
    for label, prop in kex_vs_auth_gap(df).items():
        lines.append(f"  {label:20s} {_fmt(prop)}")

    lines.append("")
    lines.append("=== Domain-level (any reachable endpoint counts) ===")
    for label, prop in domain_level_gap(df).items():
        lines.append(f"  {label:20s} {_fmt(prop)}")

    lines.append("")
    lines.append("=== By tier ===")
    for tier, rates in by_tier(df).items():
        lines.append(f"  [{tier}]")
        for label, prop in rates.items():
            lines.append(f"    {label:18s} {_fmt(prop)}")

    lines.append("")
    lines.append("=== By hosting (CDN vs origin) ===")
    for hosting, rates in by_hosting(df).items():
        lines.append(f"  [{hosting}]")
        for label, prop in rates.items():
            lines.append(f"    {label:18s} {_fmt(prop)}")

    return "\n".join(lines)
