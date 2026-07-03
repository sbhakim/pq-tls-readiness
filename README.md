# pqreadiness

**Measuring post-quantum TLS readiness of enumerable endpoint populations.**

`pqreadiness` is a terminal-only measurement pipeline that quantifies, for every
HTTPS endpoint in a population, the two independent halves of the post-quantum
TLS migration:

1. **Key exchange** — does the server *support* a hybrid/post-quantum group
   (e.g., `X25519MLKEM768`), independent of what a given client happens to
   negotiate?
2. **Authentication** — is the presented certificate signed with a post-quantum
   algorithm (ML-DSA / SLH-DSA) or a classical one (RSA / ECDSA)?

The gap between the two is the headline metric. This repository is the
measurement instrument behind the paper *"From Mandate to Migration: An
Empirical Study of Post-Quantum TLS Readiness in U.S. Government Web
Infrastructure"* and reproduces every number, table, and figure it reports.

## At a glance

![Study overview: the post-quantum key-exchange versus authentication gap in
U.S. federal TLS, the measurement pipeline, hosting attribution, and the
federal deadline timeline](docs/assets/overview.png)

## Method

- **Dual-probe capability measurement.** Each endpoint is probed under a
  classical client profile and a hybrid-capable profile; the strongest group
  across probes is a *capability lower bound*. This separates support from
  negotiation — a single classical probe reports 0% where true support is >20%.
- **Active certificate retrieval.** TLS 1.3 encrypts the certificate in the
  handshake, so the chain is fetched on a dedicated connection and classified
  from the leaf (full-chain algorithms retained for audit).
- **Two-signal hosting attribution.** Endpoints are attributed to their serving
  operator via an offline IP→ASN snapshot *and* a CNAME-chain match against
  known platform suffixes, with provenance (`cdn_via`) recorded per row.
  Resolution prefers IPv4: IPv6-first lookups against an IPv4-only ASN database
  silently erase attribution and can invert conclusions.
- **Registry-driven classification.** Group and signature identifiers map to
  readiness classes through YAML registries (`config/registry/`), so a newly
  standardized identifier is a data change, not a code change.
- **Statistics built in.** Wilson score intervals for all proportions,
  endpoint- and domain-level rates, and McNemar's test (exact binomial for
  small discordant counts) for the dual-probe comparison.
- **Run resilience.** Transient failures are retried, per-target crashes become
  explicit `internal_error` records, results stream to disk per endpoint, and
  interrupted runs continue with `--resume`.

## Requirements

- Python ≥ 3.11
- A PQC-capable OpenSSL: **≥ 3.5** (native ML-KEM / ML-DSA / SLH-DSA; the study
  used 3.6.3). Older 3.x builds work with the
  [OQS provider](https://github.com/open-quantum-safe/oqs-provider).
- `dig` (CNAME-chain attribution; degrades gracefully if absent)
- Optional: a [pyasn](https://github.com/hadiasghari/pyasn) routing snapshot
  for ASN attribution (`scripts/download_asn_db.sh`)

## Quick start

```bash
make install-dev                       # editable install + dev tools
scripts/download_dotgov.sh             # CISA .gov population lists
scripts/download_asn_db.sh             # IP->ASN snapshot (optional)

# Point the pipeline at a PQC-capable OpenSSL if it is not on PATH:
export PQR_OPENSSL_BIN=/path/to/openssl-3.6

pqreadiness run --config config/default.yaml --limit 150    # pilot
pqreadiness run --config config/default.yaml --resume       # continue a run
pqreadiness analyze data/processed/results.csv              # summary tables
pqreadiness plot    data/processed/results.csv              # figures

python -m pqreadiness.tools.pqscan example.gov              # single endpoint
```

`make test`, `make lint`, and `make typecheck` run the quality gates
(pytest / ruff / mypy).

## Repository layout

```
src/pqreadiness/
  ingest/     CISA registry parsing, tiering, endpoint expansion
  resolve/    DNS resolution (IPv4-preferred)
  probe/      dual-probe handshakes + active certificate fetch (OpenSSL)
  classify/   registry-driven key-exchange / authentication classes
  enrich/     hosting attribution (ASN + CNAME signals)
  pipeline/   per-target orchestration, retries, crash isolation, concurrency
  storage/    output schema, streaming CSV/JSONL writers, resume support
  analysis/   aggregation (endpoint/domain/tier/hosting), Wilson, McNemar
  viz/        headless figures
  tools/      pqscan — standalone single-host detector
config/       run configuration + classification registries (YAML)
scripts/      input downloads, pilot runner
tests/        unit tests for classification, statistics, parsing, attribution
docs/         architecture and output-schema reference
```

Measurement inputs and results are deliberately untracked: inputs are
re-downloadable via `scripts/`, and per-run results are archived as a separate
evidence artifact. The output schema is documented in `docs/data-schema.md`.

## Ethics

The pipeline is non-intrusive by construction: it observes only what an
ordinary TLS client sees — negotiated handshake parameters and the publicly
served certificate. No authentication attempts, no payloads, no vulnerability
probing. Concurrency is bounded and per-host delays are configurable. Targets
are public web services enumerated by an authoritative public registry.

## Citation

If you use this instrument, please cite the accompanying paper:

```bibtex
@article{pqreadiness2026,
  title  = {From Mandate to Migration: An Empirical Study of Post-Quantum
            TLS Readiness in U.S. Government Web Infrastructure},
  author = {Bin Hakim, Safayat and Song, Houbing Herbert},
  year   = {2026},
  note   = {Under submission}
}
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
