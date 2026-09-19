"""
CEREBRO — Strategic Intelligence Engine for markdown vaults.

Think like a strategist, not a search engine.

    from cerebro import VaultParser

    vault = VaultParser("/path/to/vault")
    vault.scan()
    print(vault.export_cerebro_report())
"""

__version__ = "3.0.1"
__author__ = "J'Juan Wilson Jr. / Micro Hustle Stack"
__license__ = "MIT"

from .models import (
    LinkReference,
    HeadingInfo,
    CalloutInfo,
    TagInfo,
    EmbeddedFile,
    TableInfo,
    DataviewQuery,
    UrgencySignal,
    StrategicScore,
    ParsedNote,
)
from .parser import VaultParser

__all__ = [
    "VaultParser",
    "LinkReference",
    "HeadingInfo",
    "CalloutInfo",
    "TagInfo",
    "EmbeddedFile",
    "TableInfo",
    "DataviewQuery",
    "UrgencySignal",
    "StrategicScore",
    "ParsedNote",
    "__version__",
]
