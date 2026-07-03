"""Generate the figures for the paper.

Uses the non-interactive 'Agg' backend so this runs on a headless server over
SSH and writes PNG/PDF files directly.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # must be set before importing pyplot
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..analysis.aggregate import by_tier, kex_vs_auth_gap  # noqa: E402


def plot_gap(df: pd.DataFrame, out_dir: str | Path) -> Path:
    """Bar chart of PQ key-exchange vs PQ authentication adoption (the gap)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rates = kex_vs_auth_gap(df)
    labels = ["PQ Key Exchange", "PQ Authentication"]
    values = [rates["pq_key_exchange"].rate * 100, rates["pq_authentication"].rate * 100]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(labels, values, color=["#2b8cbe", "#cc4c02"])
    ax.set_ylabel("Adoption (% of reachable endpoints)")
    ax.set_title("The Post-Quantum Authentication Gap")
    ax.set_ylim(0, 100)
    for i, v in enumerate(values):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center")

    path = out_dir / "gap.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_by_tier(df: pd.DataFrame, out_dir: str | Path) -> Path:
    """Grouped bars: PQ-KEX vs PQ-auth for each government tier."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tiers = by_tier(df)
    names = list(tiers.keys())
    kex = [tiers[t]["pq_key_exchange"].rate * 100 for t in names]
    auth = [tiers[t]["pq_authentication"].rate * 100 for t in names]

    x = range(len(names))
    width = 0.38
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([i - width / 2 for i in x], kex, width, label="PQ Key Exchange", color="#2b8cbe")
    ax.bar([i + width / 2 for i in x], auth, width, label="PQ Authentication", color="#cc4c02")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylabel("Adoption (%)")
    ax.set_title("PQ Readiness by Tier")
    ax.set_ylim(0, 100)
    ax.legend()

    path = out_dir / "by_tier.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_all(df: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    """Produce every figure and return the paths written."""
    return [plot_gap(df, out_dir), plot_by_tier(df, out_dir)]
