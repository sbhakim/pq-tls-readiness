#!/usr/bin/env bash
# Download the authoritative CISA .gov domain lists into data/raw/.
# Federal-only is the primary population; full adds state/local for comparison.
set -euo pipefail

RAW_DIR="$(dirname "$0")/../data/raw"
mkdir -p "$RAW_DIR"

BASE="https://raw.githubusercontent.com/cisagov/dotgov-data/main"

echo "Downloading current-federal.csv ..."
curl -fsSL "$BASE/current-federal.csv" -o "$RAW_DIR/current-federal.csv"

echo "Downloading current-full.csv ..."
curl -fsSL "$BASE/current-full.csv" -o "$RAW_DIR/current-full.csv"

echo "Done:"
wc -l "$RAW_DIR"/current-federal.csv "$RAW_DIR"/current-full.csv
