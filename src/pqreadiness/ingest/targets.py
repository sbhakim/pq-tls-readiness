"""Turn (domain, tier) pairs into concrete hostnames to probe.

For each domain we try a set of variants (apex and/or www). De-duplication
keeps us from probing the same hostname twice.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Target, Tier


def _hostnames(domain: str, variants: Iterable[str]) -> list[str]:
    """Expand a domain into hostnames based on the requested variants."""
    hosts: list[str] = []
    for variant in variants:
        if variant == "apex":
            hosts.append(domain)
        elif variant == "www":
            hosts.append(f"www.{domain}")
    return hosts


def build_targets(
    domains: list[tuple[str, Tier, str]],
    variants: Iterable[str],
) -> list[Target]:
    """Build a de-duplicated list of Target objects."""
    variants = list(variants)
    seen: set[str] = set()
    targets: list[Target] = []

    for domain, tier, agency in domains:
        for host in _hostnames(domain, variants):
            if host in seen:
                continue
            seen.add(host)
            targets.append(Target(domain=domain, hostname=host, tier=tier, agency=agency))
    return targets
