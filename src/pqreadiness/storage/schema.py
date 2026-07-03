"""The output schema: the exact columns of a results row.

Kept in one place so the CSV header, the JSONL keys, and the analysis code
never drift apart.
"""

from __future__ import annotations

import json

from ..models import DomainReadiness

# Ordered column names for the CSV output.
COLUMNS: list[str] = [
    "domain",
    "hostname",
    "tier",
    "agency",
    "reachable",
    "tls_version",
    "negotiated_group",
    "kex_class",
    "cert_signature_algorithm",
    "auth_class",
    "cert_key_type",
    "cert_key_bits",
    "cert_chain_length",
    "cert_chain_signature_algorithms",
    "ip",
    "hosting_asn",
    "is_cdn",
    "cdn_name",
    "cdn_via",
    "notes",
]


def to_row(record: DomainReadiness) -> dict[str, object]:
    """Flatten a DomainReadiness into a plain dict keyed by COLUMNS."""
    return {
        "domain": record.domain,
        "hostname": record.hostname,
        "tier": record.tier.value,
        "agency": record.agency,
        "reachable": record.reachable,
        "tls_version": record.tls_version or "",
        "negotiated_group": record.negotiated_group or "",
        "kex_class": record.kex_class.value,
        "cert_signature_algorithm": record.cert_signature_algorithm or "",
        "auth_class": record.auth_class.value,
        "cert_key_type": record.cert_key_type or "",
        "cert_key_bits": record.cert_key_bits or "",
        "cert_chain_length": record.cert_chain_length or "",
        "cert_chain_signature_algorithms": json.dumps(record.cert_chain_signature_algorithms),
        "ip": record.ip or "",
        "hosting_asn": record.hosting_asn or "",
        "is_cdn": record.is_cdn,
        "cdn_name": record.cdn_name or "",
        "cdn_via": record.cdn_via or "",
        "notes": record.notes,
    }
