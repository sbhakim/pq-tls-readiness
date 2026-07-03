"""Key-exchange classification picks the strongest group across profiles."""

from __future__ import annotations

from pqreadiness.classify.keyexchange import classify_key_exchange
from pqreadiness.models import KexClass, ProbeOutcome


def _probe(profile: str, group: str | None) -> ProbeOutcome:
    return ProbeOutcome(profile=profile, reachable=True, negotiated_group=group)


def test_hybrid_wins_over_classical(registry):
    # Classical profile got classical; hybrid profile got hybrid.
    probes = [
        _probe("classical", "X25519"),
        _probe("hybrid_capable", "X25519MLKEM768"),
    ]
    group, klass = classify_key_exchange(probes, registry)
    assert klass is KexClass.HYBRID_PQ
    assert group == "X25519MLKEM768"


def test_pure_pq_beats_hybrid(registry):
    probes = [
        _probe("classical", "X25519MLKEM768"),
        _probe("hybrid_capable", "MLKEM768"),
    ]
    _, klass = classify_key_exchange(probes, registry)
    assert klass is KexClass.PURE_PQ


def test_all_classical_stays_classical(registry):
    probes = [_probe("classical", "X25519"), _probe("hybrid_capable", "P-256")]
    _, klass = classify_key_exchange(probes, registry)
    assert klass is KexClass.CLASSICAL


def test_unknown_group_is_not_promoted(registry):
    # A group we don't recognize should not be classified as PQ.
    probes = [_probe("hybrid_capable", "SomeFutureGroup")]
    group, klass = classify_key_exchange(probes, registry)
    assert klass is KexClass.UNKNOWN
    assert group == "SomeFutureGroup"


def test_unreachable_probes_ignored(registry):
    probes = [ProbeOutcome(profile="classical", reachable=False, error="timeout")]
    _, klass = classify_key_exchange(probes, registry)
    assert klass is KexClass.UNKNOWN
