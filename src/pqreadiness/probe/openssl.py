"""Run one TLS 1.3 handshake with `openssl s_client` and read back what was
negotiated.

We do not trust exit codes alone — we parse the handshake text for the TLS
version and the negotiated group. OpenSSL must be PQC-capable, e.g. OpenSSL
3.5+ with native ML-KEM support or an older build with oqs-provider.
"""

from __future__ import annotations

import re

from ..models import ProbeOutcome
from ..utils.shell import run
from .profiles import Profile

# `openssl s_client -brief` reports the negotiated group two different ways:
#  - PQ/hybrid groups:  "Negotiated TLS1.3 group: X25519MLKEM768"
#  - classical groups:  "Peer Temp Key: X25519, 253 bits"
#                   or  "Peer Temp Key: ECDH, P-256, 256 bits"
_GROUP_RE = re.compile(r"Negotiated TLS1\.3 group:\s*(\S+)", re.IGNORECASE)
_TEMPKEY_RE = re.compile(r"Peer Temp Key:\s*(.+)", re.IGNORECASE)
_PROTO_RE = re.compile(r"Protocol version:\s*(\S+)", re.IGNORECASE)
# openssl prints this once the handshake completes, regardless of group type.
_ESTABLISHED = "CONNECTION ESTABLISHED"


def _extract(text: str, pattern: re.Pattern[str]) -> str | None:
    """Return the first capture group of `pattern` in `text`, or None."""
    match = pattern.search(text)
    return match.group(1) if match else None


def _extract_line(text: str, pattern: re.Pattern[str]) -> str | None:
    """Return the complete line matched by `pattern`, or None."""
    for line in text.splitlines():
        if pattern.search(line):
            return line.strip()
    return None


# Informational s_client lines that are useless as a failure reason.
_NOISE_PREFIXES = (
    "connecting to",
    "depth=",
    "verify return",
    "verify error",
    "doneconnect",
    "connection established",
)


def _failure_reason(stderr: str, category: str) -> str:
    """Pick the first stderr line that actually explains the failure.

    OpenSSL prints informational lines ("Connecting to 1.2.3.4", "depth=2 ...")
    before any error; taking the last line blindly often records those instead
    of the real reason. Fall back to the error category if nothing useful
    remains.
    """
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.lower().startswith(p) for p in _NOISE_PREFIXES):
            continue
        return stripped[:120]
    return category


def _error_category(text: str, timed_out: bool) -> str:
    """Map noisy OpenSSL failures to stable categories for analysis."""
    if timed_out:
        return "tcp_timeout"
    lower = text.lower()
    if "temporary failure in name resolution" in lower or "name or service not known" in lower:
        return "dns_failed"
    if "no suitable key share" in lower or "bad key share" in lower:
        return "unsupported_group"
    if "alert" in lower:
        return "tls_alert"
    if "wrong version number" in lower or "unsupported protocol" in lower:
        return "no_tls13"
    if "connect:errno" in lower or "bio_lookup_ex" in lower:
        return "tcp_error"
    return "handshake_failed"


def _extract_group(text: str) -> str | None:
    """Pull the negotiated group name, handling both output shapes."""
    # Prefer the explicit PQ/hybrid line when present.
    explicit = _extract(text, _GROUP_RE)
    if explicit:
        return explicit

    # Fall back to the classical "Peer Temp Key" line.
    match = _TEMPKEY_RE.search(text)
    if not match:
        return None
    tokens = [t.strip() for t in match.group(1).split(",")]
    if not tokens:
        return None
    # "ECDH, P-256, 256 bits" -> the curve is the second token.
    if tokens[0].upper() in {"ECDH", "DH"} and len(tokens) > 1:
        return tokens[1]
    # "X25519, 253 bits" -> the curve is the first token.
    return tokens[0]


def probe(
    hostname: str,
    profile: Profile,
    *,
    openssl_bin: str,
    port: int,
    timeout_s: int,
) -> ProbeOutcome:
    """Open one handshake with the given profile and report the result."""
    argv = [
        openssl_bin,
        "s_client",
        "-connect", f"{hostname}:{port}",
        "-servername", hostname,     # SNI
        "-groups", ":".join(profile.groups),
        "-tls1_3",
        "-brief",
    ]
    # Sending "Q\n" tells s_client to close the connection right after the
    # handshake instead of waiting for input.
    result = run(argv, timeout_s=timeout_s, stdin="Q\n")

    if result.timed_out:
        return ProbeOutcome(
            profile=profile.name,
            reachable=False,
            error="timeout",
            error_category="tcp_timeout",
            return_code=result.return_code,
        )

    combined = result.stdout + result.stderr
    group = _extract_group(combined)
    proto = _extract(combined, _PROTO_RE)
    raw_group_line = _extract_line(combined, _GROUP_RE) or _extract_line(combined, _TEMPKEY_RE)
    raw_protocol_line = _extract_line(combined, _PROTO_RE)

    # Reachable if the handshake completed (established, or we saw a
    # protocol / group line).
    reachable = (_ESTABLISHED in combined) or bool(proto) or bool(group)
    if not reachable:
        category = _error_category(combined, result.timed_out)
        return ProbeOutcome(
            profile=profile.name,
            reachable=False,
            error=_failure_reason(result.stderr, category),
            error_category=category,
            return_code=result.return_code,
            raw_protocol_line=raw_protocol_line,
            raw_group_line=raw_group_line,
        )

    return ProbeOutcome(
        profile=profile.name,
        reachable=True,
        tls_version=proto,
        negotiated_group=group,
        return_code=result.return_code,
        raw_protocol_line=raw_protocol_line,
        raw_group_line=raw_group_line,
    )
