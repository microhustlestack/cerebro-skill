"""
Tests for VaultParser 2.0

Covers: parsing, link graph, backlink graph, tag index, entity index,
directory index, orphan detection, urgency detection, scoring model,
CEREBRO report output, JSON export, and CLI argument handling.
"""

import json
import os
import sys
import tempfile
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from vault_parser import (
    VaultParser,
    ParsedNote,
    UrgencySignal,
    StrategicScore,
)


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture
def vault(tmp_path):
    """Build a synthetic vault and return a scanned VaultParser."""

    today = datetime.now().date()
    urgent_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    high_date = (today + timedelta(days=20)).strftime("%Y-%m-%d")
    past_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    files = {
        "grants/green-fund.md": textwrap.dedent(f"""\
            ---
            tags: [grant, environment, funding]
            deadline: {urgent_date}
            ---
            # Green Infrastructure Fund

            Apply by {urgent_date}. Funding up to $50,000.

            Connects to [[urban-garden]] and [[youth-program]].
        """),
        "grants/arts-fellowship.md": textwrap.dedent(f"""\
            ---
            tags: [grant, arts, funding]
            deadline: {high_date}
            ---
            # Arts Fellowship

            Deadline: {high_date}.

            See also [[youth-program]].
        """),
        "projects/urban-garden.md": textwrap.dedent("""\
            ---
            tags: [project, environment, community]
            ---
            # Urban Garden Initiative

            Community gardening project.

            | Phase | Timeline |
            |-------|----------|
            | Planning | Q1 |
            | Launch | Q2 |

            [[youth-program]] is a key partner.
        """),
        "projects/youth-program.md": textwrap.dedent("""\
            ---
            tags: [project, youth, community]
            ---
            # Youth Entrepreneurship Program

            Training program for young founders.

            > [!tip] Key insight
            > Connect to funding sources early.
        """),
        "orphan.md": textwrap.dedent("""\
            ---
            tags: [misc]
            ---
            # Orphaned Note

            This note has no wikilinks in or out.
        """),
        "past-deadline.md": textwrap.dedent(f"""\
            ---
            tags: [expired]
            deadline: {past_date}
            ---
            # Expired Grant

            This deadline has passed: {past_date}.
        """),
        "urgent-keyword.md": textwrap.dedent("""\
            # Action Required

            This is critical and urgent -- act immediately.
        """),
    }

    for rel_path, content in files.items():
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)

    vp = VaultParser(str(tmp_path))
    vp.scan()
    return vp


# ──────────────────────────────────────────────
# BASIC PARSING
# ──────────────────────────────────────────────

class TestParsing:
    def test_note_count(self, vault):
        assert len(vault.notes) == 7

    def test_parse_errors_empty(self, vault):
        assert vault.parse_errors == []

    def test_frontmatter_extracted(self, vault):
        note = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        assert note.has_frontmatter
        assert "grant" in [t.tag for t in note.tags]
        assert "environment" in [t.tag for t in note.tags]

    def test_body_word_count(self, vault):
        note = next(n for n in vault.notes.values() if "urban-garden" in n.filename)
        assert note.body_word_count > 0

    def test_headings_extracted(self, vault):
        note = next(n for n in vault.notes.values() if "urban-garden" in n.filename)
        assert len(note.headings) >= 1
        assert note.headings[0].level == 1

    def test_table_extracted(self, vault):
        note = next(n for n in vault.notes.values() if "urban-garden" in n.filename)
        assert len(note.tables) >= 1
        assert "Phase" in note.tables[0].headers

    def test_callout_extracted(self, vault):
        note = next(n for n in vault.notes.values() if "youth-program" in n.filename)
        assert len(note.callouts) >= 1
        assert note.callouts[0].callout_type == "tip"

    def test_empty_file_skipped(self, tmp_path):
        (tmp_path / "empty.md").write_text("   \n  ")
        vp = VaultParser(str(tmp_path))
        count = vp.scan()
        assert count == 0

    def test_utf8_errors_handled(self, tmp_path):
        bad = tmp_path / "bad.md"
        bad.write_bytes(b"# Title\n\xff\xfe invalid bytes\n")
        vp = VaultParser(str(tmp_path))
        count = vp.scan()
        assert count == 1


# ──────────────────────────────────────────────
# DIRECTORY INDEX
# ──────────────────────────────────────────────

