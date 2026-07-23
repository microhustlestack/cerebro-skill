"""
Tests for the CEREBRO command-line interface.

Covers argument parsing, exit codes, file outputs, and the --gaps payload.
"""

import json
import textwrap

import pytest

from cerebro import __version__
from cerebro.cli import build_arg_parser, main


@pytest.fixture
def vault_dir(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "alpha.md").write_text(
        textwrap.dedent("""\
            ---
            tags: [project, active]
            ---
            # Alpha

            Depends on [[missing-thing]] and [[beta]].
        """),
        encoding="utf-8",
    )
    (tmp_path / "notes" / "beta.md").write_text(
        textwrap.dedent("""\
            ---
            tags: [project, active]
            ---
            # Beta

            Standalone note.
        """),
        encoding="utf-8",
    )
    return tmp_path


# ── ARGUMENT PARSING ──────────────────────────

def test_parser_defaults():
    args = build_arg_parser().parse_args(["/some/vault"])
    assert args.vault == "/some/vault"
    assert args.top == 10
    assert args.gaps is False
    assert args.quiet is False


def test_parser_accepts_all_flags():
    args = build_arg_parser().parse_args(
        ["/v", "out.json", "--report", "r.md", "--query", "q", "--top", "3", "--gaps", "--quiet"]
    )
    assert args.output == "out.json"
    assert args.report == "r.md"
    assert args.query == "q"
    assert args.top == 3
    assert args.gaps is True
    assert args.quiet is True


def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        build_arg_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


# ── EXIT CODES ────────────────────────────────

def test_missing_vault_returns_2(tmp_path, capsys):
    assert main([str(tmp_path / "nope"), "--quiet"]) == 2
    assert "not found" in capsys.readouterr().err


def test_successful_scan_returns_0(vault_dir):
    assert main([str(vault_dir), "--quiet"]) == 0


def test_empty_vault_warns_but_succeeds(tmp_path, capsys):
    assert main([str(tmp_path), "--quiet"]) == 0
    assert "no markdown files" in capsys.readouterr().err


# ── OUTPUT ────────────────────────────────────

def test_quiet_suppresses_summary(vault_dir, capsys):
    main([str(vault_dir), "--quiet"])
    assert capsys.readouterr().out == ""


def test_summary_printed_by_default(vault_dir, capsys):
    main([str(vault_dir)])
    assert "VAULT SUMMARY" in capsys.readouterr().out


def test_report_written_to_file(vault_dir, tmp_path):
    out = tmp_path / "report.md"
    main([str(vault_dir), "--quiet", "--report", str(out)])
    assert "CEREBRO INTELLIGENCE SCAN" in out.read_text(encoding="utf-8")


def test_report_dash_goes_to_stdout(vault_dir, capsys):
    main([str(vault_dir), "--quiet", "--report", "-"])
    assert "CEREBRO INTELLIGENCE SCAN" in capsys.readouterr().out


def test_json_index_written(vault_dir, tmp_path):
    out = tmp_path / "index.json"
    main([str(vault_dir), str(out), "--quiet"])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_notes"] == 2
    assert data["cerebro_version"] == __version__


def test_gaps_flag_adds_gap_analysis_to_index(vault_dir, tmp_path):
    out = tmp_path / "index.json"
    main([str(vault_dir), str(out), "--quiet", "--gaps"])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "gap_analysis" in data
    names = [u["name"] for u in data["gap_analysis"]["unresolved_links"]]
    assert "missing-thing" in names


def test_index_without_gaps_flag_omits_gap_analysis(vault_dir, tmp_path):
    out = tmp_path / "index.json"
    main([str(vault_dir), str(out), "--quiet"])
    assert "gap_analysis" not in json.loads(out.read_text(encoding="utf-8"))


def test_gaps_printed_to_console(vault_dir, capsys):
    main([str(vault_dir), "--gaps"])
    assert "UNRESOLVED ENTITIES" in capsys.readouterr().out
