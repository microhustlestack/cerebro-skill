"""
CEREBRO command-line interface.

    cerebro /path/to/vault
    cerebro /path/to/vault output/vault-index.json --report cerebro_report.md
    cerebro /path/to/vault --gaps --query "funding gaps" --top 15
"""

import argparse
import json
import os
import sys

from . import __version__
from .parser import VaultParser

_URGENCY_RANK = {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "PAST": 1}


def _ensure_parent_dir(path: str) -> None:
    """Create a file's parent directory when one was provided."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cerebro",
        description="CEREBRO — strategic intelligence engine for markdown vaults",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cerebro /path/to/vault
  cerebro /path/to/vault output/vault-index.json
  cerebro /path/to/vault output/vault-index.json --report cerebro_report.md
  cerebro /path/to/vault --gaps --query "find funding gaps" --top 15
  cerebro /path/to/vault --report - --quiet > report.md
        """,
    )
    parser.add_argument("vault", help="Path to the vault directory")
    parser.add_argument("output", nargs="?", help="Path for JSON index output (optional)")
    parser.add_argument("--report", metavar="FILE",
                        help="Write CEREBRO report to this file ('-' for stdout)")
    parser.add_argument("--query", metavar="TEXT",
                        help="Scan label for the CEREBRO report header")
    parser.add_argument("--top", type=int, default=10, metavar="N",
                        help="Top N notes in report (default: 10)")
    parser.add_argument("--gaps", action="store_true",
                        help="Include gap analysis: unresolved links, thin coverage, "
                             "implicit connections, bottlenecks")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress the console summary; only write requested files")
    parser.add_argument("--version", action="version", version=f"cerebro {__version__}")
    return parser


def _print_summary(vault: VaultParser, args) -> None:
    report = vault.export_report()

    print(f"Vault: {args.vault}")
    print(f"Notes parsed: {len(vault.notes)}")
    print(f"Parse errors: {len(vault.parse_errors)}")
    print()

    print("=== VAULT SUMMARY ===")
    for k, v in report["summary"].items():
        print(f"  {k}: {v}")

    print("\n=== ENTITY TYPES ===")
    for etype, n in report["entity_type_distribution"].items():
        print(f"  {etype}: {n}")

    print("\n=== TOP TAGS (20) ===")
    for tag, n in report["top_tags"][:20]:
        print(f"  #{tag}: {n}")

    print("\n=== MOST LINKED HUBS ===")
    for rel, n in report["most_linked_hubs"]:
        print(f"  ({n} backlinks) {rel}")

    print("\n=== TOP SCORED NOTES ===")
    for rel, score in report["top_scored"]:
        print(f"  {score:.3f}  {rel}")

    urgent = vault.urgent_notes()
    if urgent:
        print(f"\n=== URGENT NOTES ({len(urgent)}) ===")
        for n in urgent[:5]:
            sig = max(n.urgency_signals, key=lambda s: _URGENCY_RANK.get(s.level, 0))
            print(f"  [{sig.level}] {n.rel_path}")
            print(f"        {sig.text[:80]}")


def _print_gaps(vault: VaultParser) -> None:
    unresolved = vault.unresolved_links()
    if unresolved:
        print(f"\n=== UNRESOLVED ENTITIES ({len(unresolved)}) ===")
        print("  Referenced by the vault, never documented.")
        for name, count, _ in unresolved[:10]:
            print(f"  ({count}x) {name}")

    implicit = vault.implicit_connections()
    if implicit:
        print(f"\n=== IMPLICIT CONNECTIONS ({len(implicit)}) ===")
        print("  Shared context, no wikilink between them.")
        for conn in implicit:
            a, b = conn["pair"]
            print(f"  {a}  <->  {b}")
            print(f"        shared: {', '.join('#' + t for t in conn['shared_tags'])}")

    necks = vault.bottlenecks()
    if necks:
        print(f"\n=== BOTTLENECKS ({len(necks)}) ===")
        print("  Depended on across multiple directories.")
        for b in necks[:10]:
            print(f"  ({b['dependents']} dependents) {b['rel_path']}")

    thin = vault.thin_coverage()
    if thin:
        print(f"\n=== THIN COVERAGE ({len(thin)} tags with 1 note) ===")
        print("  " + ", ".join("#" + tag for tag, _ in thin[:20]))


def main(argv: list[str] = None) -> int:
    """Entrypoint. Swallows BrokenPipeError so `cerebro vault | head` is quiet."""
    try:
        return _run(argv)
    except BrokenPipeError:
        # Downstream closed the pipe. Redirect stdout to devnull so the
        # interpreter's shutdown flush does not re-raise on the dead fd.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 0
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


def _run(argv: list[str] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    # os.walk stays silent on a bad path, so check explicitly rather than
    # letting a typo report an empty vault as a successful scan.
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
        # Gap findings ride along in the index so downstream agents get the
        # derived intelligence without re-deriving it.
        if args.gaps:
            payload = json.loads(vault.export_json())
            payload["gap_analysis"] = vault.gap_report()
            _ensure_parent_dir(args.output)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        else:
            vault.export_json(args.output)
        if not args.quiet:
            print(f"\nJSON index written: {args.output}")

    if args.report:
        report_text = vault.export_cerebro_report(
            query=args.query, top_n=args.top, include_gaps=args.gaps
        )
        if args.report == "-":
            print(report_text)
        else:
            _ensure_parent_dir(args.report)
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(report_text)
            if not args.quiet:
                print(f"CEREBRO report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
