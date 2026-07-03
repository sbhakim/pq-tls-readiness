"""pqscan — a one-shot, correct PQC detector for a single host.

This is the small public artifact from the paper: unlike classical scanners
that mislabel or ignore PQ identifiers, it dual-probes a host and reports both
the key-exchange class and the certificate authentication class.

Usage:
    python -m pqreadiness.tools.pqscan example.gov
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from ..classify.authentication import classify_authentication
from ..classify.keyexchange import classify_key_exchange
from ..classify.registry import load_registry
from ..config import load_config
from ..probe.certificate import fetch_certificate
from ..probe.openssl import probe
from ..probe.profiles import CLASSICAL, HYBRID_CAPABLE

_GROUPS = "config/registry/named_groups.yaml"
_SIGS = "config/registry/signature_algorithms.yaml"


def scan_host(
    hostname: str,
    *,
    openssl_bin: str = "openssl",
    groups_path: str = _GROUPS,
    signatures_path: str = _SIGS,
    timeout_s: int = 10,
) -> dict[str, Any]:
    """Probe one host and return a small readiness dict."""
    registry = load_registry(groups_path, signatures_path)

    probes = [
        probe(hostname, prof, openssl_bin=openssl_bin, port=443, timeout_s=timeout_s)
        for prof in (CLASSICAL, HYBRID_CAPABLE)
    ]
    group, kex_class = classify_key_exchange(probes, registry)

    cert = fetch_certificate(hostname, openssl_bin=openssl_bin, port=443, timeout_s=timeout_s)
    auth_class = classify_authentication(cert, registry)

    return {
        "host": hostname,
        "negotiated_group": group or "-",
        "kex_class": kex_class.value,
        "cert_signature": cert.signature_algorithm or "-",
        "auth_class": auth_class.value,
        "cert_chain_length": cert.chain_length or 0,
        "cert_chain_signature_algorithms": cert.chain_signature_algorithms,
        "probes": [asdict(outcome) for outcome in probes],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="dual-probe one HTTPS host for PQ-TLS readiness")
    parser.add_argument("hostname")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--openssl-bin", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv if argv is not None else sys.argv[1:])
    config = load_config(args.config)
    result = scan_host(
        args.hostname,
        openssl_bin=args.openssl_bin or config.probe.openssl_bin,
        groups_path=str(config.named_groups),
        signatures_path=str(config.signature_algorithms),
        timeout_s=args.timeout or config.probe.connect_timeout_s,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    for key in (
        "host",
        "negotiated_group",
        "kex_class",
        "cert_signature",
        "auth_class",
        "cert_chain_length",
    ):
        print(f"{key:28s}: {result[key]}")
    for probe_result in result["probes"]:
        status = "ok" if probe_result["reachable"] else probe_result["error_category"]
        print(
            f"probe[{probe_result['profile']}]: {status}; "
            f"group={probe_result['negotiated_group'] or '-'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
