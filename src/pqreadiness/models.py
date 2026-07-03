"""Data structures passed between pipeline stages.

Each stage takes the previous object and adds to it, ending in a flat
`DomainReadiness` record that maps 1:1 to an output CSV row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class KexClass(str, Enum):
    """Readiness class for a negotiated key-exchange group."""

    CLASSICAL = "classical"
    HYBRID_PQ = "hybrid_pq"
    PURE_PQ = "pure_pq"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class AuthClass(str, Enum):
    """Readiness class for a certificate signature algorithm."""

    CLASSICAL = "classical"
    PQ = "pq"
    UNKNOWN = "unknown"


class Tier(str, Enum):
    """Which slice of government a domain belongs to."""

    FEDERAL = "federal"
    STATE_LOCAL = "state_local"
    OTHER = "other"


@dataclass
class Target:
    """A single hostname to probe, derived from a domain."""

    domain: str
    hostname: str
    tier: Tier
    agency: str = ""
    source: str = "dotgov"


@dataclass
class DnsResult:
    """Outcome of resolving a hostname."""

    hostname: str
    resolved: bool
    ip: str | None = None
    error: str | None = None


@dataclass
class ProbeOutcome:
    """Result of one client-profile probe against an endpoint."""

    profile: str
    reachable: bool
    tls_version: str | None = None
    negotiated_group: str | None = None
    error: str | None = None
    error_category: str | None = None
    return_code: int | None = None
    raw_protocol_line: str | None = None
    raw_group_line: str | None = None


@dataclass
class CertInfo:
    """Parsed fields from the server certificate chain.

    Leaf fields stay first because they drive the current authentication
    classifier. Chain fields are retained for audit and future chain-level
    analysis.
    """

    signature_algorithm: str | None = None
    public_key_type: str | None = None
    public_key_bits: int | None = None
    chain_length: int | None = None
    chain_signature_algorithms: list[str] = field(default_factory=list)


@dataclass
class Hosting:
    """Where the endpoint is served from."""

    ip: str | None = None
    asn: int | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    # How the CDN was identified: "asn", "cname", or None if not a CDN.
    cdn_via: str | None = None


@dataclass
class DomainReadiness:
    """The final, flat record for one probed endpoint (one CSV row)."""

    domain: str
    hostname: str
    tier: Tier
    # Owning agency ("Organization name" in the CISA registry); the mandate
    # binds agencies, so results aggregate at this level too.
    agency: str = ""

    reachable: bool = False
    tls_version: str | None = None

    # Capability = best group seen across all probe profiles.
    negotiated_group: str | None = None
    kex_class: KexClass = KexClass.UNKNOWN

    cert_signature_algorithm: str | None = None
    auth_class: AuthClass = AuthClass.UNKNOWN
    cert_key_type: str | None = None
    cert_key_bits: int | None = None
    cert_chain_length: int | None = None
    cert_chain_signature_algorithms: list[str] = field(default_factory=list)

    ip: str | None = None
    hosting_asn: int | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    cdn_via: str | None = None

    # Free-text notes: errors, contradictions, skipped states.
    notes: str = ""

    # Raw per-profile outcomes, kept for the JSONL export / auditing.
    probes: list[ProbeOutcome] = field(default_factory=list)
