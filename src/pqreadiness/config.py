"""Load and validate run configuration.

Config comes from a YAML file, with optional environment-variable overrides
for machine-specific bits (which OpenSSL binary, how many workers).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ProbeConfig:
    openssl_bin: str
    port: int
    connect_timeout_s: int
    profiles: list[str]
    # Extra attempts for transient failures (timeouts, TCP errors) before an
    # endpoint is recorded unreachable. 0 disables retries.
    retries: int = 1


@dataclass
class Config:
    domains_csv: Path
    hostname_variants: list[str]
    probe: ProbeConfig
    dns_timeout_s: int
    cdn_asns: Path
    asn_db: Path | None
    max_workers: int
    per_host_delay_s: float
    results_csv: Path
    results_jsonl: Path
    figures_dir: Path
    named_groups: Path
    signature_algorithms: Path
    log_level: str


def load_config(path: str | Path) -> Config:
    """Read a YAML config file into a typed Config object."""
    raw = yaml.safe_load(Path(path).read_text())

    # Environment overrides win over the file for these fields.
    openssl_bin = os.getenv("PQR_OPENSSL_BIN", raw["probe"]["openssl_bin"])
    max_workers = int(os.getenv("PQR_MAX_WORKERS", raw["concurrency"]["max_workers"]))

    probe = ProbeConfig(
        openssl_bin=openssl_bin,
        port=int(raw["probe"]["port"]),
        connect_timeout_s=int(raw["probe"]["connect_timeout_s"]),
        profiles=list(raw["probe"]["profiles"]),
        retries=int(raw["probe"].get("retries", 1)),
    )

    return Config(
        domains_csv=Path(raw["input"]["domains_csv"]),
        hostname_variants=list(raw["input"]["hostname_variants"]),
        probe=probe,
        dns_timeout_s=int(raw["resolve"]["dns_timeout_s"]),
        cdn_asns=Path(raw["enrich"]["cdn_asns"]),
        # asn_db is optional: without it, CDN attribution is simply skipped.
        asn_db=(Path(raw["enrich"]["asn_db"]) if raw["enrich"].get("asn_db") else None),
        max_workers=max_workers,
        per_host_delay_s=float(raw["concurrency"]["per_host_delay_s"]),
        results_csv=Path(raw["output"]["results_csv"]),
        results_jsonl=Path(raw["output"]["results_jsonl"]),
        figures_dir=Path(raw["output"]["figures_dir"]),
        named_groups=Path(raw["registry"]["named_groups"]),
        signature_algorithms=Path(raw["registry"]["signature_algorithms"]),
        log_level=str(raw["logging"]["level"]),
    )
