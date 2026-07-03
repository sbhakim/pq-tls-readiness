#!/usr/bin/env bash
# Build the pyasn IP->ASN database (data/raw/ipasn.dat).
#
# pyasn ships two helpers (installed with the package into the active env):
#   pyasn_util_download.py  -- fetch a recent RIB snapshot from RouteViews
#   pyasn_util_convert.py   -- convert that RIB into pyasn's fast .dat format
#
# Run inside the `quantum` conda env:  conda activate quantum && scripts/download_asn_db.sh
set -euo pipefail

RAW_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$RAW_DIR"
cd "$RAW_DIR"

echo "Downloading latest RIB snapshot ..."
pyasn_util_download.py --latest

# The download writes a file like rib.YYYYMMDD.HHHH.bz2; grab the newest.
RIB="$(ls -t rib.*.bz2 | head -1)"
echo "Converting $RIB -> ipasn.dat ..."
pyasn_util_convert.py --single "$RIB" ipasn.dat

echo "Done: $RAW_DIR/ipasn.dat"
ls -la "$RAW_DIR/ipasn.dat"
