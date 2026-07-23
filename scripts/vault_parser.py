#!/usr/bin/env python3
"""
Back-compatibility shim.

CEREBRO 2.x shipped a single-file parser at scripts/vault_parser.py, and
existing installs, agent SKILL files and shell snippets still call that
path. The engine now lives in the `cerebro` package; this forwards to it so
nothing downstream breaks.

Prefer the installed entrypoint:

    pip install -e .
    cerebro /path/to/vault --report cerebro_report.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cerebro import (  # noqa: E402
    VaultParser,
    ParsedNote,
    UrgencySignal,
    StrategicScore,
    __version__,
)
from cerebro.cli import main  # noqa: E402

__all__ = ["VaultParser", "ParsedNote", "UrgencySignal", "StrategicScore", "main", "__version__"]

if __name__ == "__main__":
    raise SystemExit(main())
