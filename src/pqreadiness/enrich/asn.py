"""Resolve an IP address to its Autonomous System Number (ASN).

Hosting enrichment uses the ASN to decide whether an endpoint is served by a
CDN. Resolution is behind a small interface with two implementations:

- PyasnResolver: offline lookups against a prebuilt pyasn database. Fast,
  reproducible, and no per-query network calls.
- NullResolver: always returns None. Used when no ASN database is configured,
  so the pipeline still runs -- just without CDN attribution.

pyasn is imported lazily so the rest of the tool works even if it is absent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..utils.logging import get_logger

log = get_logger(__name__)


class AsnResolver(Protocol):
    """Anything that can turn an IP string into an ASN (or None)."""

    def lookup(self, ip: str | None) -> int | None: ...


class NullResolver:
    """Used when no ASN database is available; every lookup returns None."""

    def lookup(self, ip: str | None) -> int | None:
        return None


class PyasnResolver:
    """Offline IP -> ASN lookups against a prebuilt pyasn database file."""

    def __init__(self, db_path: str | Path) -> None:
        import pyasn  # lazy import keeps pyasn optional

        self._db = pyasn.pyasn(str(db_path))

    def lookup(self, ip: str | None) -> int | None:
        if not ip:
            return None
        try:
            asn, _prefix = self._db.lookup(ip)
            return asn
        except Exception:  # noqa: BLE001 - never let a lookup crash a scan
            return None


def build_resolver(db_path: str | Path | None) -> AsnResolver:
    """Return a PyasnResolver if the database exists and loads, else NullResolver.

    Falling back to NullResolver (with a warning) means a missing or broken ASN
    database degrades gracefully to "no CDN attribution" instead of failing.
    """
    if not db_path:
        log.info("no ASN database configured; CDN attribution disabled")
        return NullResolver()

    path = Path(db_path)
    if not path.exists():
        log.warning("ASN database not found at %s; CDN attribution disabled", path)
        return NullResolver()

    try:
        resolver = PyasnResolver(path)
        log.info("loaded ASN database from %s", path)
        return resolver
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load ASN database (%s); CDN attribution disabled", exc)
        return NullResolver()
