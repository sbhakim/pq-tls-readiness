"""Hosting enrichment: IP -> ASN -> CDN, with a fake resolver."""

from __future__ import annotations

from pqreadiness.enrich.asn import NullResolver
from pqreadiness.enrich.hosting import CdnDirectory, enrich_hosting


class FakeResolver:
    """Maps a couple of IPs to ASNs for testing, no database needed."""

    def __init__(self, mapping: dict[str, int]) -> None:
        self._mapping = mapping

    def lookup(self, ip: str | None) -> int | None:
        return self._mapping.get(ip) if ip else None


def _directory() -> CdnDirectory:
    # 13335 = Cloudflare (a CDN); 7922 = a non-CDN ISP.
    return CdnDirectory(by_asn={13335: "Cloudflare"})


def test_cdn_ip_is_tagged():
    resolver = FakeResolver({"1.1.1.1": 13335})
    hosting = enrich_hosting("1.1.1.1", resolver, _directory())
    assert hosting.asn == 13335
    assert hosting.is_cdn is True
    assert hosting.cdn_name == "Cloudflare"


def test_non_cdn_ip_is_origin():
    resolver = FakeResolver({"8.8.8.8": 7922})
    hosting = enrich_hosting("8.8.8.8", resolver, _directory())
    assert hosting.asn == 7922
    assert hosting.is_cdn is False
    assert hosting.cdn_name is None


def test_null_resolver_disables_attribution():
    hosting = enrich_hosting("1.1.1.1", NullResolver(), _directory())
    assert hosting.asn is None
    assert hosting.is_cdn is False


def test_missing_ip_is_safe():
    hosting = enrich_hosting(None, NullResolver(), _directory())
    assert hosting.asn is None
    assert hosting.is_cdn is False


def _directory_with_cnames() -> CdnDirectory:
    return CdnDirectory(
        by_asn={13335: "Cloudflare"},
        by_cname_suffix=[
            ("cloudfront.net", "AWS CloudFront"),
            ("edgekey.net", "Akamai"),
        ],
    )


def test_cname_suffix_match():
    directory = _directory_with_cnames()
    is_cdn, name = directory.lookup_cname(["d1234.cloudfront.net."])
    assert is_cdn is True and name == "AWS CloudFront"


def test_cname_suffix_no_false_positive_on_substring():
    # "evilcloudfront.net" must not match the "cloudfront.net" suffix.
    directory = _directory_with_cnames()
    is_cdn, _ = directory.lookup_cname(["evilcloudfront.net."])
    assert is_cdn is False


def test_cname_chain_order_first_match_wins():
    directory = _directory_with_cnames()
    is_cdn, name = directory.lookup_cname(
        ["www.example.gov.edgekey.net.", "e1234.cloudfront.net."]
    )
    assert is_cdn is True and name == "Akamai"


def test_asn_signal_takes_priority(monkeypatch):
    # When the ASN already identifies a CDN, no CNAME lookup should be needed.
    import pqreadiness.enrich.hosting as hosting_mod

    def _boom(hostname, **kwargs):
        raise AssertionError("cname_chain should not be called")

    monkeypatch.setattr(hosting_mod, "cname_chain", _boom)
    resolver = FakeResolver({"1.1.1.1": 13335})
    hosting = enrich_hosting("1.1.1.1", resolver, _directory_with_cnames(), hostname="x.gov")
    assert hosting.is_cdn is True and hosting.cdn_via == "asn"


def test_cname_fallback_when_asn_unknown(monkeypatch):
    import pqreadiness.enrich.hosting as hosting_mod

    monkeypatch.setattr(
        hosting_mod, "cname_chain", lambda hostname, **kw: ["d1.cloudfront.net."]
    )
    hosting = enrich_hosting("2600::1", NullResolver(), _directory_with_cnames(), hostname="x.gov")
    assert hosting.is_cdn is True
    assert hosting.cdn_name == "AWS CloudFront"
    assert hosting.cdn_via == "cname"
