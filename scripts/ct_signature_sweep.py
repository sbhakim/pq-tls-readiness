"""Certificate Transparency corroboration sweep.

For every registered domain in a CISA CSV, query the crt.sh PostgreSQL
interface for the signature/key algorithms of *unexpired* certificates
covering the domain or its subdomains. This checks the authentication plane
at issuance (what CAs have issued) rather than presentation (what one scan
observed), corroborating the 0% post-quantum authentication result at
population scale.

Usage: python scripts/ct_signature_sweep.py <cisa_csv> <out_csv>
"""
from __future__ import annotations

import csv
import subprocess
import sys
import time

QUERY = """
SELECT x509_keyAlgorithm(cai.certificate) AS key_alg,
       x509_signatureHashAlgorithm(cai.certificate) AS sig_hash,
       count(*)
FROM certificate_and_identities cai
WHERE plainto_tsquery('certwatch', %(d)s) @@ identities(cai.certificate)
  AND (cai.name_value = %(d)s OR cai.name_value LIKE %(like)s)
  AND x509_notAfter(cai.certificate) > now()
GROUP BY 1, 2;
"""

def sweep(csv_in: str, csv_out: str) -> None:
    with open(csv_in, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        domains = sorted({(row.get("Domain name") or "").strip().lower()
                          for row in reader if row.get("Domain name")})
    print(f"{len(domains)} domains", flush=True)
    with open(csv_out, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["domain", "key_alg", "sig_hash", "count", "status"])
        for i, domain in enumerate(domains, 1):
            sql = QUERY.replace("%(d)s", f"'{domain}'").replace("%(like)s", f"'%.{domain}'")
            try:
                proc = subprocess.run(
                    ["psql", "postgresql://guest@crt.sh:5432/certwatch", "-tAc", sql],
                    capture_output=True, text=True, timeout=60)
                rows = [line.split("|") for line in proc.stdout.strip().splitlines() if line]
                if not rows:
                    writer.writerow([domain, "", "", 0, "no_unexpired_certs" if proc.returncode == 0 else "query_failed"])
                for parts in rows:
                    if len(parts) == 3:
                        writer.writerow([domain, parts[0], parts[1], parts[2], "ok"])
            except subprocess.TimeoutExpired:
                writer.writerow([domain, "", "", 0, "timeout"])
            out.flush()
            if i % 100 == 0:
                print(f"{i}/{len(domains)}", flush=True)
            time.sleep(0.4)  # politeness toward the shared guest DB

if __name__ == "__main__":
    sweep(sys.argv[1], sys.argv[2])
