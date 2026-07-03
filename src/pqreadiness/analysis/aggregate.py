"""Turn a results CSV into the tables the paper reports.

Everything here operates on a pandas DataFrame loaded from the results CSV, so
it works the same on a 150-row pilot or the full population.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .statistics import Proportion, wilson_interval


def load_results(csv_path: str | Path) -> pd.DataFrame:
    """Load a results CSV into a DataFrame."""
    return pd.read_csv(csv_path)


def _rate(df: pd.DataFrame, mask: pd.Series) -> Proportion:
    """Wilson interval for the fraction of reachable rows matching `mask`."""
    reachable = df[df["reachable"] == True]  # noqa: E712 (pandas mask needs ==)
    total = len(reachable)
    successes = int(mask.loc[reachable.index].sum())
    return wilson_interval(successes, total)


def kex_vs_auth_gap(df: pd.DataFrame) -> dict[str, Proportion]:
    """The headline: PQ key-exchange adoption vs PQ authentication adoption."""
    pq_kex = df["kex_class"].isin(["hybrid_pq", "pure_pq"])
    pq_auth = df["auth_class"] == "pq"
    return {
        "pq_key_exchange": _rate(df, pq_kex),
        "pq_authentication": _rate(df, pq_auth),
    }


def by_tier(df: pd.DataFrame) -> dict[str, dict[str, Proportion]]:
    """PQ-KEX and PQ-auth rates split by government tier (federal vs state)."""
    out: dict[str, dict[str, Proportion]] = {}
    for tier, group in df.groupby("tier"):
        out[str(tier)] = kex_vs_auth_gap(group)
    return out


def by_hosting(df: pd.DataFrame) -> dict[str, dict[str, Proportion]]:
    """Same rates split by CDN vs origin, to see who drives readiness."""
    out: dict[str, dict[str, Proportion]] = {}
    df = df.copy()
    df["hosting"] = df["is_cdn"].map({True: "cdn", False: "origin"})
    for hosting, group in df.groupby("hosting"):
        out[str(hosting)] = kex_vs_auth_gap(group)
    return out


def domain_level_gap(df: pd.DataFrame) -> dict[str, Proportion]:
    """The gap computed over domains instead of endpoints.

    An apex and its www endpoint usually terminate on the same infrastructure,
    so endpoint rows are not independent samples. Here a domain counts as
    PQ-ready if *any* of its reachable endpoints is, and the denominator is
    the number of domains with at least one reachable endpoint. Confidence
    intervals over this unit are not inflated by per-domain duplication.
    """
    reachable = df[df["reachable"] == True]  # noqa: E712 (pandas mask needs ==)
    if reachable.empty:
        return {
            "pq_key_exchange": wilson_interval(0, 0),
            "pq_authentication": wilson_interval(0, 0),
        }
    grouped = reachable.groupby("domain")
    pq_kex = grouped["kex_class"].apply(
        lambda s: bool(s.isin(["hybrid_pq", "pure_pq"]).any())
    )
    pq_auth = grouped["auth_class"].apply(lambda s: bool((s == "pq").any()))
    total = len(pq_kex)
    return {
        "pq_key_exchange": wilson_interval(int(pq_kex.sum()), total),
        "pq_authentication": wilson_interval(int(pq_auth.sum()), total),
    }


def by_agency(df: pd.DataFrame) -> pd.DataFrame:
    """Domain-level readiness per owning agency.

    The mandate binds agencies, not domains, so this is the compliance view:
    one row per agency with reachable-domain counts and PQ key-exchange /
    authentication rates under any-endpoint semantics.
    """
    reachable = df[df["reachable"] == True]  # noqa: E712 (pandas mask needs ==)
    if reachable.empty:
        return pd.DataFrame(
            columns=["agency", "domains", "pq_kex_domains", "pq_kex_rate", "pq_auth_domains"]
        )
    grouped = reachable.groupby(["agency", "domain"])
    dom = pd.DataFrame({
        "pq_kex": grouped["kex_class"].apply(
            lambda s: bool(s.isin(["hybrid_pq", "pure_pq"]).any())
        ),
        "pq_auth": grouped["auth_class"].apply(lambda s: bool((s == "pq").any())),
    }).reset_index()
    agg = dom.groupby("agency").agg(
        domains=("domain", "nunique"),
        pq_kex_domains=("pq_kex", "sum"),
        pq_auth_domains=("pq_auth", "sum"),
    ).reset_index()
    agg["pq_kex_rate"] = agg["pq_kex_domains"] / agg["domains"]
    return agg.sort_values(["pq_kex_domains", "domains"], ascending=False)
