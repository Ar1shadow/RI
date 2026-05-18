"""Command-line entry point.

Subcommands:
    ri scrape <html_dir>    Parse HTML bulletins into Document records.
    ri build                Build SQLite index from scraped corpus.
    ri query [<text>]       Interactive REPL or one-shot query.
    ri eval                 Run golden-set evaluation.

Each subcommand calls into the corresponding layer module. The CLI keeps no
business logic of its own.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ri", description="RI — Recherche sur Indexation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scrape = sub.add_parser("scrape", help="Parse HTML bulletins into corpus")
    p_scrape.add_argument("html_dir", help="Directory containing .htm files")
    p_scrape.add_argument("--emit-xml", action="store_true", help="Also write debug corpus.xml")

    sub.add_parser("build", help="Build SQLite index from scraped corpus")

    p_query = sub.add_parser("query", help="Run a query (interactive REPL if omitted)")
    p_query.add_argument("text", nargs="?", help="Query string; opens REPL when omitted")
    p_query.add_argument("--mode", choices=["booleen", "classe"], default="classe")

    p_eval = sub.add_parser("eval", help="Run golden-set evaluation")
    p_eval.add_argument("--report", help="Write JSON report to this path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "scrape":
        from ri.corpus.scraper import scrape_directory

        scrape_directory(args.html_dir, emit_xml=args.emit_xml)
        return 0
    if args.cmd == "build":
        from ri.indexing.builder import build_index

        build_index()
        return 0
    if args.cmd == "query":
        from ri.retrieval.engine import run_query_repl, run_single_query

        if args.text:
            run_single_query(args.text, mode=args.mode)
        else:
            run_query_repl()
        return 0
    if args.cmd == "eval":
        from ri.evaluation.metrics import run_eval

        run_eval(report_path=args.report)
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
