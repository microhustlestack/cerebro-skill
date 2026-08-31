"""VESTRIK command-line interface."""

import argparse
import json
import os
import sys

from . import __version__
from .parser import VaultParser

_URGENCY_RANK = {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "PAST": 1}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vestrik",
        description="VESTRIK // VAULT — structured knowledge intelligence for markdown vaults",
    )
    parser.add_argument("vault", help="Path to the vault directory")
    parser.add_argument("output", nargs="?", help="Path for JSON index output (optional)")
    parser.add_argument("--report", metavar="FILE", help="Write VESTRIK report to FILE ('-' for stdout)")
    parser.add_argument("--query", metavar="TEXT", help="Scan label for the report header")
    parser.add_argument("--top", type=int, default=10, metavar="N", help="Top N notes in report (default: 10)")
    parser.add_argument("--gaps", action="store_true", help="Include structural gap analysis")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console summary")
    parser.add_argument("--version", action="version", version=f"vestrik {__version__}")
    return parser


def _print_summary(vault: VaultParser, args) -> None:
    report = vault.export_report()
    print(f"Vault: {args.vault}")
    print(f"Notes parsed: {len(vault.notes)}")
    print(f"Parse errors: {len(vault.parse_errors)}")
    print("\n=== VAULT SUMMARY ===")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")


def _print_gaps(vault: VaultParser) -> None:
    gaps = vault.gap_report()
    print("\n=== STRUCTURAL GAPS ===")
    print(f"  unresolved entities: {len(gaps['unresolved_links'])}")
    print(f"  implicit connections: {len(gaps['implicit_connections'])}")
    print(f"  bottlenecks: {len(gaps['bottlenecks'])}")
    print(f"  thin coverage tags: {len(gaps['thin_coverage'])}")


def main(argv: list[str] = None) -> int:
    try:
        return _run(argv)
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 0
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


def _run(argv: list[str] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not os.path.isdir(args.vault):
        print(f"error: vault directory not found: {args.vault}", file=sys.stderr)
        return 2

    vault = VaultParser(args.vault)
    vault.scan()
    if not vault.notes:
        print(f"warning: no markdown files found in {args.vault}", file=sys.stderr)

    if not args.quiet:
        _print_summary(vault, args)
        if args.gaps:
            _print_gaps(vault)

    if args.output:
        if args.gaps:
            payload = json.loads(vault.export_json())
            payload["gap_analysis"] = vault.gap_report()
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        else:
            vault.export_json(args.output)
        if not args.quiet:
            print(f"\nJSON index written: {args.output}")

    if args.report:
        report_text = vault.export_vestrik_report(query=args.query, top_n=args.top)
        if args.report == "-":
            print(report_text)
        else:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(report_text)
            if not args.quiet:
                print(f"VESTRIK report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
