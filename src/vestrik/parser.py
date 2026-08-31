"""
CEREBRO VaultParser — markdown vault ingestion and structural indexing.

Walks a vault, parses every .md file, and builds the link graph, backlink
graph, tag index, entity index, urgency signals, and strategic scores that
the analysis and reporting layers consume.

Report rendering lives in report.py; derived intelligence lives in
analysis.py. Both are mixed into VaultParser so the public surface is a
single object.

Dependencies: Python 3.11+, PyYAML
"""

import os
import re
import json
import hashlib
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

import yaml

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
from .report import ReportMixin
from .analysis import AnalysisMixin


# ──────────────────────────────────────────────
# COMPILED PATTERNS
# Compiled once at import rather than re-resolved per line per file.
# Every pattern the hot path touches is declared here so the vault
# grammar CEREBRO understands is reviewable in one place.
# ──────────────────────────────────────────────

_RE_FRONTMATTER   = re.compile(r'^---\n(.*?)\n---\s*\n', re.DOTALL)
_RE_HEADING       = re.compile(r'^(#{1,6})\s+(.+)$')
_RE_TRAILING_TAG  = re.compile(r'#.*$')
_RE_WIKILINK      = re.compile(r'\[\[(.+?)\]\]')
_RE_MD_LINK       = re.compile(r'\[([^\]]*)\]\((https?://[^\s)]+)\)')
_RE_BARE_URL      = re.compile(r'(?<!\()\b(https?://\S+)(?![\])])')
_RE_INLINE_TAG    = re.compile(r'#([a-zA-Z][a-zA-Z0-9/_-]*)')
_RE_CALLOUT       = re.compile(r'^>\s*\[!(\w+)\]\s*(.*)')
_RE_CALLOUT_HEADER = re.compile(r'^\[!\w+\]')
_RE_EMBED         = re.compile(r'!\[\[([^\]]+)\]\]')
_RE_ISO_DATE      = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
_RE_NON_WORD      = re.compile(r'[^\w\s-]')
_RE_WHITESPACE    = re.compile(r'\s+')
_RE_DAILY_NOTE    = (
    re.compile(r'(\d{4}-\d{2}-\d{2})'),
    re.compile(r'(\d{4}-\d{1,2}-\d{1,2})'),
)


class VaultParser(ReportMixin, AnalysisMixin):
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

        fm_match = _RE_FRONTMATTER.match(raw_content)
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
            m = _RE_HEADING.match(line.strip())
            if m:
                headings.append(HeadingInfo(
                    level=len(m.group(1)),
                    text=_RE_TRAILING_TAG.sub('', m.group(2).strip()),
                    line_number=i,
                ))
        return headings

    @staticmethod
    def _extract_wikilinks(body: str) -> list[LinkReference]:
        links = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            for m in _RE_WIKILINK.finditer(line):
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
            for m in _RE_MD_LINK.finditer(line):
                links.append(LinkReference(target=m.group(2), display=m.group(1) or None, link_type="http", line_number=i))
            for m in _RE_BARE_URL.finditer(line):
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
            for m in _RE_INLINE_TAG.finditer(line):
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
            m = _RE_CALLOUT.match(lines[i])
            if m:
                callout = CalloutInfo(callout_type=m.group(1).lower(), title=m.group(2).strip())
                i += 1
                while i < len(lines) and lines[i].startswith('>'):
                    content_line = lines[i].lstrip('>').strip()
                    if not _RE_CALLOUT_HEADER.match(content_line):
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
            for m in _RE_EMBED.finditer(line):
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

            for m in _RE_ISO_DATE.finditer(line):
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
        fname = note.filename.replace('.md', '')
        for pat in _RE_DAILY_NOTE:
            m = pat.search(fname) or pat.search(note.rel_path)
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
        name = _RE_NON_WORD.sub('', name)
        name = _RE_WHITESPACE.sub(' ', name)
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
