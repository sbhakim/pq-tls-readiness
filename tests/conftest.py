"""Shared test fixtures."""

from __future__ import annotations

import pytest

from pqreadiness.classify.registry import (
    GroupEntry,
    Registry,
    SignatureEntry,
)


@pytest.fixture
def registry() -> Registry:
    """A small in-memory registry so tests don't depend on the YAML files."""
    groups = [
        GroupEntry("x25519", ["X25519"], "classical"),
        GroupEntry("secp256r1", ["P-256", "prime256v1"], "classical"),
        GroupEntry("x25519mlkem768", ["X25519MLKEM768"], "hybrid_pq"),
        GroupEntry("mlkem768", ["MLKEM768"], "pure_pq"),
    ]
    signatures = [
        SignatureEntry("rsa", ["rsaencryption", "sha256withrsa"], "classical"),
        SignatureEntry("ecdsa", ["ecdsa-with-sha256"], "classical"),
        SignatureEntry("ml-dsa", ["ml-dsa", "dilithium"], "pq"),
        SignatureEntry("slh-dsa", ["slh-dsa", "sphincs"], "pq"),
    ]
    return Registry(groups=groups, signatures=signatures)
