"""Tag an endpoint as CDN or origin.

This matters a lot for government domains: many sit behind Cloudflare/Akamai,
which already do hybrid key exchange. Without this tag you might credit an
agency for readiness that actually comes from its CDN.

Two independent signals feed the tag, and either is sufficient:

1. ASN: resolve the endpoint IP to an ASN (via an AsnResolver), then look the
   ASN up in the CDN directory.
2. CNAME: follow the hostname's CNAME chain and match each target against
   known CDN hostname suffixes (e.g. `cloudfront.net`, `edgekey.net`).

The CNAME signal exists because ASN alone under-detects: a CDN-fronted host
can resolve to an address the ASN database cannot attribute (IPv6 ranges,
missing prefixes), and cloud ASNs like AWS cover both CDN and plain hosting.
The record keeps `cdn_via` ("asn" or "cname") so the attribution is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..models import Hosting
from ..utils.shell import run
from .asn import AsnResolver


@dataclass
class CdnDirectory:
    """Known CDN fingerprints: ASN -> name and CNAME suffix -> name."""

    by_asn: dict[int, str]
    by_cname_suffix: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CdnDirectory":
        raw = yaml.safe_load(Path(path).read_text())
        by_asn = {int(item["asn"]): item["name"] for item in raw["cdns"]}
        by_cname = [
            (item["suffix"].lower().strip("."), item["name"])
            for item in raw.get("cname_suffixes", [])
        ]
        return cls(by_asn=by_asn, by_cname_suffix=by_cname)

    def lookup(self, asn: int | None) -> tuple[bool, str | None]:
        """Return (is_cdn, cdn_name) for an ASN."""
        if asn is None:
            return False, None
        name = self.by_asn.get(asn)
        return (name is not None), name

    def lookup_cname(self, cname_targets: list[str]) -> tuple[bool, str | None]:
        """Return (is_cdn, cdn_name) if any CNAME target has a known suffix."""
        for target in cname_targets:
            host = target.lower().rstrip(".")
            for suffix, name in self.by_cname_suffix:
                if host == suffix or host.endswith("." + suffix):
                    return True, name
        return False, None


def cname_chain(hostname: str, *, timeout_s: int = 5) -> list[str]:
    """Return the CNAME targets for a hostname, in chain order.

    Uses `dig +noall +answer`, which prints the full resolution chain. If dig
    is unavailable or the query fails, returns [] so attribution degrades to
    the ASN signal alone instead of failing the scan.
    """
    result = run(["dig", "+noall", "+answer", hostname], timeout_s=timeout_s)
    if not result.ok:
        return []
    targets: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        # "www.x.gov.  300  IN  CNAME  x.cdn.cloudflare.net."
        if len(parts) >= 5 and parts[3].upper() == "CNAME":
            targets.append(parts[4])
    return targets


def enrich_hosting(
    ip: str | None,
    resolver: AsnResolver,
    directory: CdnDirectory,
    hostname: str | None = None,
) -> Hosting:
    """Combine the ASN and CNAME signals into one Hosting record.

    The ASN signal is cheap and checked first; the CNAME chain (one dig
    query) runs only when the ASN did not already identify a CDN.
    """
    asn = resolver.lookup(ip)
    is_cdn, cdn_name = directory.lookup(asn)
    cdn_via = "asn" if is_cdn else None

    if not is_cdn and hostname and directory.by_cname_suffix:
        is_cdn, cdn_name = directory.lookup_cname(cname_chain(hostname))
        cdn_via = "cname" if is_cdn else None

    return Hosting(ip=ip, asn=asn, is_cdn=is_cdn, cdn_name=cdn_name, cdn_via=cdn_via)
