"""Target expansion + de-duplication."""

from __future__ import annotations

from pqreadiness.ingest.targets import build_targets
from pqreadiness.models import Tier


def test_expands_apex_and_www():
    targets = build_targets([("example.gov", Tier.FEDERAL, "Example Agency")], ["apex", "www"])
    hosts = {t.hostname for t in targets}
    assert hosts == {"example.gov", "www.example.gov"}


def test_dedupes_repeated_hosts():
    domains = [
        ("example.gov", Tier.FEDERAL, "Example Agency"),
        ("example.gov", Tier.FEDERAL, "Example Agency"),
    ]
    targets = build_targets(domains, ["apex"])
    assert len(targets) == 1


def test_tier_and_agency_are_carried_through():
    targets = build_targets([("state.tx.us", Tier.STATE_LOCAL, "Texas")], ["apex"])
    assert targets[0].tier is Tier.STATE_LOCAL
    assert targets[0].agency == "Texas"
