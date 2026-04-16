---
name: cerebro
version: 1.1.0
author: microhustlestack
license: MIT
description: Scan, analyze, and connect knowledge across a markdown vault — identifying semantic matches, hidden relationships, ranking entities, and generating strategic recommendations. Triggers on scan, cross-reference, intelligence scan, and strategic analysis requests.
metadata:
  hermes:
    tags: [research, knowledge-base, obsidian, vault, semantic-analysis, intelligence]
    related_skills: [obsidian-vault-organizer, obsidian-skills-vault-import]
---

# CEREBRO — Strategic Intelligence Engine

An advanced scanning system that reads a structured markdown-based vault, identifies semantic relationships between entities, ranks them by strategic value, and surfaces actionable intelligence.

## Core Principle

Think like a strategist, not a search engine. Surface connections the user may not see. Prioritize clarity, relevance, and actionable output over exhaustive listing.

## When to Use

- User asks to scan, analyze, or cross-reference a vault or collection of markdown files
- User mentions Cerebro or intelligence scan
- User wants to find connections between grants, people, projects, opportunities, or any structured entities
- User needs strategic recommendations from a body of knowledge
- User wants to discover hidden relationships between items in their ecosystem

## Script vs. Brain Analysis

| Vault Size | Approach |
|------------|----------|
| 50+ files | Run `vault_parser.py` first to build a JSON index, then do semantic analysis on top |
| < 50 files | Read files directly and reason semantically — no script needed |
| Targeted query | Always brain analysis regardless of vault size |

## VaultParser Script

A production-grade Python parser lives at `~/.hermes/skills/research/cerebro/scripts/vault_parser.py`.
It parses every `.md` file, extracting frontmatter, wikilinks, backlinks, callouts, dataview queries,
embeds, tables, and code blocks. Zero external dependencies (stdlib + PyYAML only).

```bash
python3 ~/.hermes/skills/research/cerebro/scripts/vault_parser.py /path/to/vault /path/to/output.json
```

Output: entity distribution, tag index, link graph, orphan detection, full JSON index.

## Workflow

### Step 1 — Inventory the Vault

Build a mental map of entity types, directory structure, naming conventions, and key metadata fields.

**Tool usage by platform:**

| Platform | Commands |
|----------|----------|
| Hermes | `search_files target="files" pattern="*.md" path="<vault>"` |
| Claude Code | `Glob("**/*.md", path=vault_dir)` then `Grep` for `[[wikilinks]]` and `#tags` |
| OpenClaw | `search_files` then `read_file` |
| Opencode | `terminal(command="find <vault> -name '*.md'")` or attach files with `-f` |
| Codex | `cd` into vault workdir; reference files by path in the prompt |

### Step 1b — Run VaultParser (large vaults only)

```bash
python3 ~/.hermes/skills/research/cerebro/scripts/vault_parser.py <vault-dir> <output.json>
```

Use the JSON index for entity distribution, tag cloud, and link graph before doing semantic analysis.

### Step 2 — Deep Entity Analysis

Read the relevant files. Prioritize:
- Files with YAML frontmatter
- Files tagged with priority, urgency, or status markers
- Recently modified files
- Files explicitly mentioned by the user

Extract per entity: core identity, temporal markers (deadlines, dates), status (active/pending/archived), tags, and key attributes (budget, skills, regions, etc.).

### Step 3 — Semantic Matching

Cross-reference entities on multiple dimensions:

**Direct matches:** same tags, categories, keywords, people, orgs, locations, or overlapping dates.

**Semantic matches (the real value):**
- Grant themes that match project goals (not just keyword overlap)
- Person expertise that fills project gaps
- Opportunities aligned with organizational mission
- Complementary entities that could be combined

**Hidden connections:**
- Second-degree relationships (A→B, B→C implies A↔C)
- Resource gaps (multiple entities need X, nobody provides X)
- Bottlenecks (multiple entities depend on one shared constraint)
- Compound opportunities (combining 2–3 entities creates outsized value)

### Step 4 — Rank and Score

| Criterion | Weight |
|-----------|--------|
| Relevance | High — how directly aligned are the entities? |
| Impact | High — potential value if acted on? |
| Urgency | Medium — time-sensitive? (deadlines, expiring opportunities) |
| Feasibility | Medium — how easy is it to act? |

Flag urgency explicitly: **URGENT** (≤7 days), **HIGH** (≤30 days), **STANDARD**.

### Step 5 — Generate Intelligence Report

Produce the CEREBRO output format below.

### Step 6 — Deliver (OpenClaw)

