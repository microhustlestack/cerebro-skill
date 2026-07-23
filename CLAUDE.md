# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

CEREBRO is a strategic intelligence engine for markdown vaults. It parses
an Obsidian-style vault, scores notes, detects urgency, and surfaces
structural gaps and connections.

It ships as both a Python package and an Agent Skill (`SKILL.md` at root).

## Commands

```bash
pip install -e ".[dev]"      # setup
pytest                       # 107 tests, sub-second
python3 scripts/validate_skill.py SKILL.md

cerebro /path/to/vault --gaps --report cerebro_report.md
cerebro /path/to/vault out.json --gaps --quiet
```

## Layout

```
src/cerebro/
  models.py     dataclasses only
  parser.py     VaultParser — file walking, graphs, scoring
  analysis.py   AnalysisMixin — gaps, implicit connections, bottlenecks
  report.py     ReportMixin — markdown + JSON rendering
  cli.py        argparse entrypoint
scripts/
  vault_parser.py     back-compat shim, forwards to the package
  validate_skill.py   SKILL.md frontmatter validator (runs in CI)
```

`VaultParser(ReportMixin, AnalysisMixin)` — one object, separated sources.

## Conventions

Analysis findings must be structural: derived from links, tags and
frontmatter the author wrote. Do not add findings inferred from prose
statistics; an unverifiable finding is worse than no finding.

Version lives in `src/cerebro/__init__.py` and nowhere else. `pyproject.toml`
and the JSON export both read from it.

`scripts/vault_parser.py` is a compatibility shim. Existing installs call
that path — don't delete it, and don't add logic to it.
