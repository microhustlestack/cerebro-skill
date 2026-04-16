#!/usr/bin/env python3
"""
VaultParser 2.0 — Obsidian markdown vault ingestion and intelligence engine.

Reads, parses, and structurally indexes every .md file in a vault,
extracting frontmatter, wikilinks, backlinks, callouts, headings,
tags, entities, and semantic content signals.

New in 2.0:
  - Urgency detection (URGENT / HIGH / STANDARD / PAST)
  - Strategic scoring model (connectivity, tag influence, urgency, richness)
  - export_cerebro_report() -- full CEREBRO INTELLIGENCE SCAN output
  - Orphan detection bug fixed (now uses resolved rel_paths throughout)
  - Directory index bug fixed (_note_directory_index populated on scan)
  - Safe export_json() with no-directory-component path handling
  - argparse CLI with --report, --query, --top flags

Dependencies: Python 3.11+, PyYAML
"""

import os
import re
import yaml
import hashlib
import json
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


# ──────────────────────────────────────────────
# DATA MODELS
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# VAULT PARSER
# ──────────────────────────────────────────────

class VaultParser:
    """
    Parse and index an entire Obsidian vault.

    Usage:
        parser = VaultParser("/path/to/vault")
        parser.scan()

        # CEREBRO report
        print(parser.export_cerebro_report())

        # JSON index
        parser.export_json("output/vault-index.json")

        # Top scored notes
        for note, score in parser.top_scored(5):
            print(note.rel_path, score.composite)
    """

    def __init__(self, vault_path: str, skip_dirs: list = None):
        self.vault_path = os.path.abspath(vault_path)
        self.skip_dirs = skip_dirs or [".obsidian", ".git", "node_modules", "__pycache__"]
        self.notes: dict[str, ParsedNote] = {}
        self.link_graph: dict[str, list[str]] = defaultdict(list)
        self.backlink_graph: dict[str, list[str]] = defaultdict(list)
        self.tag_index: dict[str, list[str]] = defaultdict(list)
        self.entity_index: dict[str, list[str]] = defaultdict(list)
        self._note_directory_index: dict[str, list[str]] = defaultdict(list)
        self.daily_notes: list[str] = []
        self.parse_errors: list[dict] = []
        self._filename_to_rel: dict[str, str] = {}  # normalized filename -> rel_path

        self._category_hints = {
            "skill": ["when to use", "when the user wants", "triggers on", "activation signals"],
            "project": ["timeline", "milestone", "delivera", "requirements", "architecture"],
            "person": ["experience", "background", "contact", "bio", "expertise"],
            "grant": ["deadline", "funding amount", "eligibility", "grant", "award"],
            "opportunity": ["apply by", "submit", "deadline", "opportunity", "program"],
            "meeting": ["attendees", "agenda", "action items", "decisions", "next steps"],
            "strategy": ["objective", "goal", "initiative", "timeline", "metrics"],
            "report": ["summary", "findings", "recommendations", "analysis", "results"],
            "workshop": ["workshop", "session", "participants", "facilitator", "exercises"],
            "log": ["log", "router", "timestamp", "route", "provider"],
        }

        self._urgency_keywords = [
            "urgent", "asap", "immediately", "critical", "time-sensitive",
            "time sensitive", "do not delay", "priority", "overdue", "must act",
        ]

    # ── SCAN ──────────────────────────────────

    def scan(self) -> int:
        """Scan the vault directory, parsing every .md file.
        Returns the number of notes successfully parsed."""
        parsed = 0
        for root, dirs, files in os.walk(self.vault_path, followlinks=False):
            relative_root = os.path.relpath(root, self.vault_path)
            if any(relative_root.startswith(d) for d in self.skip_dirs):
                continue
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]

            for fname in sorted(files):
                if not fname.endswith('.md'):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    note = self._parse_file(fpath)
                    if note:
                        self.notes[note.path] = note
                        self._note_directory_index[note.directory].append(note.rel_path)
                        parsed += 1
                except Exception as e:
                    self.parse_errors.append({"path": fpath, "error": str(e)})

        self._build_link_graph()
        self._build_tag_index()
        self._build_entity_index()
        self._extract_urgency_signals_all()
        self._score_all_notes()

        return parsed

    # ── PARSE SINGLE FILE ─────────────────────

    def _parse_file(self, fpath: str) -> Optional[ParsedNote]:
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            raw_content = f.read()

        if not raw_content.strip():
            return None

        rel = os.path.relpath(fpath, self.vault_path)
        stat = os.stat(fpath)

        note = ParsedNote(
            path=fpath,
            rel_path=rel,
            filename=os.path.basename(fpath),
            directory=os.path.dirname(rel),
            file_hash=hashlib.sha256(raw_content.encode()).hexdigest()[:12],
            file_size=stat.st_size,
            line_count=raw_content.count('\n') + 1,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            parse_timestamp=datetime.now().isoformat(),
        )

        fm_match = re.match(r'^---\n(.*?)\n---\s*\n', raw_content, re.DOTALL)
        if fm_match:
            note.has_frontmatter = True
            note.frontmatter_raw = fm_match.group(1)
            try:
                note.frontmatter = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                note.frontmatter = {"_parse_error": True}
            note.body = raw_content[fm_match.end():]
        else:
            note.body = raw_content

        words = note.body.split()
        note.body_word_count = len(words)
        note.body_char_count = len(note.body)

        note.headings = self._extract_headings(note.body)
        note.wikilinks = self._extract_wikilinks(note.body)
        note.http_links = self._extract_http_links(note.body)
        note.tags = self._extract_tags(note.body, note.frontmatter)
        note.callouts = self._extract_callouts(note.body)
        note.embedded_files = self._extract_embedded_files(note.body)
        note.tables = self._extract_tables(note.body)
        note.dataview_queries = self._extract_dataview(note.body)
        note.code_blocks = self._extract_code_blocks(note.body)
        note.aliases = self._resolve_list(note.frontmatter.get('aliases', []))
        note.css_classes = self._resolve_list(note.frontmatter.get('cssclasses', []))

        self._detect_daily_note(note)
        self._infer_entity_type(note)

        return note

    # ── EXTRACTORS ────────────────────────────

    @staticmethod
    def _extract_headings(body: str) -> list[HeadingInfo]:
        headings = []
        for i, line in enumerate(body.splitlines(), 1):
            m = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if m:
                headings.append(HeadingInfo(
                    level=len(m.group(1)),
                    text=re.sub(r'#.*$', '', m.group(2).strip()),
                    line_number=i,
                ))
        return headings

    @staticmethod
    def _extract_wikilinks(body: str) -> list[LinkReference]:
        links = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            for m in re.finditer(r'\[\[(.+?)\]\]', line):
                inner = m.group(1)
                target = inner
                display = None
                if '|' in inner:
                    target, display = inner.split('|', 1)
                if '#' in target:
                    target = target.split('#')[0]
                links.append(LinkReference(
                    target=target.strip(),
                    display=display.strip() if display else None,
                    link_type="wiki",
                    line_number=i,
                    context=line.strip()[:100],
                ))
        return links

    @staticmethod
    def _extract_http_links(body: str) -> list[LinkReference]:
        links = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            for m in re.finditer(r'\[([^\]]*)\]\((https?://[^\s)]+)\)', line):
                links.append(LinkReference(target=m.group(2), display=m.group(1) or None, link_type="http", line_number=i))
            for m in re.finditer(r'(?<!\()\b(https?://\S+)(?![\])])', line):
                links.append(LinkReference(target=m.group(1).rstrip(',.)'), link_type="http", line_number=i))
        return links

    def _extract_tags(self, body: str, frontmatter: dict) -> list[TagInfo]:
        tags = []
        seen = set()

        fm_tags = frontmatter.get('tags', [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        for t in fm_tags:
            t_clean = str(t).strip().lstrip('#')
            if t_clean and t_clean not in seen:
                tags.append(TagInfo(tag=t_clean, source="frontmatter"))
                seen.add(t_clean)

        for line in body.splitlines():
            if line.strip().startswith('```'):
                continue
            for m in re.finditer(r'#([a-zA-Z][a-zA-Z0-9/_-]*)', line):
                t_clean = m.group(1)
                if t_clean not in seen:
                    tags.append(TagInfo(tag=t_clean, source="inline"))
                    seen.add(t_clean)

        return tags

    @staticmethod
    def _extract_callouts(body: str) -> list[CalloutInfo]:
        callouts = []
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r'^>\s*\[!(\w+)\]\s*(.*)', lines[i])
            if m:
                callout = CalloutInfo(callout_type=m.group(1).lower(), title=m.group(2).strip())
                i += 1
                while i < len(lines) and lines[i].startswith('>'):
                    content_line = lines[i].lstrip('>').strip()
                    if not re.match(r'^\[!\w+\]', content_line):
                        callout.content_lines.append(content_line)
                    i += 1
                callouts.append(callout)
            else:
                i += 1
        return callouts

    @staticmethod
    def _extract_embedded_files(body: str) -> list[EmbeddedFile]:
        files = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            for m in re.finditer(r'!\[\[([^\]]+)\]\]', line):
                path = m.group(1)
                mime = ""
                if path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    mime = "image"
                elif path.endswith('.pdf'):
                    mime = "pdf"
                elif path.endswith(('.mp4', '.mov', '.webm')):
                    mime = "video"
                elif path.endswith(('.mp3', '.wav', '.ogg')):
                    mime = "audio"
                files.append(EmbeddedFile(path=path, mime_hint=mime, line_number=i))
        return files

    @staticmethod
    def _extract_tables(body: str) -> list[TableInfo]:
        tables = []
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith('|'):
                table_start = i
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                    rows.append(row)
                    i += 1
                if len(rows) >= 2:
                    tables.append(TableInfo(line_start=table_start + 1, line_end=i, headers=rows[0], rows=rows[2:]))
            else:
                i += 1
        return tables

    @staticmethod
    def _extract_dataview(body: str) -> list[DataviewQuery]:
        queries = []
        in_block = False
        current_query = []
        q_type = ""
        q_start = 0
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip() == '```dataview':
                in_block = True
                current_query = []
                q_start = i
                continue
            if in_block and line.strip() == '```':
                q_text = '\n'.join(current_query)
                if q_text.strip():
                    queries.append(DataviewQuery(query_text=q_text.strip(), query_type=q_type, line_number=q_start))
                in_block = False
                current_query = []
                q_type = ""
                continue
            if in_block:
                current_query.append(line)
                if not q_type and current_query:
                    first = current_query[0].strip().upper()
                    if first.startswith(('TABLE', 'LIST', 'TASK', 'CALENDAR')):
                        q_type = first.split()[0]
        return queries

    @staticmethod
    def _extract_code_blocks(body: str) -> list[dict]:
        blocks = []
        in_block = False
        lang = ""
        current_lines = []
        start_line = 0
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```') and not in_block:
                in_block = True
                lang = line.strip()[3:].strip()
                current_lines = []
                start_line = i
            elif line.strip().startswith('```') and in_block:
                blocks.append({"lang": lang, "line_start": start_line, "line_end": i, "content": '\n'.join(current_lines)})
                in_block = False
                lang = ""
                current_lines = []
            elif in_block:
                current_lines.append(line)
        return blocks

    # ── URGENCY DETECTION ─────────────────────

    def _extract_urgency_signals_all(self):
        """Run urgency extraction on all parsed notes."""
        today = datetime.now().date()
        for note in self.notes.values():
            note.urgency_signals = self._extract_urgency_signals(note, today)

    def _extract_urgency_signals(self, note: ParsedNote, today: date) -> list[UrgencySignal]:
        signals = []

        for line in note.body.splitlines():
            lower = line.lower()

            if any(kw in lower for kw in self._urgency_keywords):
                signals.append(UrgencySignal(level="URGENT", signal_type="keyword", text=line.strip()[:120]))

            for m in re.finditer(r'\b(\d{4}-\d{2}-\d{2})\b', line):
                try:
                    found_date = datetime.strptime(m.group(1), '%Y-%m-%d').date()
                    delta = (found_date - today).days
                    if delta < 0:
                        level = "PAST"
                    elif delta <= 7:
                        level = "URGENT"
                    elif delta <= 30:
                        level = "HIGH"
                    else:
                        level = "STANDARD"
                    signals.append(UrgencySignal(level=level, signal_type="date", text=line.strip()[:120], days_until=delta))
                except ValueError:
                    pass

        for key in ['deadline', 'due', 'due_date', 'submit_by', 'expires', 'closes', 'apply_by']:
            val = note.frontmatter.get(key)
            if not val:
                continue
            try:
                found_date = datetime.strptime(str(val), '%Y-%m-%d').date()
                delta = (found_date - today).days
                level = "PAST" if delta < 0 else ("URGENT" if delta <= 7 else ("HIGH" if delta <= 30 else "STANDARD"))
                signals.append(UrgencySignal(level=level, signal_type="frontmatter", text=f"{key}: {val}", days_until=delta))
            except ValueError:
                signals.append(UrgencySignal(level="STANDARD", signal_type="frontmatter", text=f"{key}: {val}"))

        return signals

    # ── SCORING MODEL ─────────────────────────

    def _score_all_notes(self):
        """Score all notes after indexes and urgency signals are built."""
        total = max(len(self.notes), 1)
        for note in self.notes.values():
            note.strategic_score = self._score_note(note, total)

    def _score_note(self, note: ParsedNote, total_notes: int) -> StrategicScore:
        """
        Score a note across four dimensions.

        Connectivity  35%  outgoing + 2x incoming wikilinks
        Tag Influence 25%  vault-wide coverage of this note's tags
        Urgency       25%  derived from urgency signal levels
        Richness      15%  content quality markers
        """
        max_possible = max(total_notes - 1, 1)

        outgoing = len(note.wikilinks)
        incoming = len(self.backlink_graph.get(note.rel_path, []))
        connectivity = min((outgoing + incoming * 2) / max_possible, 1.0)

        tag_influence = 0.0
        if note.tags:
            raw = sum(len(self.tag_index.get(t.tag, [])) for t in note.tags)
            tag_influence = min(raw / max_possible, 1.0)

        urgency_map = {"URGENT": 1.0, "HIGH": 0.6, "STANDARD": 0.2, "PAST": 0.05}
        urgency = max((urgency_map.get(s.level, 0.0) for s in note.urgency_signals), default=0.0)

        richness = 0.0
        if note.has_frontmatter:
            richness += 0.2
        if note.headings:
            richness += 0.2
        if note.body_word_count > 200:
            richness += 0.3
        if note.tables:
            richness += 0.15
        if note.callouts:
            richness += 0.15
        richness = min(richness, 1.0)

        composite = round(connectivity * 0.35 + tag_influence * 0.25 + urgency * 0.25 + richness * 0.15, 4)

        return StrategicScore(
            connectivity=round(connectivity, 4),
            tag_influence=round(tag_influence, 4),
            urgency=round(urgency, 4),
            richness=round(richness, 4),
            composite=composite,
        )

    # ── INDEXING ──────────────────────────────

    def _detect_daily_note(self, note: ParsedNote):
        patterns = [r'(\d{4}-\d{2}-\d{2})', r'(\d{4}-\d{1,2}-\d{1,2})']
        fname = note.filename.replace('.md', '')
        for pat in patterns:
            m = re.search(pat, fname) or re.search(pat, note.rel_path)
            if m:
                note.note_date = m.group(1)
                note.is_daily_note = True
                self.daily_notes.append(note.path)
                return

    def _infer_entity_type(self, note: ParsedNote):
        lower_body = note.body.lower()
        scores = {}
        for entity_type, keywords in self._category_hints.items():
            score = sum(1 for kw in keywords if kw in lower_body)
            if score > 0:
                scores[entity_type] = score

        if scores:
            best = max(scores, key=scores.get)
            note.entity_type_guess = best
            note.confidence_score = scores[best] / len(self._category_hints[best])

        if note.directory:
            dir_first = note.directory.split('/')[0]
            skill_dirs = {'agents-skills', 'openclaw-skills', 'workspace-skills', 'openclaw-workspace-skills', 'betting-research-agent-skills'}
            if dir_first in skill_dirs:
                note.entity_type_guess = 'skill'
                note.confidence_score = max(note.confidence_score, 0.8)
            elif dir_first == 'AI Router Logs':
                note.entity_type_guess = 'log'
                note.confidence_score = 0.9
            elif dir_first == 'demystifying-philanthropy':
                note.entity_type_guess = 'workshop'
                note.confidence_score = 0.85

    def _resolve_list(self, val) -> list:
        if isinstance(val, list):
            return [str(v) for v in val]
        elif isinstance(val, str):
            return [val]
        return []

    def _build_link_graph(self):
        """Build link and backlink graphs using resolved rel_paths."""
        self._filename_to_rel = {
            self._normalize_filename(n.filename): n.rel_path
            for n in self.notes.values()
        }
        for note in self.notes.values():
            targets = []
            for link in note.wikilinks:
                target_norm = self._normalize_filename(link.target)
                targets.append(link.target)
                target_rel = self._filename_to_rel.get(target_norm)
                if target_rel:
                    self.backlink_graph[target_rel].append(note.rel_path)
            if targets:
                self.link_graph[note.rel_path] = targets

    def _build_tag_index(self):
        for note in self.notes.values():
            for tag in note.tags:
                self.tag_index[tag.tag].append(note.rel_path)

    def _build_entity_index(self):
        for note in self.notes.values():
            if note.entity_type_guess:
                self.entity_index[note.entity_type_guess].append(note.rel_path)

    @staticmethod
    def _normalize_filename(name: str) -> str:
        name = name.replace('.md', '').strip().lower()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    # ── QUERIES ───────────────────────────────

    def notes_by_tag(self, tag: str) -> list[ParsedNote]:
        rel_paths = set(self.tag_index.get(tag, []))
        return [n for n in self.notes.values() if n.rel_path in rel_paths]

    def notes_by_entity_type(self, etype: str) -> list[ParsedNote]:
        return [n for n in self.notes.values() if n.entity_type_guess == etype]

    def orphaned_notes(self) -> list[ParsedNote]:
        """Notes with no incoming or outgoing wikilinks (resolved by rel_path)."""
        linked_rel_paths = set()
        linked_rel_paths.update(self.link_graph.keys())
        linked_rel_paths.update(self.backlink_graph.keys())
        for sources in self.backlink_graph.values():
            linked_rel_paths.update(sources)
        return [n for n in self.notes.values() if n.rel_path not in linked_rel_paths]

    def most_linked(self, top_n: int = 10) -> list[tuple[str, int]]:
        incoming = {rel: len(sources) for rel, sources in self.backlink_graph.items()}
        return sorted(incoming.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def top_scored(self, top_n: int = 10) -> list[tuple[ParsedNote, StrategicScore]]:
        """Return top-n notes by composite strategic score."""
        scored = [(n, n.strategic_score) for n in self.notes.values() if n.strategic_score]
        return sorted(scored, key=lambda x: x[1].composite, reverse=True)[:top_n]

    def urgent_notes(self) -> list[ParsedNote]:
        return [n for n in self.notes.values() if any(s.level == "URGENT" for s in n.urgency_signals)]

    def high_notes(self) -> list[ParsedNote]:
        urgent_set = set(id(n) for n in self.urgent_notes())
        return [n for n in self.notes.values()
                if any(s.level == "HIGH" for s in n.urgency_signals) and id(n) not in urgent_set]

    def notes_with_callouts(self) -> list[ParsedNote]:
        return [n for n in self.notes.values() if n.callouts]

    def notes_with_dataview(self) -> list[ParsedNote]:
        return [n for n in self.notes.values() if n.dataview_queries]

    def notes_with_tables(self) -> list[ParsedNote]:
        return [n for n in self.notes.values() if n.tables]

    def search_body(self, pattern: str, case_sensitive: bool = False) -> list[tuple[ParsedNote, int, str]]:
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
        for note in self.notes.values():
            for i, line in enumerate(note.body.splitlines(), 1):
                if compiled.search(line):
                    results.append((note, i, line.strip()))
        return results

    # ── CEREBRO INTELLIGENCE REPORT ───────────

    def export_cerebro_report(self, query: str = None, top_n: int = 10) -> str:
        """
        Generate a CEREBRO INTELLIGENCE SCAN report.

        Includes: Top Matches, Key Connections, Strategic Insight,
        Recommended Next Actions. Ready to save or forward to Telegram.
        """
        total = len(self.notes)
        today_str = datetime.now().strftime('%Y-%m-%d')
        lines = []

        lines.append("CEREBRO INTELLIGENCE SCAN")
        if query:
            lines.append(f"Scan: {query}")
        lines.append(f"Vault: {self.vault_path}")
        lines.append(f"Date: {today_str}")
        lines.append(f"Entities analyzed: {total}")
        lines.append("")

        # Top Matches
        lines.append("## Top Matches")
        lines.append(
            f"Scored on connectivity (35%), tag influence (25%), urgency (25%), richness (15%). "
            f"Showing top {min(top_n, total)}."
        )
        lines.append("")

        ranked = self.top_scored(top_n)
        rel_to_name = {n.rel_path: n.filename.replace('.md', '') for n in self.notes.values()}

        for i, (note, score) in enumerate(ranked, 1):
            urgency_level = "STANDARD"
            if any(s.level == "URGENT" for s in note.urgency_signals):
                urgency_level = "URGENT"
            elif any(s.level == "HIGH" for s in note.urgency_signals):
                urgency_level = "HIGH"

            tags_str = " ".join(f"#{t.tag}" for t in note.tags[:5]) or "none"
            incoming = len(self.backlink_graph.get(note.rel_path, []))
            outgoing = len(note.wikilinks)
            name = note.filename.replace('.md', '')

            lines.append(f"{i}. [{urgency_level}] {name}")
            lines.append(f"   Score: {score.composite:.3f} | Type: {note.entity_type_guess or 'unknown'} | Links: {outgoing} out / {incoming} in")
            lines.append(f"   Tags: {tags_str}")
            lines.append(f"   Path: {note.rel_path}")
            if note.urgency_signals:
                top_sig = max(
                    note.urgency_signals,
                    key=lambda s: {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "PAST": 1}.get(s.level, 0)
                )
                lines.append(f"   Signal: [{top_sig.level}] {top_sig.text[:80]}")
            lines.append("")

        # Key Connections
        lines.append("## Key Connections")
        lines.append("Second-degree relationships the vault does not make explicit.")
        lines.append("")

        connections_found = 0
        seen_connections: set[tuple] = set()

        for note in self.notes.values():
            if connections_found >= 8:
                break
            a_targets = self.link_graph.get(note.rel_path, [])
            for target_name in a_targets:
                target_rel = self._filename_to_rel.get(self._normalize_filename(target_name))
                if not target_rel:
                    continue
                for c_name in self.link_graph.get(target_rel, []):
                    if self._normalize_filename(c_name) == self._normalize_filename(note.filename):
                        continue
                    key = tuple(sorted([note.rel_path, target_rel, c_name]))
                    if key not in seen_connections:
                        seen_connections.add(key)
                        a_name = rel_to_name.get(note.rel_path, note.filename.replace('.md', ''))
                        lines.append(f"- {a_name} -> {target_name} -> {c_name}")
                        connections_found += 1
                        if connections_found >= 8:
                            break

        if connections_found == 0:
            lines.append("- No second-degree connections detected.")
            lines.append("  Add wikilinks between related notes to activate connection mapping.")
        lines.append("")

        shared_clusters = [
            (tag, rels) for tag, rels in
            sorted(self.tag_index.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            if len(rels) >= 3
        ]
        if shared_clusters:
            lines.append("Tag clusters (shared context):")
            for tag, rels in shared_clusters:
                names = [rel_to_name.get(r, r) for r in rels[:4]]
                overflow = f"... +{len(rels) - 3}" if len(rels) > 3 else ""
                lines.append(f"  #{tag} ({len(rels)} notes): {', '.join(names[:3])}{overflow}")
            lines.append("")

        # Strategic Insight
        lines.append("## Strategic Insight")

        entity_dist = sorted(self.entity_index.items(), key=lambda x: len(x[1]), reverse=True)
        dominant = entity_dist[0] if entity_dist else ("unknown", [])
        top_3_tags = sorted(self.tag_index.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        orphans = self.orphaned_notes()
        urgent = self.urgent_notes()
        high = self.high_notes()

        lines.append(f"Vault: {total} notes across {len(self._note_directory_index)} directories.")
        lines.append(
            f"Dominant type: {dominant[0]} "
            f"({len(dominant[1])} notes, {round(len(dominant[1]) / max(total, 1) * 100)}% of vault)."
        )
        if top_3_tags:
            tag_str = ', '.join(f"#{t} ({len(n)} notes)" for t, n in top_3_tags)
            lines.append(f"Top tags: {tag_str}.")
        if urgent:
            lines.append(f"{len(urgent)} notes carry URGENT signals. Act on these first.")
        if high:
            lines.append(f"{len(high)} notes carry HIGH signals (window: 30 days).")
        if orphans:
            lines.append(
                f"{len(orphans)} orphaned notes: content that exists but is not connected. "
                "Link, tag, or archive."
            )
        hub_notes = self.most_linked(3)
        if hub_notes:
            hub_str = ', '.join(f"{rel_to_name.get(r, r)} ({c} in)" for r, c in hub_notes)
            lines.append(f"Highest-connectivity hubs: {hub_str}.")
        lines.append("")

        # Recommended Next Actions
        lines.append("## Recommended Next Actions")
        actions = []

        if urgent:
            n = urgent[0]
            top_sig = max(n.urgency_signals, key=lambda s: {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "PAST": 1}.get(s.level, 0))
            actions.append(f"[URGENT] Act on '{n.filename.replace('.md','')}': {top_sig.text[:60]}")
        if high:
            n = high[0]
            actions.append(f"[HIGH] Review '{n.filename.replace('.md','')}' before deadline window closes.")
        if ranked:
            top_note = ranked[0][0]
            actions.append(
                f"[HIGH] Deepen '{top_note.filename.replace('.md','')}' — highest composite score, "
                "highest strategic leverage."
            )
        if orphans:
            actions.append(f"[STANDARD] Process {len(orphans)} orphaned notes: link, tag, or archive each one.")
        if top_3_tags:
            top_tag, top_rels = top_3_tags[0]
            actions.append(f"[STANDARD] Build a #{top_tag} index note — it spans {len(top_rels)} notes and is your most active concept cluster.")
        actions.append(
            f"[STANDARD] Run a targeted CEREBRO query on the top {min(3, len(ranked))} notes "
            "above to surface compound opportunities across entity types."
        )

        for idx, action in enumerate(actions, 1):
            lines.append(f"{idx}. {action}")

        lines.append("")
        lines.append("---")
        lines.append(f"CEREBRO v2.0 | {today_str} | vault_parser.py")

        return '\n'.join(lines)

    # ── EXPORT ────────────────────────────────

    def export_report(self) -> dict:
        """Comprehensive vault analysis report as a dict."""
        return {
            "summary": {
                "total_notes": len(self.notes),
                "total_files_size_kb": round(sum(n.file_size for n in self.notes.values()) / 1024, 1),
                "total_words": sum(n.body_word_count for n in self.notes.values()),
                "total_wikilinks": sum(len(n.wikilinks) for n in self.notes.values()),
                "total_backlinks": sum(len(v) for v in self.backlink_graph.values()),
                "parse_errors": len(self.parse_errors),
                "daily_notes": len(self.daily_notes),
                "urgent_notes": len(self.urgent_notes()),
                "high_notes": len(self.high_notes()),
                "orphaned_notes": len(self.orphaned_notes()),
            },
            "by_directory": dict(sorted(
                {d: len(notes) for d, notes in self._note_directory_index.items()}.items(),
                key=lambda x: x[1], reverse=True
            )),
            "entity_type_distribution": {
                k: len(v) for k, v in sorted(self.entity_index.items(), key=lambda x: len(x[1]), reverse=True)
            },
            "top_tags": sorted(
                [(tag, len(notes)) for tag, notes in self.tag_index.items()],
                key=lambda x: x[1], reverse=True
            )[:30],
            "most_linked_hubs": self.most_linked(10),
            "top_scored": [(n.rel_path, round(score.composite, 3)) for n, score in self.top_scored(10)],
            "notes_with_callouts": len(self.notes_with_callouts()),
            "notes_with_tables": len(self.notes_with_tables()),
            "notes_with_dataview": len(self.notes_with_dataview()),
            "parse_errors": self.parse_errors[:10],
        }

    def export_json(self, output_path: str = None) -> str:
        """Export the entire vault index as JSON."""
        data = {
            "vault_path": self.vault_path,
            "indexed_at": datetime.now().isoformat(),
            "cerebro_version": "2.0",
            "total_notes": len(self.notes),
            "notes": {
                n.rel_path: {
                    "frontmatter": n.frontmatter,
                    "word_count": n.body_word_count,
                    "headings_count": len(n.headings),
                    "wikilinks": [l.target for l in n.wikilinks],
                    "tags": [t.tag for t in n.tags],
                    "entity_type": n.entity_type_guess,
                    "confidence": round(n.confidence_score, 2),
                    "has_callouts": bool(n.callouts),
                    "has_tables": bool(n.tables),
                    "has_dataview": bool(n.dataview_queries),
                    "code_block_languages": list({cb.get("lang", "") for cb in n.code_blocks}),
                    "urgency_signals": [
                        {"level": s.level, "type": s.signal_type, "text": s.text, "days_until": s.days_until}
                        for s in n.urgency_signals
                    ],
                    "strategic_score": {
                        "composite": n.strategic_score.composite,
                        "connectivity": n.strategic_score.connectivity,
                        "tag_influence": n.strategic_score.tag_influence,
                        "urgency": n.strategic_score.urgency,
                        "richness": n.strategic_score.richness,
                    } if n.strategic_score else None,
                }
                for n in self.notes.values()
            },
            "link_graph": dict(self.link_graph),
            "backlink_graph": dict(self.backlink_graph),
            "tag_index": dict(self.tag_index),
            "entity_index": dict(self.entity_index),
            "parse_errors": self.parse_errors,
        }

        json_str = json.dumps(data, indent=2, default=str)

        if output_path:
            dirname = os.path.dirname(output_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(json_str)

        return json_str


# ──────────────────────────────────────────────
# CLI INTERFACE
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="CEREBRO VaultParser 2.0 -- Obsidian vault intelligence engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 vault_parser.py /path/to/vault
  python3 vault_parser.py /path/to/vault output/vault-index.json
  python3 vault_parser.py /path/to/vault output/vault-index.json --report cerebro_report.md
  python3 vault_parser.py /path/to/vault --query "find grant opportunities" --top 15
        """
    )
    parser.add_argument("vault", help="Path to the vault directory")
    parser.add_argument("output", nargs="?", help="Path for JSON index output (optional)")
    parser.add_argument("--report", metavar="FILE", help="Write CEREBRO report to this file")
    parser.add_argument("--query", metavar="TEXT", help="Scan label for the CEREBRO report header")
    parser.add_argument("--top", type=int, default=10, metavar="N", help="Top N notes in report (default: 10)")
    args = parser.parse_args()

    vault = VaultParser(args.vault)
    count = vault.scan()

    print(f"Vault: {args.vault}")
    print(f"Notes parsed: {count}")
    print(f"Parse errors: {len(vault.parse_errors)}")
    print()

    report = vault.export_report()

    print("=== VAULT SUMMARY ===")
    for k, v in report['summary'].items():
        print(f"  {k}: {v}")

    print("\n=== ENTITY TYPES ===")
    for etype, n in report['entity_type_distribution'].items():
        print(f"  {etype}: {n}")

    print("\n=== TOP TAGS (20) ===")
    for tag, n in report['top_tags'][:20]:
        print(f"  #{tag}: {n}")

    print("\n=== MOST LINKED HUBS ===")
    for rel, n in report['most_linked_hubs']:
        print(f"  ({n} backlinks) {rel}")

    print("\n=== TOP SCORED NOTES ===")
    for rel, score in report['top_scored']:
        print(f"  {score:.3f}  {rel}")

    urgent = vault.urgent_notes()
    if urgent:
        print(f"\n=== URGENT NOTES ({len(urgent)}) ===")
        for n in urgent[:5]:
            sig = max(n.urgency_signals, key=lambda s: {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "PAST": 1}.get(s.level, 0))
            print(f"  [{sig.level}] {n.rel_path}")
            print(f"        {sig.text[:80]}")

    orphans = vault.orphaned_notes()
    print(f"\n=== ORPHANED NOTES ===")
    print(f"  Count: {len(orphans)}")
    for o in orphans[:10]:
        print(f"  {o.rel_path}")

    if args.output:
        vault.export_json(args.output)
        print(f"\nJSON index written to: {args.output}")

    cerebro_report = vault.export_cerebro_report(query=args.query, top_n=args.top)

    if args.report:
        with open(args.report, 'w') as f:
            f.write(cerebro_report)
        print(f"CEREBRO report written to: {args.report}")
    else:
        print()
        print(cerebro_report)
