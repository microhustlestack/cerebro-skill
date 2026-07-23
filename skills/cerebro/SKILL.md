---
name: cerebro
version: 1.1.0
description: Scan, analyze, and connect knowledge across a markdown-based vault — identifying semantic matches, hidden relationships, ranking entities, and generating strategic recommendations. Triggers on scan, cross-reference, Cerebro, intelligence scan, and strategic analysis requests.
metadata:
  hermes:
    tags: [research, knowledge-base, obsidian, vault, semantic-analysis, intelligence]
    related_skills: [obsidian-vault-organizer, obsidian-skills-vault-import]
---

# CEREBRO — Strategic Intelligence Engine

An advanced scanning system that reads a structured markdown-based vault, identifies semantic relationships between entities, ranks them by strategic value, and surfaces actionable intelligence.

## Core Principle

Think like a strategist, not a search engine. Surface connections the user may not see. Prioritize clarity, relevance, and actionable output over exhaustive listing.

## When to Activate

- User asks to scan, analyze, or cross-reference a vault or collection of files
- User mentions Cerebro or intelligence scan
- User wants to find connections between grants, people, projects, opportunities, or any structured entities
- User needs strategic recommendations from a body of knowledge
- User wants to discover hidden relationships between items in their ecosystem

## VaultParser Script

A production-grade Python parser is included at `scripts/vault_parser.py`. It parses every .md file in a vault, extracting frontmatter, wikilinks, backlinks, callouts, dataview queries, embeds, tables, and code blocks. Produces a JSON index for bulk analysis.

```bash
python3 scripts/vault_parser.py /path/to/vault /path/to/output/vault-index.json
```

Output: comprehensive vault report (entity distribution, tags, link graph, orphans) + full JSON index. Zero external dependencies (stdlib + PyYAML only).

### When to use the script vs brain analysis
- **Script**: Large vaults (50+ files), need structured indexes, JSON export, link graphs
- **Brain**: Targeted scan of specific files, semantic reasoning, strategic connections

## How It Works

### Step 1: Inventory the Vault

Scan the directory structure to understand what entities exist:

```bash
search_files target="files" pattern="*.md" path="<vault-dir>"
read_file path="<vault-dir>/README.md"
```

Build a mental map of:
- Entity types (grants, people, projects, opportunities, etc.)
- Directory structure and organization
- File naming conventions
- Key metadata fields (tags, frontmatter, categories, dates, status)

### Step 1b: Run VaultParser (for large vaults)

```bash
python3 ~/.hermes/skills/research/cerebro/scripts/vault_parser.py /path/to/vault /path/to/output.json
```

This gives you entity type distribution, tag index, link graph, orphan detection, and a full JSON index of every note.

### Step 2: Deep Entity Analysis

Read the relevant entity files. Prioritize based on:
- Files with frontmatter (YAML metadata blocks)
- Files tagged with priority, urgency, or status markers
- Recently modified files
- Files explicitly mentioned by the user

For each entity, extract:
- **Core identity**: What is this?
- **Temporal markers**: Deadlines, start dates, review dates
- **Status markers**: Active, pending, expired, archived
- **Tags/categories**: Classification signals
- **Key attributes**: Budget, skills, tech stacks, regions, etc.

### Step 3: Semantic Matching

Cross-reference entities using multi-dimensional analysis:

**Direct matches:**
- Same tags, categories, or keywords
- Same people, organizations, or locations mentioned
- Overlapping date ranges or deadlines

**Semantic matches (the real value):**
- Grant themes that match project goals (not exact keyword overlap)
- Person expertise that fills project gaps
- Opportunities aligned with organizational mission
- Complementary entities that could be combined
- Timeline conflicts or synergies

**Hidden connections:**
- Second-degree relationships (A matches B, B matches C)
- Resource gaps (multiple entities need X, nobody provides X)
- Bottlenecks (multiple entities depend on one shared constraint)
- Compound opportunities (combining 2-3 entities creates outsized value)

### Step 4: Rank and Score

Rank each finding by:

| Criterion | Weight | Scoring |
|-----------|--------|---------|
| **Relevance** | High | How directly aligned are the entities? |
| **Urgency** | Medium | Time-sensitive? (deadlines, expiring opportunities) |
| **Impact** | High | Potential value if acted on? |
| **Feasibility** | Medium | How easy is it to act? |

### Step 5: Generate Intelligence Report

Format output following the CEREBRO output structure below.

## Output Format

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject/description>
Vault: <path or scope>
Entities analyzed: <count>

## Top Matches
Ranked by relevance + urgency + impact.
Each entry includes what matches what, why, and urgency level.

## Key Connections
Hidden or non-obvious relationships discovered.
Focus on second-degree connections, resource gaps, compound opportunities.

## Strategic Insight
Big-picture takeaway. What does this analysis reveal?
What patterns, risks, or opportunities emerge?

## Recommended Next Actions
1-5 concrete, actionable steps. Prioritized by impact x urgency.
```

## Pitfalls

- Do not just keyword-match. Think semantically.
- Do not list everything. Surface only the most valuable connections.
- Flag urgency clearly: URGENT (within 7 days), HIGH (within 30 days), STANDARD.
- Surface negative findings too (missing funding, gaps, etc.).
- Do not fabricate connections.
- Context matters — skip what is obvious, surface what they do not know.
- Respect scope — stick to the subset requested unless told to go broader.

## Related Skills

- obsidian-skills-vault-import
- openrouter-models
