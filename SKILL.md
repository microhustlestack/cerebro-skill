---
name: cerebro
description: >
  Strategic intelligence engine for markdown vaults. Use this skill whenever the user asks to analyze a vault,
  scan notes for connections, surface relationships between entities, find hidden links, map a knowledge base,
  audit what a set of notes is missing, or generate an intelligence report from a folder of markdown files.
  Trigger on phrases like "scan my vault", "analyze my notes", "find connections in", "what am I missing in
  my notes", "what does my vault say about", "cerebro", or any request to reason across multiple markdown
  files as a system. Do not treat this as a plain search or file-reading task. Cerebro explicitly looks for
  what is not obvious: second-degree relationships, undocumented entities, thin coverage, bottlenecks, and
  compound opportunities. Always use this skill for multi-file markdown intelligence work.
license: MIT
---

# CEREBRO — Strategic Intelligence Engine

Read a markdown vault, score every note on strategic value, detect urgency,
map relationships between entities, and surface actionable intelligence —
including connections the user did not know to look for.

## Core Principle

Think like a strategist, not a search engine. Surface what the user cannot
see by reading their own notes. Prioritize clarity, relevance, and
actionable output over exhaustive listing.

A finding is only worth reporting if the user could not have gotten it by
opening a file and reading it.

## Choosing an Approach

| Situation | Approach |
|-----------|----------|
| 50+ files | Run the parser first, then reason semantically over its output |
| Under 50 files | Read files directly and reason — no script needed |
| Targeted question | Reason directly regardless of vault size |
| "What am I missing?" | Always run the parser with `--gaps` — this is structural, not semantic |

The parser is deterministic and fast. Semantic judgment is yours. Use the
parser for structure (links, tags, scores, gaps) and your own reasoning for
meaning. Never let the composite score override an obvious semantic truth.

## Running the Parser

```bash
# Installed entrypoint (preferred)
cerebro /path/to/vault --report cerebro_report.md --gaps

# Full output: JSON index + report + gap analysis
cerebro /path/to/vault output/vault-index.json \
  --report cerebro_report.md \
  --query "grant opportunities Q2" \
  --gaps --top 15

# Report to stdout, nothing else
cerebro /path/to/vault --quiet --report -

# Legacy path (still supported)
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault
```

`$CEREBRO_SKILL_DIR` is wherever this skill is installed. Requires Python
3.11+ and PyYAML. If `cerebro` is not on PATH, run `pip install -e .` from
the repo root, or fall back to the `scripts/vault_parser.py` path.

## Scoring Model

Every note is scored on four dimensions; the composite drives ranking.

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Connectivity | 35% | Outgoing wikilinks + 2x incoming backlinks |
| Tag Influence | 25% | How widely this note's tags appear across the vault |
| Urgency | 25% | URGENT=1.0, HIGH=0.6, STANDARD=0.2 |
| Richness | 15% | Frontmatter, headings, word count, tables, callouts |

The score is a starting signal, not a verdict. Say so when it conflicts
with what the content plainly means.

## Urgency Detection

Keywords: urgent, asap, immediately, critical, time-sensitive, overdue,
must act, priority, do not delay.

Frontmatter fields: deadline, due, due_date, submit_by, expires, closes,
apply_by. ISO dates (YYYY-MM-DD) in body text are detected too.

| Days Until | Level |
|------------|-------|
| Past | PAST |
| 0–7 | URGENT |
| 8–30 | HIGH |
| 31+ | STANDARD |

## Gap Analysis

Structural findings — checkable, not inferred. Run with `--gaps`.

**Unresolved entities.** Wikilink targets with no matching note. The author
links to it repeatedly and never wrote it down. Rank by mention count; a
thing referenced five times and never documented is the most expensive gap
in the vault.

**Thin coverage.** Tags applied to exactly one note — a stated intention,
not a documented area.

**Implicit connections.** Note pairs sharing two or more tags with no
wikilink between them. The relationship exists in the user's head but not
in the vault, so it cannot be traversed and gets forgotten.

**Bottlenecks.** Notes depended on by several others across more than one
directory — shared constraints whose staleness quietly blocks unrelated
work.

**Entity catalog.** Frequency count of everything the vault explicitly
names via titles, wikilinks and tags, flagged documented or not.

## Workflow

**1 — Inventory.** Map entity types, directory structure, naming
conventions, key frontmatter fields.

**2 — Parse** (large vaults). Build the JSON index and report. Use
`--gaps` whenever the user's question is about what is missing, weak, or
disconnected.

**3 — Read deeply.** Prioritize notes flagged URGENT or HIGH, high
composite scores, notes named by the user, and the notes on either side of
any implicit connection worth testing.

**4 — Cross-reference.** Look past keyword overlap:
- Grant themes matching project goals
- Person expertise filling a project gap
- Complementary entities that could combine
- Second-degree relationships (A→B, B→C implies A↔C)
- Resource gaps (several entities need X, nobody provides X)
- Compound opportunities (2–3 entities together create outsized value)

**5 — Rank.** Relevance and impact first; urgency and feasibility as
tiebreakers.

**6 — Report.** Use the output format below.

## Output Format

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject>
Vault: <path or scope>
Date: <YYYY-MM-DD>
Entities analyzed: <count>

## Top Matches
Ranked by composite score. Name, score, type, link counts, tags, path, urgency signal.

## Key Connections
Second-degree relationships, implicit connections, tag clusters.

## Gaps
Unresolved entities, thin coverage, bottlenecks.

## Strategic Insight
Dominant entity types, hub nodes, orphan count, urgency summary.

## Recommended Next Actions
1–6 concrete steps labeled URGENT / HIGH / STANDARD.
```

## Pitfalls

- Do not keyword-match — think semantically
- Do not list everything — surface only what carries weight
- Report negative findings: missing funding, dead ends, gaps
- Never fabricate a connection; if the link is not there, say the vault does not connect them
- Composite score is a signal, not a verdict
- Skip the obvious — the user has read their own notes
- Respect scope; stay in the requested subset unless told otherwise
- An empty result is a real finding. A vault with no connections means the
  notes are not linked, and saying so is more useful than manufacturing
  connections to fill the section.
