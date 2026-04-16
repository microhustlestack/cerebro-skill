# Changelog

All notable changes to cerebro-skill are documented here.

---

## [2.0.0] — 2026-04-16

### Added

Strategic scoring model. Every note is scored on four dimensions: connectivity (35%), tag influence (25%), urgency (25%), and content richness (15%). Composite score drives Top Matches ranking.

Urgency detection. VaultParser now scans every note for urgency keywords (urgent, asap, critical, overdue, etc.), ISO dates in body text, and frontmatter deadline fields (deadline, due, due_date, submit_by, expires, closes, apply_by). Each signal is classified as URGENT (0-7 days), HIGH (8-30 days), STANDARD (31+ days), or PAST.

`export_cerebro_report()`. Parser now produces a ready-to-use CEREBRO INTELLIGENCE SCAN report directly — Top Matches, Key Connections, Strategic Insight, Recommended Next Actions. No agent required for the base report.

`top_scored()`, `urgent_notes()`, `high_notes()` query methods.

`argparse` CLI with `--report`, `--query`, `--top` flags.

`UrgencySignal` and `StrategicScore` dataclasses.

`install.sh` — one-command deploy to Hermes, OpenClaw, or Claude Code.

`requirements.txt` and `requirements-dev.txt`.

Full test suite — 69 tests across parsing, link graph, orphan detection, urgency, scoring, CEREBRO report, JSON export, and edge cases.

GitHub Actions CI on Python 3.11 and 3.12.

`_filename_to_rel` cache — eliminates O(n³) traversal in second-degree connection mapping.

### Fixed

`_note_directory_index` was initialized but never populated. The `by_directory` field in `export_report()` was always empty. Fixed by populating the index during `scan()`.

`orphaned_notes()` compared rel_paths against raw wikilink target names (not resolved paths), making orphan detection unreliable. Fixed to use resolved rel_paths throughout via the backlink graph.

`export_json()` crashed with `FileNotFoundError` when the output path had no directory component (e.g., `output.json`). Fixed with a guard on `os.path.dirname` before calling `makedirs`.

Hardcoded `/home/darthvader/...` default path removed from CLI.

`CLAUDE.md` described a `cerebro` binary that does not exist. Rewritten to accurately describe `vault_parser.py` and the actual repo structure.

### Changed

`SKILL.md` paths changed from hardcoded `~/.hermes/skills/research/cerebro/` to portable `$CEREBRO_SKILL_DIR` convention with a platform resolution table.

CLI migrated from `sys.argv` to `argparse`.

`_build_link_graph` now stores `_filename_to_rel` as an instance variable for O(1) reuse.

`.gitignore` updated to exclude `.claude/`, Python cache files, and pytest artifacts.

---

## [1.1.0] — 2026-04-15

Initial public release. SKILL.md definition for Hermes, Claude Code, OpenClaw, Opencode, and Codex. `vault_parser.py` parsing frontmatter, wikilinks, backlinks, tags, callouts, tables, dataview queries, code blocks, and embedded files. Link graph and backlink graph. Tag index and entity index. Orphan detection. JSON export. CLI interface.
