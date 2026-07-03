"""Certificate signature classification handles OpenSSL's naming variety."""

from __future__ import annotations

import pytest

from pqreadiness.classify.authentication import classify_authentication
from pqreadiness.models import AuthClass, CertInfo


@pytest.mark.parametrize(
    "sig_alg, expected",
    [
        ("sha256WithRSAEncryption", AuthClass.CLASSICAL),
        ("ecdsa-with-SHA256", AuthClass.CLASSICAL),
        ("ML-DSA-65", AuthClass.PQ),
        ("dilithium3", AuthClass.PQ),
        ("SLH-DSA-SHA2-128s", AuthClass.PQ),
        ("some-unknown-alg", AuthClass.UNKNOWN),
        (None, AuthClass.UNKNOWN),
    ],
)
def test_signature_classes(registry, sig_alg, expected):
    cert = CertInfo(signature_algorithm=sig_alg)
    assert classify_authentication(cert, registry) is expected
