"""The openssl output parser extracts the version and negotiated group.

Samples mirror the real `openssl s_client -brief` output shapes: PQ/hybrid
groups appear on a "Negotiated TLS1.3 group" line, classical groups only in
the "Peer Temp Key" line.
"""

from __future__ import annotations

from pqreadiness.probe import openssl


def test_extracts_hybrid_group_and_protocol():
    sample = (
        "CONNECTION ESTABLISHED\n"
        "Protocol version: TLSv1.3\n"
        "Ciphersuite: TLS_AES_256_GCM_SHA384\n"
        "Negotiated TLS1.3 group: X25519MLKEM768\n"
    )
    assert openssl._extract_group(sample) == "X25519MLKEM768"
    assert openssl._extract(sample, openssl._PROTO_RE) == "TLSv1.3"


def test_extracts_classical_x25519_from_temp_key():
    sample = (
        "CONNECTION ESTABLISHED\n"
        "Protocol version: TLSv1.3\n"
        "Peer Temp Key: X25519, 253 bits\n"
    )
    assert openssl._extract_group(sample) == "X25519"


def test_extracts_classical_ecdh_curve():
    sample = "CONNECTION ESTABLISHED\nPeer Temp Key: ECDH, P-256, 256 bits\n"
    assert openssl._extract_group(sample) == "P-256"


def test_no_group_when_absent():
    sample = "some unrelated output\n"
    assert openssl._extract_group(sample) is None


def test_alert_protocol_version_error_is_not_reachable():
    """OpenSSL's 'tlsv1 alert protocol version:ssl/...' error text contains
    the words 'protocol version:' mid-line; it must not parse as a TLS
    version (regression for the alert-70 misclassification)."""
    from pqreadiness.probe.openssl import _PROTO_RE, _error_category

    err = ("409786B7DC720000:error:0A00042E:SSL routines:ssl3_read_bytes:"
           "tlsv1 alert protocol version:ssl/record/rec_layer_s3.c:918:"
           "SSL alert number 70")
    assert _PROTO_RE.search(err) is None
    assert _error_category(err, timed_out=False) == "no_tls13"


def test_real_brief_protocol_line_still_parses():
    from pqreadiness.probe.openssl import _PROTO_RE

    out = "CONNECTION ESTABLISHED\nProtocol version: TLSv1.3\nCiphersuite: TLS_AES_256_GCM_SHA384"
    match = _PROTO_RE.search(out)
    assert match and match.group(1) == "TLSv1.3"
