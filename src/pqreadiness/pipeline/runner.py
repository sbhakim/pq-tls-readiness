"""The end-to-end pipeline for one target.

For each target we: resolve DNS -> dual-probe -> fetch cert -> classify both
sides -> tag hosting -> return one DomainReadiness record. The orchestrator
runs `scan_target` across many targets concurrently.
"""

from __future__ import annotations

import time

from ..classify.authentication import classify_authentication
from ..classify.keyexchange import classify_key_exchange
from ..classify.registry import Registry
from ..config import Config
from ..enrich.asn import AsnResolver
from ..enrich.hosting import CdnDirectory, enrich_hosting
from ..models import AuthClass, DomainReadiness, KexClass, ProbeOutcome, Target
from ..probe.certificate import fetch_certificate
from ..probe.openssl import probe
from ..probe.profiles import Profile, get_profile
from ..resolve.dns import resolve
from ..utils.logging import get_logger

log = get_logger(__name__)

# Failure categories worth one more attempt: the endpoint may simply have been
# slow or the path congested. Handshake-level failures are deterministic and
# are not retried.
_TRANSIENT_CATEGORIES = {"tcp_timeout", "tcp_error"}


class Scanner:
    """Holds the shared, read-only context needed to scan any target."""

    def __init__(
        self,
        config: Config,
        registry: Registry,
        cdns: CdnDirectory,
        resolver: AsnResolver,
    ) -> None:
        self.config = config
        self.registry = registry
        self.cdns = cdns
        self.resolver = resolver

    def scan_target(self, target: Target) -> DomainReadiness:
        """Run all stages for one target and return its readiness record."""
        record = DomainReadiness(
            domain=target.domain,
            hostname=target.hostname,
            tier=target.tier,
            agency=target.agency,
        )

        # 1) DNS. Skip everything else if the host does not resolve.
        dns = resolve(target.hostname, timeout_s=self.config.dns_timeout_s)
        if not dns.resolved:
            record.notes = f"dns_failed: {dns.error}"
            return record

        # 2) Dual-probe: one handshake per client profile, with a retry on
        #    transient failures so a momentary timeout is not recorded as
        #    an unreachable endpoint.
        for profile_name in self.config.probe.profiles:
            profile = get_profile(profile_name)
            outcome = self._probe_with_retry(target.hostname, profile)
            record.probes.append(outcome)
            if self.config.per_host_delay_s:
                time.sleep(self.config.per_host_delay_s)

        record.reachable = any(p.reachable for p in record.probes)
        if not record.reachable:
            errs = {p.error for p in record.probes if p.error}
            record.notes = "unreachable: " + ",".join(sorted(errs))[:100]
            return record

        # Use the TLS version from the first reachable probe.
        record.tls_version = next(
            (p.tls_version for p in record.probes if p.tls_version), None
        )

        # 3) Classify key exchange from the best group across profiles.
        group, kex_class = classify_key_exchange(record.probes, self.registry)
        record.negotiated_group = group
        record.kex_class = kex_class

        # 4) Fetch + classify the certificate (authentication side).
        cert = fetch_certificate(
            target.hostname,
            openssl_bin=self.config.probe.openssl_bin,
            port=self.config.probe.port,
            timeout_s=self.config.probe.connect_timeout_s,
        )
        record.cert_signature_algorithm = cert.signature_algorithm
        record.cert_key_type = cert.public_key_type
        record.cert_key_bits = cert.public_key_bits
        record.cert_chain_length = cert.chain_length
        record.cert_chain_signature_algorithms = cert.chain_signature_algorithms
        record.auth_class = classify_authentication(cert, self.registry)

        # 5) Tag hosting (CDN vs origin). Combines the IP->ASN->CDN signal
        #    with a CNAME-suffix fallback; without an ASN database the CNAME
        #    signal still works.
        hosting = enrich_hosting(dns.ip, self.resolver, self.cdns, hostname=target.hostname)
        record.ip = dns.ip
        record.hosting_asn = hosting.asn
        record.is_cdn = hosting.is_cdn
        record.cdn_name = hosting.cdn_name
        record.cdn_via = hosting.cdn_via

        # Flag the interesting case: hybrid KEX but classical cert = the gap.
        if record.kex_class in (KexClass.HYBRID_PQ, KexClass.PURE_PQ) and (
            record.auth_class == AuthClass.CLASSICAL
        ):
            record.notes = "kex_pq_auth_classical"

        return record

    def _probe_with_retry(self, hostname: str, profile: Profile) -> ProbeOutcome:
        """Probe once, then retry transient failures up to config.probe.retries."""
        attempts = 1 + max(0, self.config.probe.retries)
        outcome = probe(
            hostname,
            profile,
            openssl_bin=self.config.probe.openssl_bin,
            port=self.config.probe.port,
            timeout_s=self.config.probe.connect_timeout_s,
        )
        for attempt in range(1, attempts):
            if outcome.reachable or outcome.error_category not in _TRANSIENT_CATEGORIES:
                break
            log.debug("retry %d for %s after %s", attempt, hostname, outcome.error_category)
            outcome = probe(
                hostname,
                profile,
                openssl_bin=self.config.probe.openssl_bin,
                port=self.config.probe.port,
                timeout_s=self.config.probe.connect_timeout_s,
            )
        return outcome

    def scan_target_safe(self, target: Target) -> DomainReadiness:
        """scan_target that never raises: one bad target must not kill a run.

        Any unexpected exception becomes an `internal_error` record, so the
        failure is visible in the output instead of aborting a long scan.
        """
        try:
            return self.scan_target(target)
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all boundary
            log.warning("scan failed for %s: %s", target.hostname, exc)
            record = DomainReadiness(
                domain=target.domain,
                hostname=target.hostname,
                tier=target.tier,
                agency=target.agency,
            )
            record.notes = f"internal_error: {type(exc).__name__}: {exc}"[:200]
            return record
