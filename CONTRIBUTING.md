# Contributing to CEREBRO

## Setup

```bash
git clone https://github.com/microhustlestack/cerebro-skill.git
cd cerebro-skill
pip install -e ".[dev]"
pytest
```

All 107 tests should pass in under a second. If they don't, stop and fix
that before writing anything new.

## Architecture

```
src/cerebro/
  models.py     Dataclasses. No logic — safe to import anywhere.
  parser.py     VaultParser: walks the vault, builds graphs, scores notes.
  analysis.py   AnalysisMixin: derived intelligence (gaps, connections).
  report.py     ReportMixin: rendering to markdown and JSON.
  cli.py        Argument parsing and console output.
```

`analysis.py` and `report.py` are mixed into `VaultParser`, so everything
is reachable from one object while the source stays separated by
responsibility. Add derived findings to `analysis.py`, not `parser.py`.

## The one rule that matters

**Findings must be structural.** Every analysis method reasons over links,
tags and frontmatter the author actually wrote. Nothing infers meaning from
prose statistics.

This is deliberate. A tool that guesses at meaning produces confident
nonsense, and a user cannot tell a real finding from a hallucinated one
without re-reading every note — which defeats the purpose. If a finding
can't be traced back to something explicit in the vault, it doesn't ship.

When you add a finding, ask: can the user verify this by opening two files?
If not, reconsider.

## Tests

Every new analysis method needs tests for:

- the positive case (it finds what it should)
- the negative case (it excludes what it shouldn't)
- an empty or single-note vault (no crash, empty result)
- any threshold parameter, at both extremes

Build fixtures as real files in `tmp_path`. Don't mock the filesystem — the
parser's job is reading files, and mocking that tests nothing.

## Useful contributions

Testing against diverse vault structures is genuinely the highest-value
thing. The parser has been exercised against a handful of vaults; every new
one tends to surface a convention nobody anticipated.

Also welcome: new entity types or relationship patterns, report formatting
that reads better, and gap findings CEREBRO *should* have caught on your
vault but missed. The last one is the most useful bug report you can file.

## Style

Match what's there. Standard library plus PyYAML — think hard before adding
a dependency to something people install into an agent runtime.
