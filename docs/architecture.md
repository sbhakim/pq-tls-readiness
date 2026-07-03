# Architecture

The pipeline is a straight line of small, single-purpose stages. Each stage has
one job and hands a slightly richer object to the next.

```
domains CSV
   │  ingest/dotgov.py      parse CISA CSV -> (domain, tier)
   │  ingest/targets.py     expand -> hostnames (apex, www)
   ▼
Target
   │  resolve/dns.py        hostname -> IP (skip if it fails)
   ▼
   │  probe/openssl.py      dual-probe handshakes (classical + hybrid)
   │  probe/certificate.py  actively fetch + parse the leaf cert
   ▼
raw probe outcomes + cert
   │  classify/keyexchange.py    best group -> KexClass
   │  classify/authentication.py cert sig  -> AuthClass
   │  enrich/hosting.py          ASN -> CDN / origin
   ▼
DomainReadiness  ──►  storage/writer.py  ──►  results.csv + results.jsonl
                                              │
                                              ▼
                              analysis/*  and  viz/*   (offline)
```

## Why it is shaped this way

- **Registries in YAML, not code.** `config/registry/*.yaml` decide what counts
  as classical vs PQ. New standards = edit YAML, not Python.
- **Dual-probe.** A single handshake only shows what was *negotiated*. Probing
  with a classical and a hybrid-capable profile tells us what the server
  *supports*. See `probe/profiles.py`.
- **Active certificate fetch.** TLS 1.3 encrypts the certificate, so we open a
  dedicated connection to read it (`probe/certificate.py`).
- **CDN tagging is first-class.** Many `.gov` sites sit behind CDNs that already
  do hybrid KEX; `enrich/hosting.py` keeps agency readiness separate from CDN
  readiness.
- **Streaming writes.** `storage/writer.py` appends every row immediately, so a
  crash mid-run still leaves usable data.

## Extending it

- New probe engine (e.g. a Go/rustls client): implement the same shape as
  `probe/openssl.py` and swap it in `pipeline/runner.py`.
- Real IP→ASN lookup: implement `enrich/hosting.py`'s ASN source (pyasn, a
  local MaxMind DB, or Team Cymru) and pass the ASN into `enrich_hosting`.
- New output sink (Parquet, a database): add a writer beside
  `storage/writer.py` that consumes `DomainReadiness`.
