"""Classify the authentication side of an endpoint from its certificate."""

from __future__ import annotations

from ..models import AuthClass, CertInfo
from .registry import Registry


def classify_authentication(cert: CertInfo, registry: Registry) -> AuthClass:
    """Map a certificate's signature algorithm to a readiness class."""
    raw_class = registry.signature_class(cert.signature_algorithm)
    if raw_class is None:
        return AuthClass.UNKNOWN
    return AuthClass(raw_class)
