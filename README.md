# CEREBRO — Strategic Intelligence Engine

> Scan, score, and connect knowledge across a markdown vault.
> Think like a strategist, not a search engine.

**Version:** 3.0.0 · **License:** MIT · **Python:** 3.11+

[![Tests](https://github.com/microhustlestack/cerebro-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/microhustlestack/cerebro-skill/actions/workflows/tests.yml)

---

## What It Does

CEREBRO reads a structured markdown vault, scores every note on strategic
value, detects time-sensitive signals, maps relationships between entities,
and surfaces actionable intelligence — including connections you did not
know to look for.

It is not a search tool. Search answers "where is that?" CEREBRO answers
"what matters most right now, and what am I missing?"

| It finds | Meaning |
|----------|---------|
| **Unresolved entities** | You link to it repeatedly. You never wrote it down. |
| **Implicit connections** | Two notes share context and were never linked. |
| **Second-degree relationships** | A links to B, B links to C. CEREBRO surfaces A↔C. |
| **Bottlenecks** | One note that unrelated areas of work all depend on. |
| **Thin coverage** | A tag applied once — an intention, not a documented area. |
| **Urgency signals** | Deadlines and keywords classified URGENT / HIGH / STANDARD / PAST. |

### Findings are structural, not inferred

Every finding is derived from links, tags and frontmatter you actually
wrote. Nothing is guessed from prose statistics.

That constraint is the point. A tool that infers meaning from your writing
produces confident nonsense, and you cannot tell a real finding from a
fabricated one without re-reading every note — which defeats the purpose.
Every CEREBRO finding can be verified by opening two files.

---

## Install

```bash
git clone https://github.com/microhustlestack/cerebro-skill.git
cd cerebro-skill
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
cerebro --version
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` before
running `python -m pip install .`.

Or deploy as an agent skill at the same time:

```bash
bash install.sh              # package + Claude; detected Hermes/OpenClaw
bash install.sh package claude  # install the CLI and one skill target
```

Explicit targets are `package`, `claude`, `hermes`, and `openclaw`. Supplying
targets replaces the defaults, so include `package` when you also want the
`cerebro` command installed.

Dependencies: Python 3.11+ and PyYAML. Nothing else.

---

## Quick Start

```bash
# Full scan with gap analysis
cerebro ~/Documents/Obsidian/my-vault --gaps --report cerebro_report.md

# JSON index for an agent to reason over, gap findings included
cerebro ~/vault output/vault-index.json --gaps --quiet

# Report straight to stdout
cerebro ~/vault --quiet --report -
```

| Flag | Effect |
|------|--------|
| `--gaps` | Add unresolved entities, implicit connections, bottlenecks, and thin coverage to console, JSON, and Markdown report output |
| `--report FILE` | Write the CEREBRO report (`-` for stdout) |
| `--query TEXT` | Label the scan in the report header |
| `--top N` | Number of ranked notes (default 10) |
| `--quiet` | Suppress console summary; write files only |

---

## Use as an AI Agent Skill

`SKILL.md` at the repository root is an Agent Skill definition. Once
deployed, trigger it in natural language:

> "Run a CEREBRO scan on ~/Documents/Obsidian/my-vault"
> "What am I missing in my grant research notes?"
> "Show how 'zero-cost model' relates to 'model-fallback-protocol'"

| Platform | Install |
|----------|---------|
| **Claude Code** | `bash install.sh claude` → `~/.claude/skills/cerebro/` |
| **Hermes** | `bash install.sh package hermes` → `~/.hermes/skills/research/cerebro/` |
| **OpenClaw** | `bash install.sh openclaw` |
| **Opencode** | `opencode run` with `-f vault-index.json` |
| **Codex** | Run inside a git repo with `--full-auto` |

### Small vault vs. large vault

Under 50 files, point the agent at the vault and let it read directly —
semantic reasoning beats parsing at that scale.

Over 50 files, parse first and let the agent reason over the index:

```bash
cerebro /path/to/vault output/vault-index.json --report cerebro_report.md --gaps

opencode run 'You are CEREBRO. Analyze this index and report. Deepen the
strategic insight: compound opportunities, second-degree connections,
resource gaps.' -f output/vault-index.json -f cerebro_report.md
```

For "what am I missing" questions, always run `--gaps` regardless of size.
That analysis is structural, and an agent reading files one at a time will
not reliably reconstruct it.

---

## Scoring Model

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Connectivity | 35% | Outgoing wikilinks + 2× incoming backlinks |
| Tag Influence | 25% | How widely this note's tags appear across the vault |
| Urgency | 25% | URGENT=1.0, HIGH=0.6, STANDARD=0.2 |
| Richness | 15% | Frontmatter, headings, word count, tables, callouts |

The composite score is a starting signal, not a verdict. Semantic judgment
overrides it when warranted.

## Urgency Detection

**Keywords:** urgent, asap, immediately, critical, time-sensitive, overdue,
must act, priority, do not delay.

**Frontmatter fields:** deadline, due, due_date, submit_by, expires,
closes, apply_by.

ISO dates (`YYYY-MM-DD`) in body text are detected and classified by days
remaining: past → `PAST`, 0–7 → `URGENT`, 8–30 → `HIGH`, 31+ → `STANDARD`.

---

## Live Example

`samples/kepano-vault-report.md` was generated against a real public
Obsidian vault — [kepano/kepano-obsidian](https://github.com/kepano/kepano-obsidian),
103 notes, no manual editing, under two seconds.

What CEREBRO found:

- 49 of 103 notes (47%) were orphaned — the vault stored knowledge without connecting it
- Two notes covered the same decision framework from different angles and had never been linked
- The Evergreen framework, the vault's stated intellectual foundation, existed in three places that barely referenced each other
- A Kevin Kelly cluster shared a common source with zero explicit connections
- Only 3 notes had any incoming backlinks across the entire vault

---

## Python API

```python
from cerebro import VaultParser

vault = VaultParser("/path/to/vault")
vault.scan()

print(vault.export_cerebro_report(query="funding gaps", top_n=15))

# Gap analysis
for name, mentions, referrers in vault.unresolved_links(min_mentions=2):
    print(f"{name}: referenced {mentions}x, never documented")

for conn in vault.implicit_connections():
    a, b = conn["pair"]
    print(f"{a} <-> {b} — shares {conn['shared_tags']}")

for neck in vault.bottlenecks():
    print(f"{neck['rel_path']}: {neck['dependents']} dependents")

vault.export_json("output/vault-index.json")
```

| Method | Returns |
|--------|---------|
| `unresolved_links(min_mentions)` | Referenced but undocumented entities, ranked |
| `implicit_connections(top_n, min_shared_tags)` | Unlinked note pairs sharing context |
| `bottlenecks(min_dependents)` | Cross-directory shared constraints |
| `entity_catalog(min_mentions)` | Frequency catalog, documented flag |
| `thin_coverage(max_notes)` | Tags too sparse to constitute coverage |
| `gap_report()` | All of the above, JSON-serializable |
| `top_scored(n)`, `urgent_notes()`, `orphaned_notes()` | Ranking and triage |

---

## Repository Structure

```
cerebro-skill/
  SKILL.md                  Agent Skill definition
  CLAUDE.md                 Claude Code guidance
  CONTRIBUTING.md           Architecture + contribution rules
  install.sh                Package install + skill deploy
  pyproject.toml            Packaging, cerebro entrypoint
  src/cerebro/
    models.py               Dataclasses
    parser.py               VaultParser — walking, graphs, scoring
    analysis.py             Gaps, implicit connections, bottlenecks
    report.py               Markdown + JSON rendering
    cli.py                  Command-line interface
  scripts/
    vault_parser.py         Back-compat shim (2.x entry path)
    validate_skill.py       SKILL.md frontmatter validator
  tests/                    112 tests
  samples/                  Live example report
```

---

## Tests

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

112 tests covering parsing, link graph, orphan detection, urgency, scoring,
gap analysis, report output, JSON export, CLI behavior, and edge cases. CI
runs on Python 3.11, 3.12 and 3.13.

---

## Upgrading from 2.x

The legacy CLI path remains supported. `scripts/vault_parser.py` forwards to
the package and accepts the same arguments as the `cerebro` entrypoint.

To adopt the new entrypoint: `python3 -m pip install .`, then use `cerebro` in
place of `python3 scripts/vault_parser.py`.

To upgrade a source checkout, pull the desired release and rerun
`python3 -m pip install --upgrade .`. To uninstall, run
`python3 -m pip uninstall cerebro-skill`.

`cerebro-skill-v2` is superseded by this release and can be archived — its
specification is implemented here.

---

## License

MIT. See [LICENSE](LICENSE).

Built by J'Juan Wilson Jr. / Micro Hustle Stack —
strategic intelligence for purpose-driven systems and ventures.
