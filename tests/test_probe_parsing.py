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
