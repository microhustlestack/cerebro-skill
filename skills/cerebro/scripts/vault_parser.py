#!/usr/bin/env python3
"""
VaultParser — Obsidian markdown vault ingestion and interpretation engine.

Reads, parses, and structurally indexes every .md file in a vault,
extracting frontmatter, wikilinks, backlinks, callouts, headings,
tags, entities, and semantic content signals.

Dependencies: Python 3.11+, PyYAML (stdlib-equivalent on this machine)
"""

import os
import re
import yaml
import hashlib
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict


# ──────────────────────────────────────────────
# DATA MODELS
# ──────────────────────────────────────────────

@dataclass
class LinkReference:
    """A link extracted from markdown content."""
    target: str
    display: Optional[str] = None
    link_type: str = "wiki"  # wiki, http, internal
    line_number: int = 0
    context: str = ""  # surrounding text


@dataclass
class HeadingInfo:
    """A heading in the document."""
    level: int
    text: str
    line_number: int


@dataclass
class CalloutInfo:
    """A callout/admonition block."""
    callout_type: str  # note, warning, tip, danger, etc.
    title: str
    content_lines: list = field(default_factory=list)


@dataclass
class TagInfo:
    """A tag found in the document."""
    tag: str
    source: str = "frontmatter"  # frontmatter, inline


@dataclass
class EmbeddedFile:
    """An embedded file reference (image, PDF, etc.)."""
    path: str
    mime_hint: str = ""
    line_number: int = 0


@dataclass
class TableInfo:
    """A markdown table found in the document."""
    line_start: int
    line_end: int
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class DataviewQuery:
    """A Dataview plugin query block."""
    query_text: str
    query_type: str = ""  # TABLE, LIST, TASK, CALENDAR
    line_number: int = 0


@dataclass
class ParsedNote:
    """Complete parsed representation of a single .md file."""
    path: str              # Absolute path
    rel_path: str          # Relative to vault root
    filename: str
    directory: str
    file_hash: str         # SHA256 of raw content
    file_size: int         # Bytes
    line_count: int
    
    # Frontmatter
    has_frontmatter: bool = False
    frontmatter: dict = field(default_factory=dict)
    frontmatter_raw: str = ""
    
    # Content
    body: str = ""
    body_word_count: int = 0
    body_char_count: int = 0
    
    # Extracted elements
    headings: list = field(default_factory=list)       # HeadingInfo
    wikilinks: list = field(default_factory=list)      # LinkReference
    http_links: list = field(default_factory=list)     # LinkReference
    tags: list = field(default_factory=list)           # TagInfo
    callouts: list = field(default_factory=list)       # CalloutInfo
    embedded_files: list = field(default_factory=list) # EmbeddedFile
    tables: list = field(default_factory=list)         # TableInfo
    dataview_queries: list = field(default_factory=list) # DataviewQuery
    code_blocks: list = field(default_factory=list)    # {lang, lines, content}
    
    # Structure
    is_daily_note: bool = False
    note_date: Optional[str] = None
    aliases: list = field(default_factory=list)
    css_classes: list = field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    modified_at: str = ""
    parse_timestamp: str = ""
    
    # Semantic signals
    entity_type_guess: str = ""  # What type of entity this seems to be
    key_phrases: list = field(default_factory=list)
    mentioned_people: list = field(default_factory=list)
    confidence_score: float = 0.0


# ──────────────────────────────────────────────
# VAULT PARSER
# ──────────────────────────────────────────────

