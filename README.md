# VESTRIK // VAULT

> Structured Knowledge Intelligence for AI agents.
>
> **Deterministic analysis first. Agent reasoning second.**

**Version:** 3.0.0 · **License:** MIT · **Python:** 3.11+

[![Tests](https://github.com/microhustlestack/cerebro-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/microhustlestack/cerebro-skill/actions/workflows/tests.yml)

VESTRIK // VAULT scans structured markdown knowledge, scores strategic importance, detects urgency, maps
relationships and surfaces structural gaps that an agent can reason over. Findings are derived from links,
tags and frontmatter rather than guessed from prose.

## What exists today

- unresolved entities
- implicit connections
- second-degree relationships
- bottlenecks
- thin coverage
- entity cataloging
- relationship matrices
- urgency detection
- strategic scoring
- Markdown and JSON intelligence reports

These are **VAULT capabilities**, not separate product modules.

## Install

```bash
git clone https://github.com/microhustlestack/cerebro-skill.git
cd cerebro-skill
bash install.sh
```

The repository retains its current GitHub name during the migration. The canonical package and CLI are VESTRIK:

```bash
vestrik ~/Documents/Obsidian/my-vault --gaps --report vestrik_report.md
vestrik ~/vault output/vault-index.json --gaps --quiet
vestrik ~/vault --quiet --report -
```

## Python API

```python
from vestrik import VaultParser

vault = VaultParser("/path/to/vault")
vault.scan()
print(vault.export_vestrik_report(query="funding gaps", top_n=15))
vault.export_json("output/vault-index.json")
```

## Agent Skill

`SKILL.md` defines **VESTRIK // VAULT** as an Agent Skill. The installer deploys to VESTRIK-native paths such as
`~/.claude/skills/vestrik/`.

## Compatibility during migration

This PR intentionally separates the rebrand from refactoring. Existing `cerebro` imports, the `cerebro` CLI,
and the legacy skill directory remain available as a temporary compatibility bridge for current users and forks.
New integrations should use `vestrik`.

No scoring, parsing, graph analysis, urgency logic or gap-analysis behavior is intentionally changed by this rebrand.

## Architecture boundary

VESTRIK is the system identity. VAULT is the only named capability/product surface currently being branded.
Future modules should exist only when they introduce a genuinely distinct data source, computational domain or
operational responsibility that VAULT cannot reasonably own.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

CI runs on Python 3.11, 3.12 and 3.13.

## License

MIT. See [LICENSE](LICENSE).

Built by J'Juan Wilson Jr. / Micro Hustle Stack.
