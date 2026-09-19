"""
CEREBRO report generation.

Rendering is separated from parsing: `ReportMixin` holds every method that
turns an indexed vault into human- or machine-readable output. VaultParser
mixes this in, so `parser.export_cerebro_report()` still works unchanged.
"""

import os
import json
from datetime import datetime, date
from collections import defaultdict

from . import __version__


class ReportMixin:
    """Output rendering for VaultParser. Not usable standalone."""

    def export_cerebro_report(
        self, query: str = None, top_n: int = 10, include_gaps: bool = False
    ) -> str:
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

        if include_gaps:
            lines.append("## Gaps")
            gap_data = self.gap_report()

            unresolved = gap_data["unresolved_links"]
            lines.append("### Unresolved Entities")
            if unresolved:
                for item in unresolved[:10]:
                    lines.append(f"- {item['name']} ({item['mentions']} references)")
            else:
                lines.append("- None detected.")
            lines.append("")

            implicit = gap_data["implicit_connections"]
            lines.append("### Implicit Connections")
            if implicit:
                for item in implicit[:10]:
                    a, b = item["pair"]
                    tags = ", ".join(f"#{tag}" for tag in item["shared_tags"])
                    lines.append(f"- {a} <-> {b} — shared context: {tags}")
            else:
                lines.append("- None detected.")
            lines.append("")

            bottlenecks = gap_data["bottlenecks"]
            lines.append("### Bottlenecks")
            if bottlenecks:
                for item in bottlenecks[:10]:
                    lines.append(
                        f"- {item['rel_path']} ({item['dependents']} dependents)"
                    )
            else:
                lines.append("- None detected.")
            lines.append("")

            thin = gap_data["thin_coverage"]
            lines.append("### Thin Coverage")
            if thin:
                lines.append("- " + ", ".join(f"#{item['tag']}" for item in thin[:20]))
            else:
                lines.append("- None detected.")
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
        lines.append(f"CEREBRO v{__version__} | {today_str} | cerebro")

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
            "cerebro_version": __version__,
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
