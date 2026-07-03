"""Command-line entry point.

Subcommands:
    run       scan a domain population and write results
    analyze   print summary tables from a results CSV
    plot      write figures from a results CSV

Kept thin on purpose: it wires config to the library and calls into the
pipeline/analysis modules. All real logic lives in those modules.
"""

from __future__ import annotations

import argparse
import sys

from .analysis.aggregate import load_results
from .analysis.report import summarize
from .classify.registry import load_registry
from .config import load_config
from .enrich.asn import build_resolver
from .enrich.hosting import CdnDirectory
from .ingest.dotgov import load_domains
from .ingest.plainlist import load_plain_domains
from .ingest.targets import build_targets
from .pipeline.concurrency import map_concurrent
from .pipeline.runner import Scanner
from .storage.writer import ResultWriter, completed_hostnames
from .utils.logging import get_logger, setup_logging
from .viz.plots import generate_all

log = get_logger("pqreadiness.cli")


def _cmd_run(args: argparse.Namespace) -> int:
    """Scan a population end-to-end and stream results to disk."""
    config = load_config(args.config)
    setup_logging(config.log_level)

    registry = load_registry(config.named_groups, config.signature_algorithms)
    cdns = CdnDirectory.from_yaml(config.cdn_asns)
    resolver = build_resolver(config.asn_db)
    scanner = Scanner(config, registry, cdns, resolver)

    # Build the target list, optionally capped for a pilot run.
    if config.domains_format == "plainlist":
        domains = load_plain_domains(config.domains_csv)
    else:
        domains = load_domains(config.domains_csv)
    targets = build_targets(domains, config.hostname_variants)
    if args.limit:
        targets = targets[: args.limit]

    # --resume: skip targets already in the results CSV and append to it.
    if args.resume:
        done_hosts = completed_hostnames(config.results_csv)
        before = len(targets)
        targets = [t for t in targets if t.hostname not in done_hosts]
        log.info("resume: skipping %d already-scanned targets", before - len(targets))

    log.info("scanning %d targets with %d workers", len(targets), config.max_workers)

    done = 0
    with ResultWriter(config.results_csv, config.results_jsonl, resume=args.resume) as writer:
        for record in map_concurrent(scanner.scan_target_safe, targets, config.max_workers):
            writer.write(record)
            done += 1
            if done % 100 == 0:
                log.info("progress: %d/%d", done, len(targets))

    log.info("wrote %s and %s", config.results_csv, config.results_jsonl)
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Print summary tables from an existing results CSV."""
    setup_logging("INFO")
    df = load_results(args.results_csv)
    print(summarize(df))
    return 0


def _cmd_plot(args: argparse.Namespace) -> int:
    """Write figures from an existing results CSV."""
    setup_logging("INFO")
    df = load_results(args.results_csv)
    paths = generate_all(df, args.out)
    for path in paths:
        log.info("wrote %s", path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Define the CLI surface."""
    parser = argparse.ArgumentParser(prog="pqreadiness", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="scan a domain population")
    p_run.add_argument("--config", default="config/default.yaml")
    p_run.add_argument("--limit", type=int, default=0, help="cap targets (0 = all)")
    p_run.add_argument(
        "--resume",
        action="store_true",
        help="append to existing results, skipping already-scanned hostnames",
    )
    p_run.set_defaults(func=_cmd_run)

    p_analyze = sub.add_parser("analyze", help="summarize a results CSV")
    p_analyze.add_argument("results_csv")
    p_analyze.set_defaults(func=_cmd_analyze)

    p_plot = sub.add_parser("plot", help="plot figures from a results CSV")
    p_plot.add_argument("results_csv")
    p_plot.add_argument("--out", default="data/processed/figures")
    p_plot.set_defaults(func=_cmd_plot)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the chosen subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
