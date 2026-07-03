# Output schema

Each probed endpoint is one row in `results.csv`. Column order is defined once
in `storage/schema.py`.

| Column | Type | Meaning |
|---|---|---|
| `domain` | str | Registered domain from the CISA list |
| `hostname` | str | Actual host probed (apex or `www.`) |
| `tier` | enum | `federal` / `state_local` / `other` |
| `reachable` | bool | Any probe completed a handshake |
| `tls_version` | str | Negotiated TLS version (e.g. `TLSv1.3`) |
| `negotiated_group` | str | Best key-exchange group seen across profiles |
| `kex_class` | enum | `classical` / `hybrid_pq` / `pure_pq` / `unknown` |
| `cert_signature_algorithm` | str | Leaf cert signature algorithm |
| `auth_class` | enum | `classical` / `pq` / `unknown` |
| `cert_key_type` | str | Public key algorithm of the leaf cert |
| `cert_key_bits` | int | Public key size in bits |
| `hosting_asn` | int | ASN serving the endpoint (if resolved) |
| `is_cdn` | bool | Endpoint served by a known CDN |
| `cdn_name` | str | CDN name if `is_cdn` |
| `notes` | str | Errors, skipped states, or `kex_pq_auth_classical` |

`results.jsonl` mirrors this but also keeps the raw per-profile `probes` list
for auditing (which profile negotiated what).

## The headline metric

The **authentication gap** = (share of reachable endpoints with `kex_class` in
{hybrid_pq, pure_pq}) − (share with `auth_class == pq`). The `notes` value
`kex_pq_auth_classical` flags exactly the endpoints that make up this gap.
