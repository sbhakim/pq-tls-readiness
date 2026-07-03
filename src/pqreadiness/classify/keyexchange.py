"""Classify the key-exchange side of an endpoint.

We take the outcomes from all probe profiles and pick the *strongest* group
seen. That gives a capability lower bound: if any profile got a hybrid group,
the endpoint is hybrid-capable.
"""

from __future__ import annotations

from ..models import KexClass, ProbeOutcome
from .registry import Registry

# Ranking so we can pick the "best" class seen across profiles.
_RANK = {
    KexClass.CLASSICAL: 1,
    KexClass.HYBRID_PQ: 2,
    KexClass.PURE_PQ: 3,
}


def classify_key_exchange(
    probes: list[ProbeOutcome],
    registry: Registry,
) -> tuple[str | None, KexClass]:
    """Return (best_group_name, best_kex_class) across all probe outcomes."""
    best_group: str | None = None
    best_class = KexClass.UNKNOWN

    for outcome in probes:
        if not outcome.reachable or not outcome.negotiated_group:
            continue
        raw_class = registry.group_class(outcome.negotiated_group)
        if raw_class is None:
            # Reachable but the group is not in our registry: mark unknown but
            # keep the raw name so we can add it later.
            if best_group is None:
                best_group = outcome.negotiated_group
            continue

        kex_class = KexClass(raw_class)
        if _RANK.get(kex_class, 0) > _RANK.get(best_class, 0):
            best_class = kex_class
            best_group = outcome.negotiated_group

    return best_group, best_class
