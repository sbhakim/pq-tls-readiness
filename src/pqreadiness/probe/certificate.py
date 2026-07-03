"""Fetch and parse the server certificate chain.

In TLS 1.3 the certificate is encrypted in the handshake, so we cannot read it
from a passive capture. We fetch it actively: open a connection, ask openssl
to print the peer certificates, then parse each PEM with `openssl x509`.
"""

from __future__ import annotations

import re

from ..models import CertInfo
from ..utils.shell import run

# Lines from `openssl x509 -text`:
_SIG_RE = re.compile(r"Signature Algorithm:\s*(\S+)", re.IGNORECASE)
_KEY_RE = re.compile(r"Public Key Algorithm:\s*(\S+)", re.IGNORECASE)
_BITS_RE = re.compile(r"Public-Key:\s*\((\d+)\s*bit\)", re.IGNORECASE)

# openssl wraps the PEM cert between these markers in s_client output.
_PEM_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
    re.DOTALL,
)


def _fetch_pems(hostname: str, *, openssl_bin: str, port: int, timeout_s: int) -> list[str]:
    """Grab all PEM certificates printed by the endpoint."""
    argv = [
        openssl_bin,
        "s_client",
        "-connect", f"{hostname}:{port}",
        "-servername", hostname,
        "-showcerts",
    ]
    result = run(argv, timeout_s=timeout_s, stdin="Q\n")
    return [match.group(0) for match in _PEM_RE.finditer(result.stdout)]


def _parse_pem(pem: str, *, openssl_bin: str, timeout_s: int) -> CertInfo:
    """Run `openssl x509 -text` on a PEM cert and pull out the fields we need."""
    argv = [openssl_bin, "x509", "-noout", "-text"]
    result = run(argv, timeout_s=timeout_s, stdin=pem)
    text = result.stdout

    sig = _SIG_RE.search(text)
    key = _KEY_RE.search(text)
    bits = _BITS_RE.search(text)
    return CertInfo(
        signature_algorithm=sig.group(1) if sig else None,
        public_key_type=key.group(1) if key else None,
        public_key_bits=int(bits.group(1)) if bits else None,
    )


def fetch_certificate(
    hostname: str,
    *,
    openssl_bin: str,
    port: int,
    timeout_s: int,
) -> CertInfo:
    """Fetch + parse the certificate chain; empty CertInfo if unavailable."""
    pems = _fetch_pems(hostname, openssl_bin=openssl_bin, port=port, timeout_s=timeout_s)
    if not pems:
        return CertInfo()

    parsed = [_parse_pem(pem, openssl_bin=openssl_bin, timeout_s=timeout_s) for pem in pems]
    leaf = parsed[0]
    leaf.chain_length = len(parsed)
    leaf.chain_signature_algorithms = [
        cert.signature_algorithm for cert in parsed if cert.signature_algorithm
    ]
    return leaf
