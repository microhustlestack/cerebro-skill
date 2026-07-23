"""
CEREBRO derived intelligence.

The parser answers "what is in the vault." This layer answers the questions
the vault does not answer about itself: what is referenced but missing, what
is thin, what co-occurs without ever being linked, and what everything
depends on.

Every method here is structural — it reasons over links, tags and frontmatter
the author actually wrote. Nothing is inferred from prose statistics, so
findings are checkable rather than plausible.

Mixed into VaultParser; not usable standalone.
"""

from collections import Counter, defaultdict
from itertools import combinations


class AnalysisMixin:
    """Derived intelligence for VaultParser."""

    # ── GAP ANALYSIS ──────────────────────────

    def unresolved_links(self, min_mentions: int = 1) -> list[tuple[str, int, list[str]]]:
        """Entities the vault references but never documents.

        A wikilink target with no matching note is a phantom entity: the
        author treats it as a real thing, links to it repeatedly, and never
        writes it down. High mention counts mark the most expensive gaps.

        Returns (target_name, mention_count, referring_rel_paths), ranked by
        mention count descending.
        """
        mentions: dict[str, set[str]] = defaultdict(set)
        display: dict[str, str] = {}

        for rel_path, targets in self.link_graph.items():
            for target in targets:
                norm = self._normalize_filename(target)
                if not norm or norm in self._filename_to_rel:
                    continue
                mentions[norm].add(rel_path)
                display.setdefault(norm, target)

        results = [
            (display[norm], len(refs), sorted(refs))
            for norm, refs in mentions.items()
            if len(refs) >= min_mentions
        ]
        results.sort(key=lambda r: (-r[1], r[0].lower()))
        return results

    def thin_coverage(self, max_notes: int = 1) -> list[tuple[str, list[str]]]:
        """Tags carrying too few notes to constitute real coverage.

        A tag applied once is a stated intention, not a documented area.
        Returns (tag, rel_paths) ranked alphabetically.
        """
        return sorted(
            ((tag, sorted(rels)) for tag, rels in self.tag_index.items()
             if len(rels) <= max_notes),
            key=lambda t: t[0].lower(),
        )

    # ── ENTITY CATALOG ────────────────────────

    def entity_catalog(self, min_mentions: int = 2) -> list[dict]:
        """Frequency catalog of everything the vault explicitly names.

        Counts structural mentions only — wikilink targets, tags, and note
        titles — rather than guessing at proper nouns in prose. An entity
        that is named structurally is one the author chose to name.

        Returns dicts with name, mentions, documented (bool), rel_path,
        and sources (which channels named it).
        """
        counts: Counter = Counter()
        sources: dict[str, set[str]] = defaultdict(set)
        display: dict[str, str] = {}

        def record(raw: str, channel: str, weight: int = 1, display_as: str = None):
            # Always key on the normalized filename stem so catalog entries
            # line up with _filename_to_rel; display separately, because the
            # human-readable label and the resolution key differ.
            norm = self._normalize_filename(raw)
            if not norm:
                return
            counts[norm] += weight
            sources[norm].add(channel)
            display.setdefault(norm, display_as or raw)

        for note in self.notes.values():
            stem = note.filename.replace('.md', '')
            heading = next((h.text for h in note.headings if h.level == 1), None)
            record(stem, 'title', display_as=heading or stem)

        for targets in self.link_graph.values():
            for target in targets:
                record(target, 'wikilink')

        for tag, rels in self.tag_index.items():
            record(tag, 'tag', weight=len(rels))

        catalog = []
        for norm, count in counts.items():
            if count < min_mentions:
                continue
            rel = self._filename_to_rel.get(norm)
            catalog.append({
                "name": display[norm],
                "mentions": count,
                "documented": rel is not None,
                "rel_path": rel,
                "sources": sorted(sources[norm]),
            })

        catalog.sort(key=lambda e: (-e["mentions"], e["name"].lower()))
        return catalog

    # ── IMPLICIT CONNECTIONS ──────────────────

    def implicit_connections(
        self,
        top_n: int = 10,
        min_shared_tags: int = 2,
        ubiquity_cutoff: float = 0.4,
    ) -> list[dict]:
        """Note pairs that share context but were never linked.

        Two notes carrying the same tags are about the same thing. If the
        author never wikilinked them, the relationship exists in their head
        but not in the vault — which means it cannot be traversed, and gets
        forgotten.

        Tags appearing on more than `ubiquity_cutoff` of the vault are
        skipped: a tag on everything discriminates nothing.

        Returns dicts with pair, shared_tags, and shared count.
        """
        total = len(self.notes)
        if total < 2:
            return []

        ceiling = max(2, int(total * ubiquity_cutoff))
        pair_tags: dict[tuple[str, str], set[str]] = defaultdict(set)

        for tag, rels in self.tag_index.items():
            unique = sorted(set(rels))
            if len(unique) < 2 or len(unique) > ceiling:
                continue
            for a, b in combinations(unique, 2):
                pair_tags[(a, b)].add(tag)

        linked = self._linked_pairs()
        results = []
        for (a, b), tags in pair_tags.items():
            if len(tags) < min_shared_tags:
                continue
            if (a, b) in linked:
                continue
            results.append({
                "pair": (a, b),
                "shared_tags": sorted(tags),
                "shared": len(tags),
            })

        results.sort(key=lambda r: (-r["shared"], r["pair"]))
        return results[:top_n]

    def _linked_pairs(self) -> set[tuple[str, str]]:
        """All rel_path pairs joined by a wikilink in either direction."""
        pairs: set[tuple[str, str]] = set()
        for source, targets in self.link_graph.items():
            for target in targets:
                target_rel = self._filename_to_rel.get(self._normalize_filename(target))
                if target_rel and target_rel != source:
                    pairs.add(tuple(sorted((source, target_rel))))
        return pairs

    # ── STRUCTURE ─────────────────────────────

    def relationship_matrix(self, top_n: int = 12) -> dict:
        """Adjacency view over the highest-scoring notes.

        Restricted to top_n so the matrix stays readable; a full vault
        adjacency matrix is data, not intelligence.
        """
        ranked = [note.rel_path for note, _ in self.top_scored(top_n)]
        index = set(ranked)
        matrix = {rel: [] for rel in ranked}

        for source in ranked:
            for target in self.link_graph.get(source, []):
                target_rel = self._filename_to_rel.get(self._normalize_filename(target))
                if target_rel in index and target_rel != source:
                    matrix[source].append(target_rel)

        return {"notes": ranked, "edges": {k: sorted(set(v)) for k, v in matrix.items()}}

    def bottlenecks(self, min_dependents: int = 3) -> list[dict]:
        """Notes many others depend on, spanning multiple directories.

        In-degree alone finds popular notes. Requiring dependents from more
        than one directory finds shared constraints — the note whose
        staleness quietly blocks unrelated areas of work.
        """
        results = []
        for rel_path, sources in self.backlink_graph.items():
            unique_sources = sorted(set(sources))
            if len(unique_sources) < min_dependents:
                continue
            directories = {s.rsplit('/', 1)[0] if '/' in s else '.' for s in unique_sources}
            if len(directories) < 2:
                continue
            results.append({
                "rel_path": rel_path,
                "dependents": len(unique_sources),
                "directories": sorted(directories),
                "referring": unique_sources,
            })

        results.sort(key=lambda r: (-r["dependents"], r["rel_path"]))
        return results

    # ── ROLLUP ────────────────────────────────

    def gap_report(self) -> dict:
        """Every derived finding in one structure, for JSON export."""
        return {
            "unresolved_links": [
                {"name": n, "mentions": c, "referenced_by": refs}
                for n, c, refs in self.unresolved_links(min_mentions=1)
            ],
            "thin_coverage": [
                {"tag": tag, "notes": rels} for tag, rels in self.thin_coverage()
            ],
            "entity_catalog": self.entity_catalog(),
            "implicit_connections": self.implicit_connections(),
            "bottlenecks": self.bottlenecks(),
            "relationship_matrix": self.relationship_matrix(),
        }
