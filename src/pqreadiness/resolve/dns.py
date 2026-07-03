"""Resolve a hostname to an IP before we bother opening a TLS connection.

Skipping unresolvable hostnames up front saves a lot of wasted probe time.
Uses the standard library resolver; no external DNS library required.
"""

from __future__ import annotations

import socket

from ..models import DnsResult


def resolve(hostname: str, timeout_s: int = 5) -> DnsResult:
    """Look up an address for a hostname, preferring IPv4.

    The offline ASN database used for CDN attribution is IPv4-only, so a
    dual-stack endpoint that resolves IPv6-first would silently lose its ASN
    (and could be mislabeled "origin"). We therefore pick an A record when one
    exists and fall back to AAAA only for IPv6-only hosts.

    Returns a DnsResult with resolved=False (and a reason) on failure, rather
    than raising, so the caller can record it and move on.
    """
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_s)
    try:
        info = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
        ipv4 = next((str(i[4][0]) for i in info if i[0] == socket.AF_INET), None)
        ip = ipv4 or (str(info[0][4][0]) if info else None)
        if ip:
            return DnsResult(hostname=hostname, resolved=True, ip=ip)
        return DnsResult(hostname=hostname, resolved=False, error="no address")
    except socket.gaierror as exc:
        return DnsResult(hostname=hostname, resolved=False, error=f"dns: {exc}")
    except OSError as exc:
        return DnsResult(hostname=hostname, resolved=False, error=str(exc))
    finally:
        socket.setdefaulttimeout(previous_timeout)
