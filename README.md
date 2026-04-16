# CEREBRO — Strategic Intelligence Engine

> Scan, score, and connect knowledge across a markdown vault. Think like a strategist, not a search engine.

**Version:** 2.0.0 · **License:** MIT · **Author:** microhustlestack · **Python:** 3.11+

![Tests](https://github.com/microhustlestack/cerebro-skill/actions/workflows/tests.yml/badge.svg)

---

## What It Does

CEREBRO reads a structured markdown vault, scores every note on strategic value, detects time-sensitive signals, maps semantic relationships between entities, and surfaces actionable intelligence — including connections you did not know to look for.

It is not a search tool. It finds:

**Second-degree relationships** — A links to B, B links to C. CEREBRO surfaces A→C.

**Resource gaps** — multiple entities need X, nobody provides X.

**Compound opportunities** — combining 2-3 entities creates outsized value.

**Bottlenecks** — multiple entities depend on one shared constraint.

**Urgency signals** — deadlines, keywords, and frontmatter date fields classified as URGENT, HIGH, STANDARD, or PAST.

---

## Supported Platforms

| Platform | Install method |
|----------|---------------|
| **Hermes** | `hermes skills tap add microhustlestack/cerebro-skill` |
| **Claude Code** | Copy `SKILL.md` to `~/.claude/skills/cerebro/` |
| **OpenClaw** | `bash install.sh openclaw` |
| **Opencode** | `opencode run` with `-f vault-index.json` |
| **Codex** | Run inside a git repo with `--full-auto` |

---

## Installation

### One-command install

```bash
git clone https://github.com/microhustlestack/cerebro-skill.git
cd cerebro-skill
bash install.sh          # installs to Hermes, OpenClaw, and Claude Code
bash install.sh hermes   # install to one platform only
```

### Hermes

```bash
hermes skills tap add microhustlestack/cerebro-skill
hermes skills install cerebro
```

### Manual

Clone the repo and copy `SKILL.md` and `scripts/vault_parser.py` to your agent's skills folder.

---

## Quick Start

### Small vault (under 50 files) — brain analysis

Point your agent at the vault and trigger with natural language:

> "Run a CEREBRO intelligence scan on ~/Documents/Obsidian/my-vault"

The agent reads files directly, reasons semantically, and produces the report.

### Large vault (50+ files) — parser + brain analysis

```bash
# Install dependencies (PyYAML only)
pip install -r requirements.txt

# 1. Build a JSON index and CEREBRO report in one command
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json \
  --report cerebro_report.md \
  --query "grant opportunities Q2"

# 2. Feed the index to your agent for deeper semantic analysis
opencode run 'You are CEREBRO. Analyze vault-index.json and cerebro_report.md. Deepen the strategic insight: compound opportunities, second-degree connections, resource gaps.' \
  -f output/vault-index.json \
  -f cerebro_report.md
```

---

## The vault_parser.py Script

A production-grade Python parser bundled in `scripts/`. Parses every `.md` file and produces a structured JSON index with urgency signals and strategic scores.

**Dependencies:** Python 3.11+ · PyYAML only

```bash
# Basic scan — CEREBRO report to stdout
python3 scripts/vault_parser.py /path/to/vault

# JSON index only
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json

# Full output — JSON index + report file + custom query label + top 15
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json \
  --report cerebro_report.md \
  --query "find funding gaps" \
  --top 15
```

**What it extracts:**

YAML frontmatter, wikilinks (with display text and heading anchor resolution), backlinks, tags (frontmatter and inline), callouts, dataview queries, embedded files, markdown tables, code blocks, entity type inference, daily note detection.

**What it produces:**

Link graph, backlink graph, tag index, entity index, directory index, orphan detection, urgency signals per note, strategic scores per note, JSON export, CEREBRO INTELLIGENCE SCAN report.

---

## Scoring Model

Every note is scored on four dimensions. Composite score drives Top Matches ranking.

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Connectivity | 35% | Outgoing wikilinks + 2x incoming backlinks |
| Tag Influence | 25% | How widely this note's tags appear across the vault |
| Urgency | 25% | Derived from urgency signals (URGENT=1.0, HIGH=0.6, STANDARD=0.2) |
| Richness | 15% | Frontmatter, headings, word count, tables, callouts |

Composite score is a starting signal for the agent, not a final verdict. Semantic judgment overrides when warranted.

---

## Urgency Detection

VaultParser scans every note automatically for time-sensitive signals.

**Keywords detected:** urgent, asap, immediately, critical, time-sensitive, overdue, must act.

**Frontmatter fields checked:** deadline, due, due_date, submit_by, expires, closes, apply_by.

**ISO dates in body text** (YYYY-MM-DD) are detected and classified by days remaining.

| Days Until | Level |
|------------|-------|
| Past | PAST |
| 0-7 | URGENT |
| 8-30 | HIGH |
| 31+ | STANDARD |

---

## Output Format

Every CEREBRO run produces a report in this structure:

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject/description>
Vault: <path or scope>
Date: <YYYY-MM-DD>
Entities analyzed: <count>

## Top Matches
Ranked by composite score. Each entry: name, score, type, link counts, tags, path, urgency signal.

## Key Connections
Second-degree relationships and tag clusters not made explicit by the vault.

## Strategic Insight
Dominant entity types, hub nodes, orphan count, urgency summary.

## Recommended Next Actions
1-6 concrete steps labeled URGENT / HIGH / STANDARD.
```

| Platform | Output destination |
|----------|--------------------|
| Hermes | `$CEREBRO_SKILL_DIR/output/cerebro_report.md` |
| Claude Code | `cerebro_report.md` in working directory |
| OpenClaw | `cerebro_report.md` + optional Telegram push |
| Opencode | stdout or `> cerebro_report.md` |
| Codex | `cerebro_report.md` written into workdir |

---

## Platform-Specific Usage

### Hermes

Trigger naturally in chat:

> "Cerebro scan ~/Documents/Obsidian/Skills-Vault"

Or with a targeted query:

> "Show how 'zero-cost model' relates to 'model-fallback-protocol'"

### Claude Code

```bash
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json \
  --report cerebro_report.md

claude -p "Run a CEREBRO intelligence scan. Deepen the analysis beyond the auto-generated report." \
  --file output/vault-index.json \
  --file cerebro_report.md
```

### Opencode

```bash
# Large vault
python3 scripts/vault_parser.py /path/to/vault /tmp/vault-index.json \
  --report /tmp/cerebro_report.md

opencode run 'You are CEREBRO. Analyze this vault index and report. Surface compound opportunities and second-degree relationships.' \
  -f /tmp/vault-index.json \
  -f /tmp/cerebro_report.md \
  --model openrouter/anthropic/claude-sonnet-4

# Small vault
opencode run 'Run a CEREBRO intelligence scan across these notes.' \
  $(find /path/to/vault -name "*.md" | head -40 | xargs -I{} echo "-f {}")
```

### Codex

Codex requires a git repo and `pty=true`:

```bash
python3 scripts/vault_parser.py /path/to/vault \
  /path/to/vault/vault-index.json --report /path/to/vault/cerebro_report.md

terminal(
  command="codex --full-auto exec 'You are CEREBRO. Read vault-index.json and cerebro_report.md. Deepen the analysis. Save to cerebro_report_v2.md.'",
  workdir="/path/to/vault",
  pty=true
)
```

If the vault is not a git repo:

```bash
TMPVAULT=$(mktemp -d)
cp -r /path/to/vault/. $TMPVAULT
cd $TMPVAULT && git init && git add -A && git commit -m 'init'
codex --full-auto exec 'Run a CEREBRO intelligence scan. Read all .md files and save cerebro_report.md.'
```

### OpenClaw

Trigger in chat, then push results to Telegram:

```bash
openclaw message send --target telegram:<your-id> --message "$(cat cerebro_report.md)"
```

---

## Ranking Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Relevance | High | How directly aligned are the entities? |
| Impact | High | Potential value if acted on? |
| Urgency | Medium | Time-sensitive? (deadlines, expiring opportunities) |
| Feasibility | Medium | How easy is it to act? |

---

## Use with LLM Wiki

> **LLM Wiki = your organized brain (structured knowledge)**
> **CEREBRO = your strategist (pattern recognition + decision engine)**

### The Simple Model

LLM Wiki answers: "What is this?" and "Where is that?"

CEREBRO answers: "What matters most right now?", "What's connected that I'm missing?", "Where is the opportunity?"

### The Workflow

**Step 1 — Ingest (LLM Wiki)**

Drop content into `raw/`: grant notes, meeting notes, ideas, articles.

**Step 2 — Structure (LLM Wiki)**

Content moves into `wiki/` with tags, links, categories, and indexes.

**Step 3 — Parse (CEREBRO)**

```bash
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json \
  --report cerebro_report.md
```

Produces a link graph, tag index, urgency triage, strategic scores, and entity map.

**Step 4 — Analyze (CEREBRO Skill)**

Run queries like:

- "Find strongest connections between initiatives"
- "Identify underutilized resources"
- "Detect repeated bottlenecks"
- "Map stakeholder overlap"

**Step 5 — Output (Strategic Reports)**

Into `output/` — Top Opportunities, Strategic Gaps, High-Value Connections, Action Recommendations.

### Real Example

Say your vault contains: MSVL Sunset Concert Series, Taste of Juneteenth, Black Philanthropy Month, YESpvd, East 33.

LLM Wiki alone lets you find each program.

CEREBRO shows that:
- The same sponsors appear across 3 initiatives
- One initiative is under-leveraged
- One audience overlaps but is not monetized
- A single partnership strategy could unlock all 5

That is strategy. That is leverage.

### Intelligence Prompt (Plug-and-Play)

Use this with your parsed vault index:

```
SYSTEM ROLE:
You are CEREBRO, a strategic intelligence engine operating on a structured knowledge vault.

OBJECTIVE:
Analyze the provided vault data and generate a strategic intelligence report focused on leverage, opportunity, and system-level insights.

INPUT:
- Entity map
- Tag index
- Link graph
- Urgency signals
- Strategic scores

TASKS:
1. Identify the top 5 most connected entities (high leverage nodes)
2. Detect underutilized assets (low connection, high potential)
3. Surface hidden relationships between unrelated domains
4. Identify repeated bottlenecks or gaps
5. Recommend 5 strategic actions ranked by impact and urgency

OUTPUT FORMAT:

CEREBRO INTELLIGENCE REPORT

Top Leverage Nodes:
- [Entity]: reason

Hidden Opportunities:
- [Insight]

System Gaps:
- [Gap]

Key Connections:
- [Connection]

Recommended Actions:
1. [Action] (Impact: High, Urgency: High)
2. ...

TONE:
Direct, strategic. Focus on leverage and execution.
```

---

## CEREBRO OS — Full Stack Architecture

| Layer | Tool | Role |
|-------|------|------|
| Knowledge Base | LLM Wiki / Obsidian / NotebookLM | Storage + retrieval |
| Structure Extractor | `vault_parser.py` | Machine-readable index + urgency + scores |
| Reasoning Layer | Claude / OpenClaw / ChatGPT | Semantic analysis + strategy |
| Visualization | Google Sheets / Notion / Dashboard | Output + action tracking |

---

## Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

69 tests covering parsing, link graph, orphan detection, urgency detection, scoring, CEREBRO report output, JSON export, and edge cases. CI runs on every push via GitHub Actions on Python 3.11 and 3.12.

---

## Repository Structure

```
cerebro-skill/
  SKILL.md                  Agent skill definition (all platforms)
  CLAUDE.md                 Claude Code guidance
  CHANGELOG.md              Version history
  install.sh                One-command deploy script
  requirements.txt          Runtime dependencies
  requirements-dev.txt      Test dependencies
  scripts/
    vault_parser.py         Vault indexing and intelligence engine
  tests/
    test_vault_parser.py    69-test suite
  output/                   Runtime reports (git-ignored)
  .github/
    workflows/
      tests.yml             CI — Python 3.11 + 3.12
```

---

## Related Skills

- [`obsidian-vault-organizer`](https://github.com/microhustlestack) — clean and restructure a vault before scanning
- `obsidian-skills-vault-import` — import skills from the vault into OpenClaw/Hermes
- `cerebro-knowledge-export` — export insights to Notion, Google Docs, etc.

---

## License

MIT
