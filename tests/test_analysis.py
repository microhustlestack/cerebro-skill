"""
Tests for the CEREBRO analysis layer.

Covers gap analysis (unresolved links, thin coverage), the entity catalog,
implicit connection detection, bottleneck detection, the relationship
matrix, and the combined gap_report rollup.
"""

import textwrap

import pytest

from cerebro import VaultParser


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture
def analysis_vault(tmp_path):
    """Vault engineered to exercise every analysis path.

    Structure:
      - [[sponsor-network]] referenced 3x, never written  -> unresolved
      - [[one-off]] referenced 1x, never written          -> unresolved
      - shared-hub.md referenced from 3 dirs              -> bottleneck
      - sunset-series / juneteenth share 2 tags, no link  -> implicit
      - #archive appears once                             -> thin coverage
    """
    files = {
        "programs/sunset-series.md": textwrap.dedent("""\
            ---
            tags: [event, community, sponsorship]
            ---
            # Sunset Concert Series

            Backed by [[sponsor-network]]. Depends on [[shared-hub]].
        """),
        "programs/juneteenth.md": textwrap.dedent("""\
            ---
            tags: [event, community, sponsorship]
            ---
            # Taste of Juneteenth

            Backed by [[sponsor-network]]. See [[shared-hub]].
        """),
        "orgs/east-33.md": textwrap.dedent("""\
            ---
            tags: [partner, archive]
            ---
            # East 33

            Coordinates with [[sponsor-network]] and [[shared-hub]].
            Also mentions [[one-off]].
        """),
        "shared-hub.md": textwrap.dedent("""\
            ---
            tags: [infrastructure]
            ---
            # Shared Hub

            Central coordination note.
        """),
    }

    for rel, content in files.items():
        fpath = tmp_path / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")

    parser = VaultParser(str(tmp_path))
    parser.scan()
    return parser


# ──────────────────────────────────────────────
# GAP ANALYSIS
# ──────────────────────────────────────────────

def test_unresolved_links_finds_phantom_entities(analysis_vault):
    names = [name for name, _, _ in analysis_vault.unresolved_links()]
    assert "sponsor-network" in names
    assert "one-off" in names


def test_unresolved_links_excludes_documented_notes(analysis_vault):
    names = [name for name, _, _ in analysis_vault.unresolved_links()]
    assert "shared-hub" not in names


def test_unresolved_links_ranked_by_mention_count(analysis_vault):
    results = analysis_vault.unresolved_links()
    counts = [count for _, count, _ in results]
    assert counts == sorted(counts, reverse=True)
    top_name, top_count, referrers = results[0]
    assert top_name == "sponsor-network"
    assert top_count == 3
    assert len(referrers) == 3


def test_unresolved_links_respects_min_mentions(analysis_vault):
    names = [name for name, _, _ in analysis_vault.unresolved_links(min_mentions=2)]
    assert "sponsor-network" in names
    assert "one-off" not in names


def test_thin_coverage_finds_single_note_tags(analysis_vault):
    tags = [tag for tag, _ in analysis_vault.thin_coverage()]
    assert "archive" in tags
    assert "community" not in tags


def test_thin_coverage_returns_note_paths(analysis_vault):
    coverage = dict(analysis_vault.thin_coverage())
    assert coverage["archive"] == ["orgs/east-33.md"]


# ──────────────────────────────────────────────
# ENTITY CATALOG
# ──────────────────────────────────────────────

def test_entity_catalog_marks_documented_entities(analysis_vault):
    catalog = {e["name"]: e for e in analysis_vault.entity_catalog(min_mentions=1)}
    assert catalog["Shared Hub"]["documented"] is True
    assert catalog["Shared Hub"]["rel_path"] == "shared-hub.md"


def test_entity_catalog_marks_undocumented_entities(analysis_vault):
    catalog = {e["name"]: e for e in analysis_vault.entity_catalog(min_mentions=1)}
    assert catalog["sponsor-network"]["documented"] is False
    assert catalog["sponsor-network"]["rel_path"] is None