class TestDirectoryIndex:
    def test_directories_populated(self, vault):
        assert len(vault._note_directory_index) > 0

    def test_grants_directory(self, vault):
        grants = vault._note_directory_index.get("grants", [])
        assert len(grants) == 2

    def test_projects_directory(self, vault):
        projects = vault._note_directory_index.get("projects", [])
        assert len(projects) == 2

    def test_root_directory(self, vault):
        root = vault._note_directory_index.get("", [])
        assert len(root) >= 2  # orphan.md, past-deadline.md, urgent-keyword.md


# ──────────────────────────────────────────────
# LINK GRAPH
# ──────────────────────────────────────────────

class TestLinkGraph:
    def test_outgoing_links_exist(self, vault):
        green = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        assert len(green.wikilinks) == 2

    def test_link_graph_populated(self, vault):
        green = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        assert green.rel_path in vault.link_graph

    def test_backlink_graph_populated(self, vault):
        youth = next(n for n in vault.notes.values() if "youth-program" in n.filename)
        backlinks = vault.backlink_graph.get(youth.rel_path, [])
        # green-fund, arts-fellowship, and urban-garden all link to youth-program
        assert len(backlinks) >= 2

    def test_filename_to_rel_cached(self, vault):
        assert len(vault._filename_to_rel) == len(vault.notes)


# ──────────────────────────────────────────────
# TAG INDEX
# ──────────────────────────────────────────────

class TestTagIndex:
    def test_tag_index_populated(self, vault):
        assert "grant" in vault.tag_index
        assert len(vault.tag_index["grant"]) == 2

    def test_community_tag(self, vault):
        assert len(vault.tag_index.get("community", [])) == 2

    def test_notes_by_tag(self, vault):
        results = vault.notes_by_tag("grant")
        assert len(results) == 2


# ──────────────────────────────────────────────
# ORPHAN DETECTION
# ──────────────────────────────────────────────

class TestOrphanDetection:
    def test_orphan_count(self, vault):
        orphans = vault.orphaned_notes()
        # orphan.md has no links in or out
        orphan_names = [o.filename for o in orphans]
        assert "orphan.md" in orphan_names

    def test_linked_notes_not_orphans(self, vault):
        orphans = {o.filename for o in vault.orphaned_notes()}
        assert "youth-program.md" not in orphans
        assert "urban-garden.md" not in orphans

    def test_orphan_uses_rel_paths(self, tmp_path):
        """Regression: orphan detection must compare rel_paths, not raw target names."""
        (tmp_path / "a.md").write_text("# A\n\n[[b]]\n")
        (tmp_path / "b.md").write_text("# B\n\nContent.\n")
        (tmp_path / "c.md").write_text("# C\n\nNo links.\n")
        vp = VaultParser(str(tmp_path))
        vp.scan()
        orphans = {o.filename for o in vp.orphaned_notes()}
        assert "c.md" in orphans
        assert "a.md" not in orphans
        assert "b.md" not in orphans


# ──────────────────────────────────────────────
# URGENCY DETECTION
# ──────────────────────────────────────────────

class TestUrgencyDetection:
    def test_urgent_frontmatter_deadline(self, vault):
        green = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        levels = [s.level for s in green.urgency_signals]
        assert "URGENT" in levels

    def test_high_frontmatter_deadline(self, vault):
        arts = next(n for n in vault.notes.values() if "arts-fellowship" in n.filename)
        levels = [s.level for s in arts.urgency_signals]
        assert "HIGH" in levels

    def test_past_deadline_flagged(self, vault):
        past = next(n for n in vault.notes.values() if "past-deadline" in n.filename)
        levels = [s.level for s in past.urgency_signals]
        assert "PAST" in levels

    def test_urgent_keyword_detected(self, vault):
        kw = next(n for n in vault.notes.values() if "urgent-keyword" in n.filename)
        levels = [s.level for s in kw.urgency_signals]
        assert "URGENT" in levels

    def test_signal_type_recorded(self, vault):
        green = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        types = [s.signal_type for s in green.urgency_signals]
        assert "frontmatter" in types

    def test_urgent_notes_query(self, vault):
        urgent = vault.urgent_notes()
        names = [n.filename for n in urgent]
        assert "green-fund.md" in names

    def test_high_notes_query(self, vault):
        high = vault.high_notes()
        names = [n.filename for n in high]
        assert "arts-fellowship.md" in names

    def test_high_notes_excludes_urgent(self, vault):
        urgent_names = {n.filename for n in vault.urgent_notes()}
        high_names = {n.filename for n in vault.high_notes()}
        assert urgent_names.isdisjoint(high_names)

    def test_no_false_urgency_on_clean_note(self, vault):
        urban = next(n for n in vault.notes.values() if "urban-garden" in n.filename)
        urgent_signals = [s for s in urban.urgency_signals if s.level == "URGENT"]
        assert len(urgent_signals) == 0


