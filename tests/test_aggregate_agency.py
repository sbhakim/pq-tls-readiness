"""Per-agency rollup: domain-level counts grouped by owning agency."""

from __future__ import annotations

import pandas as pd

from pqreadiness.analysis.aggregate import by_agency


def test_agency_rollup_counts_domains_once():
    df = pd.DataFrame([
        {"agency": "A", "domain": "x.gov", "reachable": True, "kex_class": "hybrid_pq", "auth_class": "classical"},
        {"agency": "A", "domain": "x.gov", "reachable": True, "kex_class": "classical", "auth_class": "classical"},
        {"agency": "A", "domain": "y.gov", "reachable": True, "kex_class": "classical", "auth_class": "classical"},
        {"agency": "B", "domain": "z.gov", "reachable": True, "kex_class": "classical", "auth_class": "classical"},
        {"agency": "B", "domain": "w.gov", "reachable": False, "kex_class": "unknown", "auth_class": "unknown"},
    ])
    agg = by_agency(df).set_index("agency")
    assert agg.loc["A", "domains"] == 2
    assert agg.loc["A", "pq_kex_domains"] == 1
    assert agg.loc["B", "domains"] == 1
    assert agg.loc["B", "pq_kex_domains"] == 0


def test_agency_rollup_empty():
    df = pd.DataFrame([{"agency": "A", "domain": "x.gov", "reachable": False,
                        "kex_class": "unknown", "auth_class": "unknown"}])
    assert by_agency(df).empty