def test_entity_catalog_ranked_by_mentions(analysis_vault):
    catalog = analysis_vault.entity_catalog(min_mentions=1)
    mentions = [e["mentions"] for e in catalog]
    assert mentions == sorted(mentions, reverse=True)


def test_entity_catalog_records_sources(analysis_vault):
    catalog = {e["name"]: e for e in analysis_vault.entity_catalog(min_mentions=1)}
    assert "wikilink" in catalog["sponsor-network"]["sources"]
    assert "title" in catalog["Shared Hub"]["sources"]


def test_entity_catalog_min_mentions_filters(analysis_vault):
    assert all(e["mentions"] >= 3 for e in analysis_vault.entity_catalog(min_mentions=3))


# ──────────────────────────────────────────────
# IMPLICIT CONNECTIONS
# ──────────────────────────────────────────────

def test_implicit_connections_finds_unlinked_shared_context(analysis_vault):
    pairs = [c["pair"] for c in analysis_vault.implicit_connections()]
    expected = tuple(sorted(("programs/sunset-series.md", "programs/juneteenth.md")))
    assert expected in pairs


def test_implicit_connections_reports_shared_tags(analysis_vault):
    result = next(
        c for c in analysis_vault.implicit_connections()
        if "programs/juneteenth.md" in c["pair"]
    )
    assert "sponsorship" in result["shared_tags"]
    assert result["shared"] >= 2


def test_implicit_connections_excludes_already_linked(analysis_vault):
    """Notes joined by a wikilink are an explicit relationship, not a finding."""
    linked = analysis_vault._linked_pairs()
    pairs = {c["pair"] for c in analysis_vault.implicit_connections()}
    assert not (pairs & linked)


def test_implicit_connections_respects_min_shared_tags(analysis_vault):
    assert analysis_vault.implicit_connections(min_shared_tags=99) == []


def test_implicit_connections_empty_on_tiny_vault(tmp_path):
    (tmp_path / "solo.md").write_text("# Solo\n\nOnly note.\n", encoding="utf-8")
    parser = VaultParser(str(tmp_path))
    parser.scan()
    assert parser.implicit_connections() == []


# ──────────────────────────────────────────────
# BOTTLENECKS + MATRIX
# ──────────────────────────────────────────────

def test_bottlenecks_finds_cross_directory_dependency(analysis_vault):
    paths = [b["rel_path"] for b in analysis_vault.bottlenecks()]
    assert "shared-hub.md" in paths


def test_bottlenecks_reports_dependent_count_and_dirs(analysis_vault):
    hub = next(b for b in analysis_vault.bottlenecks() if b["rel_path"] == "shared-hub.md")
    assert hub["dependents"] == 3
    assert len(hub["directories"]) >= 2


def test_bottlenecks_respects_min_dependents(analysis_vault):
    assert analysis_vault.bottlenecks(min_dependents=99) == []


def test_relationship_matrix_shape(analysis_vault):
    matrix = analysis_vault.relationship_matrix(top_n=4)
    assert len(matrix["notes"]) <= 4
    assert set(matrix["edges"]) == set(matrix["notes"])


def test_relationship_matrix_edges_stay_in_scope(analysis_vault):
    matrix = analysis_vault.relationship_matrix(top_n=3)
    scope = set(matrix["notes"])
    for targets in matrix["edges"].values():
        assert set(targets) <= scope


# ──────────────────────────────────────────────
# ROLLUP
# ──────────────────────────────────────────────

def test_gap_report_contains_all_sections(analysis_vault):
    report = analysis_vault.gap_report()
    for key in (
        "unresolved_links",
        "thin_coverage",
        "entity_catalog",
        "implicit_connections",
        "bottlenecks",
        "relationship_matrix",
    ):
        assert key in report


def test_gap_report_is_json_serializable(analysis_vault):
    import json
    json.dumps(analysis_vault.gap_report())


def test_gap_report_on_empty_vault(tmp_path):
    parser = VaultParser(str(tmp_path))
    parser.scan()
    report = parser.gap_report()
    assert report["unresolved_links"] == []
    assert report["entity_catalog"] == []