# ──────────────────────────────────────────────
# SCORING MODEL
# ──────────────────────────────────────────────

class TestScoringModel:
    def test_all_notes_scored(self, vault):
        for note in vault.notes.values():
            assert note.strategic_score is not None

    def test_composite_between_zero_and_one(self, vault):
        for note in vault.notes.values():
            assert 0.0 <= note.strategic_score.composite <= 1.0

    def test_score_dimensions_between_zero_and_one(self, vault):
        for note in vault.notes.values():
            s = note.strategic_score
            assert 0.0 <= s.connectivity <= 1.0
            assert 0.0 <= s.tag_influence <= 1.0
            assert 0.0 <= s.urgency <= 1.0
            assert 0.0 <= s.richness <= 1.0

    def test_urgent_note_has_nonzero_urgency_score(self, vault):
        green = next(n for n in vault.notes.values() if "green-fund" in n.filename)
        assert green.strategic_score.urgency > 0.0

    def test_orphan_has_zero_connectivity(self, vault):
        orphan = next(n for n in vault.notes.values() if n.filename == "orphan.md")
        assert orphan.strategic_score.connectivity == 0.0

    def test_well_linked_note_has_higher_connectivity(self, vault):
        youth = next(n for n in vault.notes.values() if "youth-program" in n.filename)
        orphan = next(n for n in vault.notes.values() if n.filename == "orphan.md")
        assert youth.strategic_score.connectivity > orphan.strategic_score.connectivity

    def test_top_scored_sorted_descending(self, vault):
        ranked = vault.top_scored(7)
        scores = [s.composite for _, s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_richness_with_table(self, vault):
        urban = next(n for n in vault.notes.values() if "urban-garden" in n.filename)
        assert urban.strategic_score.richness > 0.0


# ──────────────────────────────────────────────
# CEREBRO REPORT
# ──────────────────────────────────────────────

class TestCerebroReport:
    def test_report_contains_required_sections(self, vault):
        report = vault.export_cerebro_report()
        assert "CEREBRO INTELLIGENCE SCAN" in report
        assert "## Top Matches" in report
        assert "## Key Connections" in report
        assert "## Strategic Insight" in report
        assert "## Recommended Next Actions" in report

    def test_report_shows_entity_count(self, vault):
        report = vault.export_cerebro_report()
        assert "Entities analyzed: 7" in report

    def test_report_custom_query(self, vault):
        report = vault.export_cerebro_report(query="find grants")
        assert "Scan: find grants" in report

    def test_report_urgency_label_appears(self, vault):
        report = vault.export_cerebro_report()
        assert "[URGENT]" in report

    def test_report_footer_present(self, vault):
        report = vault.export_cerebro_report()
        assert "CEREBRO v2.0" in report

    def test_report_top_n_respected(self, vault):
        report = vault.export_cerebro_report(top_n=2)
        assert "Showing top 2" in report

    def test_report_second_degree_connections(self, vault):
        report = vault.export_cerebro_report()
        # green-fund -> youth-program -> (something)
        assert "->" in report

    def test_report_orphan_mentioned_in_actions(self, vault):
        report = vault.export_cerebro_report()
        assert "orphan" in report.lower()


# ──────────────────────────────────────────────
# JSON EXPORT
# ──────────────────────────────────────────────

class TestJsonExport:
    def test_export_json_returns_valid_json(self, vault):
        raw = vault.export_json()
        data = json.loads(raw)
        assert "notes" in data
        assert "link_graph" in data
        assert "tag_index" in data

    def test_export_json_includes_scores(self, vault):
        data = json.loads(vault.export_json())
        for rel, meta in data["notes"].items():
            assert "strategic_score" in meta
            assert meta["strategic_score"] is not None
            assert "composite" in meta["strategic_score"]

    def test_export_json_includes_urgency(self, vault):
        data = json.loads(vault.export_json())
        for rel, meta in data["notes"].items():
            assert "urgency_signals" in meta

    def test_export_json_writes_file(self, vault, tmp_path):
        out = tmp_path / "index.json"
        vault.export_json(str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["total_notes"] == 7

    def test_export_json_no_dir_component(self, vault, tmp_path):
        """Regression: export_json must not crash when output path has no directory."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            vault.export_json("flat-output.json")
            assert (tmp_path / "flat-output.json").exists()
        finally:
            os.chdir(original_dir)

    def test_export_json_cerebro_version(self, vault):
        data = json.loads(vault.export_json())
        assert data["cerebro_version"] == "2.0"


# ──────────────────────────────────────────────
# EXPORT REPORT DICT
# ──────────────────────────────────────────────

class TestExportReport:
    def test_summary_keys(self, vault):
        report = vault.export_report()
        expected = {"total_notes", "total_words", "urgent_notes", "high_notes", "orphaned_notes"}
        assert expected.issubset(report["summary"].keys())

    def test_by_directory_populated(self, vault):
        """Regression: _note_directory_index must be populated during scan."""
        report = vault.export_report()
        assert len(report["by_directory"]) > 0

    def test_top_scored_in_report(self, vault):
        report = vault.export_report()
        assert len(report["top_scored"]) > 0
        assert isinstance(report["top_scored"][0], tuple)

    def test_urgency_counts_in_summary(self, vault):
        report = vault.export_report()
        assert report["summary"]["urgent_notes"] >= 1
        assert report["summary"]["high_notes"] >= 1
        assert report["summary"]["orphaned_notes"] >= 1


# ──────────────────────────────────────────────
# QUERY METHODS
# ──────────────────────────────────────────────

class TestQueryMethods:
    def test_most_linked_sorted(self, vault):
        hubs = vault.most_linked(5)
        counts = [c for _, c in hubs]
        assert counts == sorted(counts, reverse=True)

    def test_notes_by_entity_type(self, vault):
        grants = vault.notes_by_entity_type("grant")
        # entity inference is heuristic; just confirm method runs
        assert isinstance(grants, list)

    def test_search_body(self, vault):
        results = vault.search_body("community")
        assert len(results) >= 1
        for note, line_num, text in results:
            assert isinstance(note, ParsedNote)
            assert "community" in text.lower()

    def test_notes_with_tables(self, vault):
        assert len(vault.notes_with_tables()) >= 1

    def test_notes_with_callouts(self, vault):
        assert len(vault.notes_with_callouts()) >= 1


# ──────────────────────────────────────────────
# EDGE CASES
# ──────────────────────────────────────────────

class TestEdgeCases:
    def test_skip_dirs_respected(self, tmp_path):
        (tmp_path / ".obsidian").mkdir()
        (tmp_path / ".obsidian" / "config.md").write_text("# Config\n")
        (tmp_path / "real.md").write_text("# Real\n")
        vp = VaultParser(str(tmp_path))
        count = vp.scan()
        assert count == 1

    def test_wikilink_with_display_text(self, tmp_path):
        (tmp_path / "a.md").write_text("[[b|Display Text]]\n")
        (tmp_path / "b.md").write_text("# B\n")
        vp = VaultParser(str(tmp_path))
        vp.scan()
        a = next(n for n in vp.notes.values() if "a.md" in n.filename)
        assert a.wikilinks[0].target == "b"
        assert a.wikilinks[0].display == "Display Text"

    def test_wikilink_heading_anchor_stripped(self, tmp_path):
        (tmp_path / "a.md").write_text("[[b#section|text]]\n")
        (tmp_path / "b.md").write_text("# B\n")
        vp = VaultParser(str(tmp_path))
        vp.scan()
        a = next(n for n in vp.notes.values() if "a.md" in n.filename)
        assert a.wikilinks[0].target == "b"

    def test_single_note_vault(self, tmp_path):
        (tmp_path / "solo.md").write_text("# Solo\n\nNo links.\n")
        vp = VaultParser(str(tmp_path))
        count = vp.scan()
        assert count == 1
        assert len(vp.orphaned_notes()) == 1

    def test_frontmatter_yaml_error_handled(self, tmp_path):
        (tmp_path / "bad.md").write_text("---\nbad: [unclosed\n---\n# Bad\n")
        vp = VaultParser(str(tmp_path))
        count = vp.scan()
        assert count == 1
        note = next(iter(vp.notes.values()))
        assert note.frontmatter.get("_parse_error") is True

    def test_no_duplicate_tags(self, tmp_path):
        (tmp_path / "a.md").write_text("---\ntags: [foo]\n---\n#foo inline\n")
        vp = VaultParser(str(tmp_path))
        vp.scan()
        note = next(iter(vp.notes.values()))
        tag_names = [t.tag for t in note.tags]
        assert len(tag_names) == len(set(tag_names))
