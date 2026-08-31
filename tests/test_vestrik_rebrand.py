import json

from vestrik import VaultParser, __version__
from vestrik.cli import build_arg_parser


def test_vestrik_namespace_is_canonical():
    assert VaultParser is not None
    assert __version__ == "3.0.0"


def test_vestrik_cli_identity():
    parser = build_arg_parser()
    assert parser.prog == "vestrik"


def test_vestrik_json_version_key(tmp_path):
    (tmp_path / "note.md").write_text("# Note\n#test", encoding="utf-8")
    vault = VaultParser(str(tmp_path))
    vault.scan()
    payload = json.loads(vault.export_json())
    assert payload["vestrik_version"] == __version__
    assert "cerebro_version" not in payload


def test_vestrik_report_brand(tmp_path):
    (tmp_path / "note.md").write_text("# Note\n#test", encoding="utf-8")
    vault = VaultParser(str(tmp_path))
    vault.scan()
    report = vault.export_vestrik_report()
    assert "VESTRIK INTELLIGENCE SCAN" in report
    assert "CEREBRO INTELLIGENCE SCAN" not in report
