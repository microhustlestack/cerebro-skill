"""
CEREBRO data models.

Structural types produced by the vault parser. Kept free of parsing logic
so analysis, reporting, and downstream consumers can import them without
pulling in the parser.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class LinkReference:
    target: str
    display: Optional[str] = None
    link_type: str = "wiki"
    line_number: int = 0
    context: str = ""


@dataclass
class HeadingInfo:
    level: int
    text: str
    line_number: int


@dataclass
class CalloutInfo:
    callout_type: str
    title: str
    content_lines: list = field(default_factory=list)


@dataclass
class TagInfo:
    tag: str
    source: str = "frontmatter"


@dataclass
class EmbeddedFile:
    path: str
    mime_hint: str = ""
    line_number: int = 0


@dataclass
class TableInfo:
    line_start: int
    line_end: int
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class DataviewQuery:
    query_text: str
    query_type: str = ""
    line_number: int = 0


@dataclass
class UrgencySignal:
    """A time-sensitivity signal extracted from a note."""
    level: str                       # URGENT, HIGH, STANDARD, PAST
    signal_type: str                 # keyword, date, frontmatter
    text: str                        # context snippet
    days_until: Optional[int] = None # None if no date resolved


@dataclass
class StrategicScore:
    """Multi-dimension strategic score for a note."""
    connectivity: float = 0.0    # Link density (outgoing + 2x incoming)
    tag_influence: float = 0.0   # Vault-wide coverage of this note's tags
    urgency: float = 0.0         # From urgency signals
    richness: float = 0.0        # Content quality markers
    composite: float = 0.0       # Weighted composite


@dataclass
class ParsedNote:
    path: str
    rel_path: str
    filename: str
    directory: str
    file_hash: str
    file_size: int
    line_count: int

    has_frontmatter: bool = False
    frontmatter: dict = field(default_factory=dict)
    frontmatter_raw: str = ""

    body: str = ""
    body_word_count: int = 0
    body_char_count: int = 0

    headings: list = field(default_factory=list)
    wikilinks: list = field(default_factory=list)
    http_links: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    callouts: list = field(default_factory=list)
    embedded_files: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    dataview_queries: list = field(default_factory=list)
    code_blocks: list = field(default_factory=list)

    is_daily_note: bool = False
    note_date: Optional[str] = None
    aliases: list = field(default_factory=list)
    css_classes: list = field(default_factory=list)

    created_at: str = ""
    modified_at: str = ""
    parse_timestamp: str = ""

    entity_type_guess: str = ""
    key_phrases: list = field(default_factory=list)
    mentioned_people: list = field(default_factory=list)
    confidence_score: float = 0.0

    # Intelligence layer (populated post-scan)
    urgency_signals: list = field(default_factory=list)  # UrgencySignal
    strategic_score: Optional[StrategicScore] = None
