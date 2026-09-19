# Changelog

All notable changes to cerebro-skill are documented here.

---

## [Unreleased]

### Fixed

- Removed the stale nested v1.1 skill bundle that conflicted with the root
  v3 skill definition and parser.
- Made `install.sh` work inside virtual environments and propagate package
  installation failures.
- Added gap findings to Markdown reports produced with `--gaps`.
- Create parent directories consistently for JSON and Markdown output.
- Report footers now use the package version instead of hardcoded v2.0.
- Corrected package metadata URLs and aligned install documentation.
- Updated GitHub Actions to Node 24-compatible action majors and made the
  skill validator's PyYAML dependency explicit.

### Tests

- Added coverage for the compatibility shim, nested output directories,
  gap-aware reports, version footers, and all discovered skill definitions.

---

## [3.0.0] — 2026-07-23

Consolidation release. Merges the `cerebro-skill-v2` specification into this
repository and implements the analysis features it described but never
shipped. `cerebro-skill-v2` is superseded and should be archived.

### Added

Gap analysis layer (`cerebro/analysis.py`). Five structural findings, all
derived from links and tags the author actually wrote — checkable rather
than inferred:

- `unresolved_links()` — wikilink targets with no note behind them, ranked
  by mention count. An entity referenced repeatedly and never documented is
  the most expensive gap in a vault.
- `implicit_connections()` — note pairs sharing two or more tags with no
  wikilink between them. Tags appearing on more than 40% of the vault are
  excluded, since a tag on everything discriminates nothing.
- `bottlenecks()` — notes depended on by several others across more than
  one directory. In-degree alone finds popular notes; the directory span
  requirement finds shared constraints.
- `entity_catalog()` — frequency catalog of everything the vault names via
  titles, wikilinks and tags, each flagged documented or not.
- `thin_coverage()` — tags carrying a single note, i.e. a stated intention
  rather than a documented area.
- `gap_report()` — all of the above as one JSON-serializable structure.

`LICENSE` file. The 2.x README claimed MIT while the repository shipped no
license text, leaving the actual terms unstated.

`scripts/validate_skill.py` — validates `SKILL.md` frontmatter in CI. A
malformed skill file fails silently: the agent never loads it and nothing
reports an error. This turns that into a build failure.

`pyproject.toml` with a `cerebro` console entrypoint, `[dev]` extra, and
version read from `cerebro.__version__`.

CLI flags `--gaps`, `--quiet`, `--version`, and `--report -` for stdout.

38 new tests covering the analysis layer and the CLI.

Python 3.13 added to the CI matrix; CI now also smoke-tests the installed
entrypoint.

### Changed

Restructured into a `src/` package. The 1,060-line `vault_parser.py` is
split by responsibility into `models.py`, `parser.py`, `analysis.py`,
`report.py` and `cli.py`. Reporting and analysis are mixins on
`VaultParser`, so the public object surface is unchanged and existing calls
such as `parser.export_cerebro_report()` still work.

All 69 tests from 2.0.0 pass unmodified against the restructured code, with
one exception noted under Fixed.

Thirteen hot-path regexes compiled once at module import rather than
re-resolved per line per file, and collected in one reviewable block.

`SKILL.md` frontmatter reduced to the Agent Skill spec keys (`name`,
`description`, `license`). The 2.x file carried `version`, `author` and a
`metadata.hermes` block that are not part of the spec. Trigger language was
expanded so gap-analysis phrasing ("what am I missing") routes correctly.

`install.sh` installs the package and its entrypoint rather than copying
loose files.

`requirements.txt` and `requirements-dev.txt` retained but now defer to
`pyproject.toml`.

### Fixed

`export_json()` hardcoded `"cerebro_version": "2.0"`, so an index produced
by any later build misreported the version that made it. Now read from
`cerebro.__version__`. The test asserting the literal `"2.0"` was retargeted
to the same source rather than deleted.

The CLI reported a mistyped vault path as a successful scan of an empty
vault, because `os.walk` returns silently on a nonexistent directory. Now
validated explicitly, exiting 2.

`cerebro vault | head` raised `BrokenPipeError` on exit. Handled, along with
`KeyboardInterrupt` (exit 130).

### Compatibility

`scripts/vault_parser.py` remains as a forwarding shim. Existing SKILL
files, shell snippets and installs that call that path keep working. Prefer
`pip install -e .` and the `cerebro` entrypoint.

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