class VaultParser:
    """
    Parse and index an entire Obsidian vault.
    
    Usage:
        parser = VaultParser("/path/to/vault")
        parser.scan()
        
        # Access individual notes
        for note in parser.notes.values():
            print(note.rel_path, note.frontmatter)
        
        # Access the link graph
        for source, targets in parser.link_graph.items():
            print(f"{source} -> {targets}")
        
        # Export
        report = parser.export_report()
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
        
        # Heuristic entity type detectors
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
    
    # ── SCAN ──────────────────────────────────
    
    def scan(self) -> int:
        """Scan the vault directory, parsing every .md file.
        Returns the number of notes parsed."""
        
        parsed = 0
        for root, dirs, files in os.walk(self.vault_path, followlinks=False):
            # Skip excluded directories
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
                        parsed += 1
                except Exception as e:
                    self.parse_errors.append({
                        "path": fpath,
                        "error": str(e),
                    })
        
        # Build indexes after all notes are parsed
        self._build_link_graph()
        self._build_tag_index()
        self._build_entity_index()
        
        return parsed
    
    # ── PARSE SINGLE FILE ─────────────────────
    
    def _parse_file(self, fpath: str) -> Optional[ParsedNote]:
        """Parse a single markdown file into a ParsedNote."""
        
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
        
        # Split frontmatter
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
            note.has_frontmatter = False
            note.frontmatter = {}
            note.body = raw_content
        
        # Content stats
        words = note.body.split()
        note.body_word_count = len(words)
        note.body_char_count = len(note.body)
        
        # Extract all elements
        note.headings = self._extract_headings(note.body)
        note.wikilinks = self._extract_wikilinks(note.body)
        note.http_links = self._extract_http_links(note.body)
        note.tags = self._extract_tags(note.body, note.frontmatter)
        note.callouts = self._extract_callouts(note.body)
        note.embedded_files = self._extract_embedded_files(note.body)
        note.tables = self._extract_tables(note.body)
        note.dataview_queries = self._extract_dataview(note.body)
        note.code_blocks = self._extract_code_blocks(note.body)
        
        # Metadata
        note.aliases = self._resolve_list(note.frontmatter.get('aliases', []))
        note.css_classes = self._resolve_list(note.frontmatter.get('cssclasses', []))
        
        # Daily note detection
        self._detect_daily_note(note)
        
        # Entity type inference
        self._infer_entity_type(note)
        
        return note
    
    # ── EXTRACTORS ────────────────────────────
    
    @staticmethod
    def _extract_headings(body: str) -> list[HeadingInfo]:
        """Extract all markdown headings with level and line number."""
        headings = []
        for i, line in enumerate(body.splitlines(), 1):
            m = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if m:
                headings.append(HeadingInfo(
                    level=len(m.group(1)),
                    text=re.sub(r'#.*$', '', m.group(2).strip()),  # Strip trailing heading anchors
                    line_number=i,
                ))
        return headings
    
    @staticmethod
    def _extract_wikilinks(body: str) -> list[LinkReference]:
        """Extract [[wikilinks]] with display text and embedded links."""
        links = []
        for i, line in enumerate(body.splitlines(), 1):
            # Skip code blocks
            if line.strip().startswith('```'):
                continue
            # Pattern: [[target]] or [[target|display]] or [[target#heading]]
            for m in re.finditer(r'\[\[(.+?)\]\]', line):
                inner = m.group(1)
                target = inner
                display = None
                
                if '|' in inner:
                    target, display = inner.split('|', 1)
                
                # Strip heading/heading anchors for target resolution
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
        """Extract http/https URLs."""
        links = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            for m in re.finditer(r'\[([^\]]*)\]\((https?://[^\s)]+)\)', line):
                links.append(LinkReference(
                    target=m.group(2),
                    display=m.group(1) or None,
                    link_type="http",
                    line_number=i,
                ))
            # Bare URLs
            for m in re.finditer(r'(?<!\()\b(https?://\S+)(?![\])])', line):
                links.append(LinkReference(
                    target=m.group(1).rstrip(',.)').rstrip(),
                    link_type="http",
                    line_number=i,
                ))
        return links
    
    def _extract_tags(self, body: str, frontmatter: dict) -> list[TagInfo]:
        """Extract tags from frontmatter and inline."""
        tags = []
        seen = set()
        
        # From frontmatter
        fm_tags = frontmatter.get('tags', [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        for t in fm_tags:
            t_clean = str(t).strip().lstrip('#')
            if t_clean and t_clean not in seen:
                tags.append(TagInfo(tag=t_clean, source="frontmatter"))
                seen.add(t_clean)
        
        # Inline tags: #tag-name
        for i, line in enumerate(body.splitlines(), 1):
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
        """Extract Obsidian callout blocks: > [!type] Title"""
        callouts = []
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r'^>\s*\[!(\w+)\]\s*(.*)', lines[i])
            if m:
                callout = CalloutInfo(
                    callout_type=m.group(1).lower(),
                    title=m.group(2).strip(),
                )
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
        """Extract embedded file references: ![[filename]] or ![](url)"""
        files = []
        for i, line in enumerate(body.splitlines(), 1):
            if line.strip().startswith('```'):
                continue
            # ![[file]]
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
        """Extract markdown tables."""
        tables = []
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            # Table starts with | and has |---| separator within 2 lines
            if lines[i].strip().startswith('|'):
                table_start = i
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                    rows.append(row)
                    i += 1
                
                if len(rows) >= 2:  # Need at least header + separator
                    headers = rows[0]
                    data_rows = rows[2:]  # Skip header and separator
                    tables.append(TableInfo(
                        line_start=table_start + 1,
                        line_end=i,
                        headers=headers,
                        rows=data_rows,
                    ))
            else:
                i += 1
        return tables
    
    @staticmethod
    def _extract_dataview(body: str) -> list[DataviewQuery]:
        """Extract Dataview plugin query blocks."""
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
                    queries.append(DataviewQuery(
                        query_text=q_text.strip(),
                        query_type=q_type,
                        line_number=q_start,
                    ))
                in_block = False
                current_query = []
                continue
            if in_block:
                current_query.append(line)
                # Detect query type from first line
                if not q_type and current_query:
                    first = current_query[0].strip().upper()
                    if first.startswith(('TABLE', 'LIST', 'TASK', 'CALENDAR')):
                        q_type = first.split()[0]
        
        return queries
    
    @staticmethod
    def _extract_code_blocks(body: str) -> list[dict]:
        """Extract code fences with language."""
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
                blocks.append({
                    "lang": lang,
                    "line_start": start_line,
                    "line_end": i,
                    "content": '\n'.join(current_lines),
                })
                in_block = False
                lang = ""
                current_lines = []
            elif in_block:
                current_lines.append(line)
        
        return blocks
    
    # ── INDEXING ──────────────────────────────
    
    def _detect_daily_note(self, note: ParsedNote):
        """Detect if a note is a daily note based on name, date, or path."""
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{1,2}-\d{1,2})',
        ]
        fname = note.filename.replace('.md', '')
        for pat in patterns:
            m = re.search(pat, fname)
            if m:
                note.note_date = m.group(1)
                note.is_daily_note = True
                self.daily_notes.append(note.path)
                return
            m = re.search(pat, note.rel_path)
            if m:
                note.note_date = m.group(1)
                note.is_daily_note = True
                self.daily_notes.append(note.path)
                return
    
    def _infer_entity_type(self, note: ParsedNote):
        """Infer what type of entity this note represents based on content signals."""
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
        
        # Directory path is a strong signal
        if note.directory:
            dir_first = note.directory.split('/')[0]
            if dir_first in ('agents-skills', 'openclaw-skills', 'workspace-skills', 
                           'openclaw-workspace-skills', 'betting-research-agent-skills'):
                if not note.entity_type_guess or scores.get('skill', 0) > 0:
                    note.entity_type_guess = 'skill'
                    note.confidence_score = max(note.confidence_score, 0.8)
            elif dir_first == 'AI Router Logs':
                note.entity_type_guess = 'log'
                note.confidence_score = 0.9
            elif dir_first == 'demystifying-philanthropy':
                note.entity_type_guess = 'workshop'
                note.confidence_score = 0.85
    
    def _resolve_list(self, val) -> list:
        """Normalize frontmatter list values."""
        if isinstance(val, list):
            return [str(v) for v in val]
        elif isinstance(val, str):
            return [val]
        return []
    
    def _build_link_graph(self):
        """Build the full wikilink graph and backlink map."""
        note_keys = set()
        for note in self.notes.values():
            # Create normalized key for matching
            norm = self._normalize_filename(note.filename)
            note_keys.add(norm)
        
        for note in self.notes.values():
            source_key = note.rel_path
            targets = []
            
            for link in note.wikilinks:
                target_norm = self._normalize_filename(link.target)
                targets.append(link.target)
                
                # Find matching note
                for n in self.notes.values():
                    if self._normalize_filename(n.filename) == target_norm:
                        self.backlink_graph[n.rel_path].append(source_key)
                        break
            
            if targets:
                self.link_graph[source_key] = targets
    
    def _build_tag_index(self):
        """Build a reverse index: tag -> list of note paths."""
        for note in self.notes.values():
            for tag in note.tags:
                self.tag_index[tag.tag].append(note.rel_path)
    
    def _build_entity_index(self):
        """Build a reverse index: entity_type -> list of note paths."""
        for note in self.notes.values():
            if note.entity_type_guess:
                self.entity_index[note.entity_type_guess].append(note.rel_path)
    
    @staticmethod
    def _normalize_filename(name: str) -> str:
        """Normalize a filename for cross-matching."""
        name = name.replace('.md', '').strip()
        name = name.lower()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    # ── QUERIES ───────────────────────────────
    
    def notes_by_tag(self, tag: str) -> list[ParsedNote]:
        """Get all notes that have a specific tag."""
        paths = self.tag_index.get(tag, [])
        return [self.notes[n.path] for n in self.notes.values() if n.rel_path in paths]
    
    def notes_by_entity_type(self, etype: str) -> list[ParsedNote]:
        """Get all notes of a specific inferred entity type."""
        return [n for n in self.notes.values() if n.entity_type_guess == etype]
    
    def orphaned_notes(self) -> list[ParsedNote]:
        """Notes with no incoming or outgoing wikilinks."""
        linked = set()
        for sources in self.link_graph.values():
            for s in sources:
                linked.add(s)
        for targets in self.backlink_graph.values():
            for t in targets:
                linked.add(t)
        
        return [n for n in self.notes.values() 
                if n.rel_path not in linked and n.rel_path not in self.link_graph]
    
    def most_linked(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Return the most-linked-to notes (hubs)."""
        incoming = defaultdict(int)
        for source, targets in self.backlink_graph.items():
            incoming[source] = len(targets)
        return sorted(incoming.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    def notes_with_callouts(self) -> list[ParsedNote]:
        """Notes that contain callout blocks."""
        return [n for n in self.notes.values() if n.callouts]
    
    def notes_with_dataview(self) -> list[ParsedNote]:
        """Notes that use Dataview queries."""
        return [n for n in self.notes.values() if n.dataview_queries]
    
    def notes_with_tables(self) -> list[ParsedNote]:
        """Notes that contain markdown tables."""
        return [n for n in self.notes.values() if n.tables]
    
    def search_body(self, pattern: str, case_sensitive: bool = False) -> list[tuple[ParsedNote, int, str]]:
        """Search note bodies with regex. Returns (note, line_number, line_text)."""
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
        
        for note in self.notes.values():
            for i, line in enumerate(note.body.splitlines(), 1):
                if compiled.search(line):
                    results.append((note, i, line.strip()))
        
        return results
    
    # ── EXPORT ────────────────────────────────
    
    def export_report(self) -> dict:
        """Generate a comprehensive vault analysis report."""
        total_words = sum(n.body_word_count for n in self.notes.values())
        total_links = sum(len(n.wikilinks) for n in self.notes.values())
        total_backlinks = sum(len(v) for v in self.backlink_graph.values())
        
        return {
            "summary": {
                "total_notes": len(self.notes),
                "total_files_size_kb": round(sum(n.file_size for n in self.notes.values()) / 1024, 1),
                "total_words": total_words,
                "total_wikilinks": total_links,
                "total_backlinks": total_backlinks,
                "parse_errors": len(self.parse_errors),
                "daily_notes": len(self.daily_notes),
            },
            "by_directory": dict(sorted(
                {d: len(notes) for d, notes in self._note_directory_index.items()}.items(),
                key=lambda x: x[1], reverse=True
            )),
            "entity_type_distribution": {
                k: len(v) for k, v in sorted(self.entity_index.items(), key=lambda x: x[1], reverse=True)
            },
            "top_tags": sorted(
                [(tag, len(notes)) for tag, notes in self.tag_index.items()],
                key=lambda x: x[1],
                reverse=True
            )[:30],
            "most_linked_hubs": self.most_linked(10),
            "orphaned_note_count": len(self.orphaned_notes()),
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
            "total_notes": len(self.notes),
            "notes": {
                rel: {
                    "frontmatter": n.frontmatter,
                    "word_count": n.body_word_count,
                    "headings_count": len(n.headings),
                    "wikilinks": [l.target for l in n.wikilinks],
                    "tags": [t.tag for t in n.tags],
                    "entity_type": n.entity_type_guess,
                    "confidence": round(n.confidence_score, 2),
                    "has_callouts": len(n.callouts) > 0,
                    "has_tables": len(n.tables) > 0,
                    "has_dataview": len(n.dataview_queries) > 0,
                    "code_block_languages": list(set(cb.get("lang", "") for cb in n.code_blocks)),
                }
                for rel, n in self.notes.items()
            },
            "link_graph": dict(self.link_graph),
            "backlink_graph": dict(self.backlink_graph),
            "tag_index": dict(self.tag_index),
            "entity_index": dict(self.entity_index),
            "parse_errors": self.parse_errors,
        }
        
        json_str = json.dumps(data, indent=2, default=str)
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(json_str)
        
        return json_str


# ──────────────────────────────────────────────
# CLI INTERFACE
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "/home/darthvader/Documents/Obsidian/Skills-Vault"
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    parser = VaultParser(vault_path)
    count = parser.scan()
    
    print(f"Vault: {vault_path}")
    print(f"Notes parsed: {count}")
    print(f"Parse errors: {len(parser.parse_errors)}")
    print()
    
    report = parser.export_report()
    
    print("=== VAULT SUMMARY ===")
    for k, v in report['summary'].items():
        print(f"  {k}: {v}")
    
    print(f"\n=== ENTITY TYPES ===")
    for etype, count in report['entity_type_distribution'].items():
        print(f"  {etype}: {count}")
    
    print(f"\n=== TOP TAGS (20) ===")
    for tag, count in report['top_tags'][:20]:
        print(f"  #{tag}: {count}")
    
    print(f"\n=== MOST LINKED HUBS ===")
    for note_rel, count in report['most_linked_hubs']:
        print(f"  ({count} backlinks) {note_rel}")
    
    print(f"\n=== ORPHANED NOTES ===")
    orphans = parser.orphaned_notes()
    print(f"  Count: {len(orphans)}")
    for o in orphans[:10]:
        print(f"  {o.rel_path}")
    
    if output_path:
        parser.export_json(output_path)
        print(f"\nJSON index written to: {output_path}")
