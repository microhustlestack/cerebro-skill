# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## What This Is

This is the CEREBRO skill -- a strategic intelligence engine for markdown vaults.
It ships a SKILL.md definition (multi-platform agent instructions) and a Python parser
script that indexes Obsidian vaults into structured JSON with urgency detection and
strategic scoring.

## Repository Structure

```
cerebro-skill/
  SKILL.md              Agent skill definition (all platforms)
  CLAUDE.md             This file
  scripts/
    vault_parser.py     Vault indexing and intelligence engine
  output/               Runtime reports (git-ignored)
  README.md             Full documentation
```

## The Parser

`scripts/vault_parser.py` is the primary executable. It has no external dependencies
beyond PyYAML (Python 3.11+).

What it does:
- Parses every .md file in a vault directory
- Extracts frontmatter, wikilinks, backlinks, tags, callouts, tables, dataview queries, code blocks
- Builds a link graph, backlink graph, tag index, and entity index
- Detects urgency signals (keywords, ISO dates, frontmatter deadline fields)
- Scores every note on four dimensions: connectivity, tag influence, urgency, richness
- Outputs a JSON index and a ready-to-use CEREBRO INTELLIGENCE SCAN report

CLI:
```bash
python3 scripts/vault_parser.py <vault-dir>
python3 scripts/vault_parser.py <vault-dir> output/vault-index.json --report cerebro_report.md
python3 scripts/vault_parser.py <vault-dir> --query "grants" --top 15
```

## Key Classes

VaultParser    Main orchestrator. Call scan() then export methods.
ParsedNote     Complete representation of a single .md file.
UrgencySignal  A time-sensitivity signal (URGENT/HIGH/STANDARD/PAST).
StrategicScore Four-dimension score for a note (composite drives ranking).

## Scoring Model

Connectivity  35%  outgoing + 2x incoming wikilinks
Tag Influence 25%  vault-wide coverage of this note's tags
Urgency       25%  derived from urgency signal levels
Richness      15%  frontmatter, headings, word count, tables, callouts

## Modifying the Skill

Edit SKILL.md to change agent instructions.
Edit scripts/vault_parser.py to change parsing or scoring logic.

After editing, deploy by copying to the appropriate skills directory:
- Hermes: ~/.hermes/skills/research/cerebro/
- OpenClaw: ~/.openclaw/shared-skills/cerebro/
- Claude Code: ~/.claude/skills/cerebro/ or project root
- Skills-Vault (canonical source): ~/Documents/Obsidian/Skills-Vault/

## Testing the Parser

```bash
# Point at any directory with .md files
python3 scripts/vault_parser.py /path/to/vault

# With a small test vault
mkdir -p /tmp/test-vault
echo "# Test\n\nThis is [[linked note]].\n\nDeadline: 2026-05-01" > /tmp/test-vault/note-a.md
echo "# Linked Note\n\nContent here." > /tmp/test-vault/linked-note.md
python3 scripts/vault_parser.py /tmp/test-vault /tmp/test-index.json --report /tmp/cerebro.md
cat /tmp/cerebro.md
```

## No Build System

There is no build system, test suite, or package manager config.
This skill is purely a Python script + markdown definition.
