"""VESTRIK // VAULT — Structured Knowledge Intelligence for AI agents."""

__version__ = "3.0.0"
__author__ = "J'Juan Wilson Jr. / Micro Hustle Stack"
__license__ = "MIT"

from .models import (
    LinkReference, HeadingInfo, CalloutInfo, TagInfo, EmbeddedFile,
    TableInfo, DataviewQuery, UrgencySignal, StrategicScore, ParsedNote,
)
from .parser import VaultParser

__all__ = [
    "VaultParser", "LinkReference", "HeadingInfo", "CalloutInfo", "TagInfo",
    "EmbeddedFile", "TableInfo", "DataviewQuery", "UrgencySignal",
    "StrategicScore", "ParsedNote", "__version__",
]
