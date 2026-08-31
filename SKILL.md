---
name: vestrik
description: >
  Structured knowledge intelligence for markdown vaults. Use this skill to analyze a vault, scan notes for
  connections, surface relationships between entities, find hidden links, map a knowledge base, audit what
  a set of notes is missing, or generate an intelligence report from markdown files. Trigger on phrases like
  "scan my vault", "analyze my notes", "find connections in", "what am I missing in my notes", "vestrik",
  or requests to reason across multiple markdown files as a system. VESTRIK // VAULT looks for structural
  findings including second-degree relationships, undocumented entities, thin coverage, bottlenecks and
  compound opportunities. Do not treat it as plain search.
license: MIT
---

# VESTRIK // VAULT

Structured Knowledge Intelligence for AI agents.

## Core Principle

Deterministic analysis first. Agent reasoning second. Use the parser for checkable structure — links, tags,
scores, gaps and urgency — then use semantic reasoning for meaning. Never fabricate a connection.

## Running VESTRIK

```bash
vestrik /path/to/vault --report vestrik_report.md --gaps
vestrik /path/to/vault output/vault-index.json --gaps --quiet
vestrik /path/to/vault --quiet --report -
```

Requires Python 3.11+ and PyYAML. During the migration, the legacy `cerebro` command remains available as a
compatibility alias for existing users.

## Structural Intelligence

- **Unresolved entities:** wikilink targets with no matching note.
- **Thin coverage:** tags carrying too little documentation.
- **Implicit connections:** note pairs sharing context without a direct link.
- **Bottlenecks:** notes depended on across multiple areas.
- **Entity catalog:** structurally named entities, frequency and documentation status.
- **Relationship matrix:** adjacency among the highest-scoring notes.
- **Urgency:** deadline and keyword signals classified URGENT / HIGH / STANDARD / PAST.

## Workflow

1. Inventory the vault structure and metadata conventions.
2. Parse large vaults; use `--gaps` for missing/weak/disconnected questions.
3. Read high-value and urgent notes deeply.
4. Cross-reference explicit and second-degree relationships.
5. Rank by relevance and impact; use urgency and feasibility as tie-breakers.
6. Report only findings that carry weight and can be checked.

## Output

```text
VESTRIK INTELLIGENCE SCAN
Scan: <subject>
Vault: <path>
Date: <YYYY-MM-DD>
Entities analyzed: <count>

## Top Matches
## Key Connections
## Gaps
## Strategic Insight
## Recommended Next Actions
```

## Guardrails

- Do not keyword-match and call it intelligence.
- Do not list everything.
- Report negative findings and dead ends.
- Never fabricate relationships.
- Treat the composite score as a signal, not a verdict.
- An empty result is a valid finding.