For OpenClaw, optionally push the report to Telegram after saving:

```bash
openclaw message send --target telegram:7184395339 --message "<report>"
```

## Platform-Specific Invocation

### Opencode

Opencode is the cleanest fit — `opencode run` is a bounded one-shot task, matching cerebro's workflow exactly.

**Large vault (50+ files):**
```bash
# 1. Build JSON index
python3 ~/.hermes/skills/research/cerebro/scripts/vault_parser.py /path/to/vault /tmp/vault-index.json

# 2. Run cerebro analysis with index attached
opencode run 'You are CEREBRO. Analyze this vault index and produce the full CEREBRO INTELLIGENCE SCAN report: Top Matches, Key Connections, Strategic Insight, Recommended Next Actions. Think like a strategist — surface hidden connections and second-degree relationships. Rank findings by relevance + impact + urgency. Flag URGENT (≤7d), HIGH (≤30d), STANDARD.' \
  -f /tmp/vault-index.json
```

**Small vault (< 50 files):**
```bash
# Attach individual files directly
opencode run 'Run a CEREBRO intelligence scan across these notes. Surface hidden connections, rank by impact x urgency, and produce the full CEREBRO INTELLIGENCE SCAN report.' \
  $(find /path/to/vault -name "*.md" | head 40 | xargs -I{} echo "-f {}")
```

**Save output to file:**
```bash
opencode run '...' -f vault-index.json > cerebro_report.md
```

Use `--model openrouter/anthropic/claude-sonnet-4` or similar for best semantic reasoning.

---

### Codex

Codex requires a git repo and `pty=true`. It has no `-f` flag — files must be in the workdir.

**Large vault:**
```bash
# 1. Build JSON index inside the vault directory
python3 ~/.hermes/skills/research/cerebro/scripts/vault_parser.py /path/to/vault /path/to/vault/vault-index.json

# 2. Run Codex from inside the vault (which must be a git repo)
terminal(
  command="codex --full-auto exec 'You are CEREBRO. Read vault-index.json, then read individual .md files as needed. Produce the CEREBRO INTELLIGENCE SCAN report: Top Matches, Key Connections, Strategic Insight, Recommended Next Actions. Save output to cerebro_report.md.'",
  workdir="/path/to/vault",
  pty=true
)
```

**If vault is not a git repo:**
```bash
# Initialize a temporary git repo with the vault contents
terminal(command="TMPVAULT=$(mktemp -d) && cp -r /path/to/vault/. $TMPVAULT && cd $TMPVAULT && git init && git add -A && git commit -m 'init' && codex --full-auto exec 'Run a CEREBRO intelligence scan. Read all .md files, find hidden relationships, and save cerebro_report.md.'", pty=true)
```

**Key Codex constraints:**
- Always `pty=true` — Codex hangs without a PTY
- Always inside a git repo — use `git init` in a temp dir if needed
- Use `--full-auto` so Codex can read files and write `cerebro_report.md` without approval prompts
- For long vaults, use `background=true` and monitor with `process(action="log")`

## Output Format

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject/description>
Vault: <path or scope>
Entities analyzed: <count>

## Top Matches
Ranked by relevance + urgency + impact.
Each entry: what matches what, why, and urgency level.

## Key Connections
Hidden or non-obvious relationships discovered.
Focus on second-degree connections, resource gaps, compound opportunities.

## Strategic Insight
Big-picture takeaway. What patterns, risks, or opportunities emerge?

## Recommended Next Actions
1–5 concrete, prioritized steps (impact × urgency).
```

| Platform | Output destination |
|----------|--------------------|
| Hermes | `~/.hermes/skills/research/cerebro/output/cerebro_report.md` |
| Claude Code | `cerebro_report.md` in working directory |
| OpenClaw | `cerebro_report.md` + optional Telegram push |
| Opencode | stdout or redirect with `> cerebro_report.md` |
| Codex | `cerebro_report.md` written by agent into workdir |

## Pitfalls

- Do not keyword-match only — think semantically
- Do not list everything — surface only the most valuable connections
- Surface negative findings too (missing funding, gaps, dead ends)
- Do not fabricate connections
- Context matters — skip what is obvious, surface what they do not know
- Respect scope — stick to the subset requested unless told to go broader

## Related Skills

- `obsidian-vault-organizer` — clean and restructure a vault before scanning
- `obsidian-skills-vault-import` — import skills from the vault into OpenClaw/Hermes
- `cerebro-knowledge-export` — export insights to Notion, Google Docs, etc.
