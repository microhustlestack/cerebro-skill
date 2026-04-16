---
name: cerebro
version: 2.0.0
author: microhustlestack
license: MIT
description: Scan, analyze, and connect knowledge across a markdown vault -- identifying semantic matches, hidden relationships, scoring entities by strategic value, and generating actionable intelligence reports. Triggers on scan, cross-reference, intelligence scan, and strategic analysis requests.
metadata:
  hermes:
    tags: [research, knowledge-base, obsidian, vault, semantic-analysis, intelligence, scoring]
    related_skills: [obsidian-vault-organizer, obsidian-skills-vault-import]
---

# CEREBRO -- Strategic Intelligence Engine

An advanced scanning system that reads a structured markdown vault, identifies semantic relationships between entities, scores them by strategic value using a four-dimension model, detects urgency signals, and surfaces actionable intelligence.

## Core Principle

Think like a strategist, not a search engine. Surface connections the user may not see. Prioritize clarity, relevance, and actionable output over exhaustive listing.

## When to Use

- User asks to scan, analyze, or cross-reference a vault or collection of markdown files
- User mentions Cerebro or intelligence scan
- User wants to find connections between grants, people, projects, opportunities, or any structured entities
- User needs strategic recommendations from a body of knowledge
- User wants to discover hidden relationships between items in their ecosystem
- User needs urgency triage across a set of notes

## Script vs. Brain Analysis

| Vault Size | Approach |
|------------|----------|
| 50+ files | Run `vault_parser.py` first to build a JSON index + CEREBRO report, then do semantic analysis on top |
| < 50 files | Read files directly and reason semantically -- no script needed |
| Targeted query | Always brain analysis regardless of vault size |

## VaultParser Script

A production-grade Python parser lives at `$CEREBRO_SKILL_DIR/scripts/vault_parser.py`.

`$CEREBRO_SKILL_DIR` is the directory where this skill is installed. Common locations:

| Platform | Path |
|----------|------|
| Hermes | `~/.hermes/skills/research/cerebro` |
| Claude Code | `~/.claude/skills/cerebro` or project root |
| OpenClaw | `~/.openclaw/shared-skills/cerebro` |
| Opencode | wherever the skill was cloned |

Zero external dependencies (stdlib + PyYAML only).

```bash
# Basic scan + CEREBRO report to stdout
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault

# JSON index + report file
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault output/vault-index.json \
  --report cerebro_report.md \
  --query "grant opportunities" \
  --top 15
```

Output: entity distribution, tag index, link graph, orphan detection, urgency signals, strategic scores, full JSON index, and a ready-to-use CEREBRO INTELLIGENCE SCAN report.

## Scoring Model

Every note is scored across four dimensions. Composite score drives Top Matches ranking.

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Connectivity | 35% | Outgoing wikilinks + 2x incoming backlinks |
| Tag Influence | 25% | How widely this note's tags appear across the vault |
| Urgency | 25% | Derived from urgency signals (URGENT=1.0, HIGH=0.6, STANDARD=0.2) |
| Richness | 15% | Frontmatter, headings, word count, tables, callouts |

## Urgency Detection

VaultParser automatically detects urgency signals in body text and frontmatter.

Keywords detected: urgent, asap, immediately, critical, time-sensitive, overdue, must act.

Frontmatter fields checked: deadline, due, due_date, submit_by, expires, closes, apply_by.

| Days Until | Level |
|------------|-------|
| Past | PAST |
| 0-7 | URGENT |
| 8-30 | HIGH |
| 31+ | STANDARD |

ISO dates (YYYY-MM-DD) in body text are also detected and classified automatically.

## Workflow

### Step 1 -- Inventory the Vault

Build a mental map of entity types, directory structure, naming conventions, and key metadata fields.

**Tool usage by platform:**

| Platform | Commands |
|----------|----------|
| Hermes | `search_files target="files" pattern="*.md" path="<vault>"` |
| Claude Code | `Glob("**/*.md", path=vault_dir)` then `Grep` for `[[wikilinks]]` and `#tags` |
| OpenClaw | `search_files` then `read_file` |
| Opencode | `terminal(command="find <vault> -name '*.md'")` or attach files with `-f` |
| Codex | `cd` into vault workdir; reference files by path in the prompt |

### Step 1b -- Run VaultParser (large vaults only)

```bash
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py <vault-dir> <output.json> --report cerebro_report.md
```

Use the JSON index for entity distribution, tag cloud, urgency triage, strategic scores, and link graph before doing semantic analysis.

### Step 2 -- Deep Entity Analysis

Read the relevant files. Prioritize:
- Files flagged URGENT or HIGH by vault_parser.py
- Files with high composite strategic scores
- Files with YAML frontmatter
- Recently modified files
- Files explicitly mentioned by the user

Extract per entity: core identity, temporal markers (deadlines, dates), status (active/pending/archived), tags, and key attributes (budget, skills, regions, etc.).

### Step 3 -- Semantic Matching

Cross-reference entities on multiple dimensions.

Direct matches: same tags, categories, keywords, people, orgs, locations, or overlapping dates.

