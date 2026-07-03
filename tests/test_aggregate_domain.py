"""Domain-level rollup: apex/www duplication must not inflate the rates."""

from __future__ import annotations

import pandas as pd

from pqreadiness.analysis.aggregate import domain_level_gap


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_domain_counts_once_even_with_two_ready_endpoints():
    df = _df(
        [
            {"domain": "a.gov", "reachable": True, "kex_class": "hybrid_pq", "auth_class": "classical"},
            {"domain": "a.gov", "reachable": True, "kex_class": "hybrid_pq", "auth_class": "classical"},
            {"domain": "b.gov", "reachable": True, "kex_class": "classical", "auth_class": "classical"},
        ]
    )
    gap = domain_level_gap(df)
    # 1 of 2 domains is PQ-KEX ready; endpoint-level would say 2 of 3.
    assert gap["pq_key_exchange"].successes == 1
    assert gap["pq_key_exchange"].total == 2


def test_any_endpoint_semantics():
    df = _df(
        [
            {"domain": "a.gov", "reachable": True, "kex_class": "classical", "auth_class": "classical"},
            {"domain": "a.gov", "reachable": True, "kex_class": "hybrid_pq", "auth_class": "classical"},
        ]
    )
    gap = domain_level_gap(df)
    assert gap["pq_key_exchange"].successes == 1
    assert gap["pq_key_exchange"].total == 1


def test_unreachable_domains_excluded():
    df = _df(
        [
            {"domain": "a.gov", "reachable": False, "kex_class": "unknown", "auth_class": "unknown"},
        ]
    )
    gap = domain_level_gap(df)
    assert gap["pq_key_exchange"].total == 0
