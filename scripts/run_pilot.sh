#!/usr/bin/env bash
# Run a small pilot end-to-end: scan 150 federal domains, summarize, plot.
# Answers the two pilot questions: how much is CDN-masked, and is there any
# authentication-side signal at all.
set -euo pipefail

CONFIG="${1:-config/default.yaml}"

pqreadiness run --config "$CONFIG" --limit 150
pqreadiness analyze data/processed/results.csv
pqreadiness plot    data/processed/results.csv --out data/processed/figures

echo "Pilot complete. See data/processed/ for results and figures."