Semantic matches (the real value):
- Grant themes that match project goals (not just keyword overlap)
- Person expertise that fills project gaps
- Opportunities aligned with organizational mission
- Complementary entities that could be combined

Hidden connections:
- Second-degree relationships (A->B, B->C implies A<->C)
- Resource gaps (multiple entities need X, nobody provides X)
- Bottlenecks (multiple entities depend on one shared constraint)
- Compound opportunities (combining 2-3 entities creates outsized value)

### Step 4 -- Rank and Score

Use the scoring model output from vault_parser.py as the baseline. Supplement with semantic judgment. Composite score is a starting signal, not a final verdict.

Flag urgency: URGENT (<=7 days), HIGH (<=30 days), STANDARD.

### Step 5 -- Generate Intelligence Report

Produce the CEREBRO output format below. vault_parser.py generates this automatically via --report. For brain analysis, produce it manually.

### Step 6 -- Deliver (OpenClaw)

For OpenClaw, optionally push the report to Telegram after saving:

```bash
openclaw message send --target telegram:<your-id> --message "$(cat cerebro_report.md)"
```

## Platform-Specific Invocation

### Opencode

**Large vault (50+ files):**
```bash
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault /tmp/vault-index.json \
  --report /tmp/cerebro_report.md

opencode run 'You are CEREBRO. Analyze this vault index. Deepen the analysis beyond the auto-generated report: surface compound opportunities, second-degree relationships, and resource gaps. Produce the full CEREBRO INTELLIGENCE SCAN report.' \
  -f /tmp/vault-index.json \
  -f /tmp/cerebro_report.md \
  --model openrouter/anthropic/claude-sonnet-4
```

**Small vault (< 50 files):**
```bash
opencode run 'Run a CEREBRO intelligence scan across these notes. Surface hidden connections, rank by impact x urgency, produce the full CEREBRO INTELLIGENCE SCAN report.' \
  $(find /path/to/vault -name "*.md" | head -40 | xargs -I{} echo "-f {}")
```

---

### Codex

Codex requires a git repo and `pty=true`.

```bash
# Build index inside the vault directory first
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault \
  /path/to/vault/vault-index.json --report /path/to/vault/cerebro_report.md

# Run from inside the vault (must be a git repo)
terminal(
  command="codex --full-auto exec 'You are CEREBRO. Read vault-index.json and cerebro_report.md. Deepen the analysis: compound opportunities, second-degree connections, resource gaps. Save updated report to cerebro_report_v2.md.'",
  workdir="/path/to/vault",
  pty=true
)
```

If vault is not a git repo:
```bash
TMPVAULT=$(mktemp -d)
cp -r /path/to/vault/. $TMPVAULT
cd $TMPVAULT && git init && git add -A && git commit -m 'init'
codex --full-auto exec 'Run a CEREBRO intelligence scan. Read all .md files and save cerebro_report.md.'
```

### Claude Code

```bash
python3 $CEREBRO_SKILL_DIR/scripts/vault_parser.py /path/to/vault /tmp/vault-index.json \
  --report /tmp/cerebro_report.md

claude -p "Run a CEREBRO intelligence scan on this vault index. Deepen the strategic insight beyond the auto-generated report." \
  --file /tmp/vault-index.json \
  --file /tmp/cerebro_report.md
```

### OpenClaw

Trigger in chat, then push results to Telegram:

```bash
openclaw message send --target telegram:<your-id> --message "$(cat cerebro_report.md)"
```

## Output Format

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject/description>
Vault: <path or scope>
Date: <YYYY-MM-DD>
Entities analyzed: <count>

## Top Matches
Ranked by composite score (connectivity 35%, tag influence 25%, urgency 25%, richness 15%).
Each entry: name, score, type, link counts, tags, path, top urgency signal.

## Key Connections
Hidden or non-obvious relationships.
Second-degree connections, tag clusters, resource gaps, compound opportunities.

## Strategic Insight
Patterns, risks, opportunities, dominant entity types, hub nodes.

## Recommended Next Actions
1-6 concrete steps labeled URGENT / HIGH / STANDARD.
```

| Platform | Output destination |
|----------|--------------------|
| Hermes | `$CEREBRO_SKILL_DIR/output/cerebro_report.md` |
| Claude Code | `cerebro_report.md` in working directory |
| OpenClaw | `cerebro_report.md` + optional Telegram push |
| Opencode | stdout or redirect with `> cerebro_report.md` |
| Codex | `cerebro_report.md` written by agent into workdir |

## Pitfalls

- Do not keyword-match only -- think semantically
- Do not list everything -- surface only the most valuable connections
- Surface negative findings too (missing funding, gaps, dead ends)
- Do not fabricate connections
- Composite score is a starting signal -- semantic judgment overrides when warranted
- Context matters -- skip what is obvious, surface what the user does not know
- Respect scope -- stick to the subset requested unless told to go broader

## Related Skills

- `obsidian-vault-organizer` -- clean and restructure a vault before scanning
- `obsidian-skills-vault-import` -- import skills from the vault into OpenClaw/Hermes
- `cerebro-knowledge-export` -- export insights to Notion, Google Docs, etc.
