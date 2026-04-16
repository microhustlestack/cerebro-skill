# CEREBRO — Strategic Intelligence Engine

> Scan, analyze, and connect knowledge across a markdown vault. Think like a strategist, not a search engine.

**Version:** 1.1.0 · **License:** MIT · **Author:** microhustlestack

---

## What It Does

CEREBRO reads a structured markdown vault, maps semantic relationships between entities, ranks them by strategic value, and surfaces actionable intelligence — including connections the user didn't know to look for.

It is not a search tool. It finds:
- **Second-degree relationships** (A→B, B→C implies A↔C)
- **Resource gaps** (multiple entities need X, nobody provides X)
- **Compound opportunities** (combining 2–3 entities creates outsized value)
- **Bottlenecks** (multiple entities depend on one shared constraint)

---

## Supported Platforms

| Platform | Install method |
|----------|---------------|
| **Hermes** | `hermes skills tap add microhustlestack/cerebro-skill` |
| **Claude Code** | Copy `SKILL.md` to your project or `~/.claude/skills/cerebro/` |
| **OpenClaw** | Copy skill directory to `~/.openclaw/shared-skills/cerebro/` |
| **Opencode** | Use `opencode run` with `-f vault-index.json` |
| **Codex** | Run inside a git repo with `--full-auto` |

---

## Installation

### Hermes

```bash
hermes skills tap add microhustlestack/cerebro-skill
hermes skills install cerebro
```

### OpenClaw

```bash
cp -r cerebro/ ~/.openclaw/shared-skills/cerebro
```

### Claude Code / Opencode / Codex

Clone the repo and reference `SKILL.md` directly, or copy the skill directory to your agent's skills folder.

```bash
git clone https://github.com/microhustlestack/cerebro-skill.git
```

---

## Quick Start

### Small vault (< 50 files) — brain analysis

Just point your agent at the vault and trigger with natural language:

> *"Run a CEREBRO intelligence scan on ~/Documents/Obsidian/my-vault"*

The agent reads files directly, reasons semantically, and produces the report.

### Large vault (50+ files) — script + brain analysis

```bash
# 1. Build a JSON index of the vault
python3 scripts/vault_parser.py /path/to/vault /tmp/vault-index.json

# 2. Feed the index to your agent
opencode run 'You are CEREBRO. Analyze vault-index.json and produce the full CEREBRO INTELLIGENCE SCAN report.' \
  -f /tmp/vault-index.json
```

---

## The vault_parser.py Script

A production-grade Python parser bundled in `scripts/`. Parses every `.md` file in a vault and produces a structured JSON index.

**What it extracts:**
- YAML frontmatter
- Wikilinks (`[[...]]`) and backlinks
- Tags (`#tag`)
- Callouts, dataview queries, embeds, tables, code blocks
- Entity distribution, tag index, link graph, orphan detection

**Dependencies:** Python 3.11+ · PyYAML only (no other external deps)

```bash
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json
```

---

## Output Format

Every CEREBRO run produces a report in this structure:

```
CEREBRO INTELLIGENCE SCAN
Scan: <subject/description>
Vault: <path or scope>
Entities analyzed: <count>

## Top Matches
Ranked by relevance + urgency + impact.

## Key Connections
Hidden or non-obvious relationships discovered.

## Strategic Insight
Big-picture takeaway — patterns, risks, opportunities.

## Recommended Next Actions
1–5 concrete steps, prioritized by impact × urgency.
```

Urgency is flagged as **URGENT** (≤7 days), **HIGH** (≤30 days), or **STANDARD**.

| Platform | Output destination |
|----------|--------------------|
| Hermes | `~/.hermes/skills/research/cerebro/output/cerebro_report.md` |
| Claude Code | `cerebro_report.md` in working directory |
| OpenClaw | `cerebro_report.md` + optional Telegram push |
| Opencode | stdout or `> cerebro_report.md` |
| Codex | `cerebro_report.md` written into workdir |

---

## Platform-Specific Usage

### Hermes

Trigger naturally in chat:
> *"Cerebro scan ~/Documents/Obsidian/Skills-Vault"*

Or with a targeted query:
> *"Show how 'zero-cost model' relates to 'model-fallback-protocol'"*

### Claude Code

```bash
# Claude Code reads markdown natively via Glob + Grep + Read
# For large vaults, run the parser first
python3 scripts/vault_parser.py /path/to/vault /tmp/vault-index.json
claude -p "Run a CEREBRO intelligence scan on this vault index" --file /tmp/vault-index.json
```

### Opencode

```bash
# Large vault
python3 scripts/vault_parser.py /path/to/vault /tmp/vault-index.json
opencode run 'You are CEREBRO. Produce the full CEREBRO INTELLIGENCE SCAN report.' \
  -f /tmp/vault-index.json \
  --model openrouter/anthropic/claude-sonnet-4

# Small vault — attach files directly
opencode run 'Run a CEREBRO intelligence scan across these notes.' \
  $(find /path/to/vault -name "*.md" | head -40 | xargs -I{} echo "-f {}")
```

### Codex

Codex requires a git repo and `pty=true`:

```bash
# Build index inside the vault directory first
python3 scripts/vault_parser.py /path/to/vault /path/to/vault/vault-index.json

# Run from inside the vault (must be a git repo)
codex --full-auto exec 'You are CEREBRO. Read vault-index.json, analyze relationships, save cerebro_report.md.'
```

If the vault is not a git repo:

```bash
TMPVAULT=$(mktemp -d)
cp -r /path/to/vault/. $TMPVAULT
cd $TMPVAULT && git init && git add -A && git commit -m 'init'
codex --full-auto exec 'Run a CEREBRO intelligence scan. Read all .md files and save cerebro_report.md.'
```

### OpenClaw

Trigger in chat, or push results to Telegram:

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

## Repository Structure

```
cerebro-skill/
├── SKILL.md          # Agent skill definition (all platforms)
├── scripts/
│   └── vault_parser.py   # Vault indexing script
├── output/           # Runtime reports (git-ignored)
└── README.md
```

---

---

## Use with LLM Wiki

> **LLM Wiki = your organized brain (structured knowledge)**
> **CEREBRO = your strategist (pattern recognition + decision engine)**

LLM Wiki systems are great at storing and retrieving knowledge. They're weak at strategy, prioritization, and insight generation. That's exactly where CEREBRO plugs in.

### The Simple Model

**LLM Wiki = Library + Memory**

Your vault structure already aligns:

```
vault/
├── raw/       → inbox (messy inputs)
├── wiki/      → clean structured knowledge
└── output/    → reports + deliverables
```

LLM Wiki answers: *"What is this?"* and *"Where is that?"*

**CEREBRO = Intelligence Layer**

CEREBRO sits on top of the wiki, not inside it. It processes relationships between notes, frequency of entities, connection density, and gaps and silos.

CEREBRO answers: *"What matters most right now?"*, *"What's connected that I'm missing?"*, *"Where is the opportunity?"*

---

### The Workflow

**Step 1 — Ingest (LLM Wiki)**

Drop content into `raw/`: grant notes, meeting notes, ideas, articles.

**Step 2 — Structure (LLM Wiki)**

Content moves into `wiki/` with tags, links, categories, and indexes.

**Step 3 — Parse (CEREBRO)**

```bash
python3 scripts/vault_parser.py /path/to/vault output/vault-index.json
```

Produces a link graph, tag index, entity map, and orphan detection. This is where your knowledge becomes machine-readable intelligence.

**Step 4 — Analyze (CEREBRO Skill)**

Run queries like:
- "Find strongest connections between initiatives"
- "Identify underutilized resources"
- "Detect repeated bottlenecks"
- "Map stakeholder overlap"

**Step 5 — Output (Strategic Reports)**

Into `output/` — Top Opportunities, Strategic Gaps, High-Value Connections, Action Recommendations.

---

### Real Example

Say your LLM Wiki contains: MSVL Sunset Concert Series, Taste of Juneteenth, Black Philanthropy Month, YESpvd, East 33.

**LLM Wiki alone** lets you find each program.

**CEREBRO** shows that:
- The same sponsors appear across 3 initiatives
- One initiative is under-leveraged
- One audience overlaps but isn't monetized
- A single partnership strategy could unlock all 5

That's strategy. That's leverage.

---

### Where This Gets Powerful

You're not building a note system. You're building a **decision engine for community ecosystems**.

| Capability | What it gives you |
|---|---|
| **Ecosystem Mapping** | Who connects to what, where influence actually lives |
| **Opportunity Detection** | Hidden partnerships, underused assets, funding gaps |
| **Strategic Prioritization** | What creates compound impact vs. what can wait |

---

### Intelligence Prompt (Plug-and-Play)

Use this prompt with your parsed vault index:

```
SYSTEM ROLE:
You are CEREBRO, a strategic intelligence engine operating on a structured knowledge vault.

OBJECTIVE:
Analyze the provided vault data and generate a strategic intelligence report focused on leverage, opportunity, and system-level insights.

INPUT:
- Entity map
- Tag index
- Link graph
- Orphan files
- Frequency distribution

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
Direct, strategic, no fluff. Focus on leverage and execution.
```

---

### CEREBRO OS — Full Stack Architecture

Stack the full system like this:

| Layer | Tool | Role |
|---|---|---|
| Knowledge Base | LLM Wiki / Obsidian / NotebookLM | Storage + retrieval |
| Structure Extractor | `vault_parser.py` | Machine-readable index |
| Reasoning Layer | Claude / OpenClaw / ChatGPT | Semantic analysis + strategy |
| Visualization | Google Sheets / Notion / Dashboard | Output + action tracking |

---

### Honest Gaps (Current State)

| Missing | Status |
|---|---|
| Real scoring models (impact, urgency, ROI) | Not yet built |
| Automation layer (continuous scans) | Planned |
| Visualization (graphs, dashboards) | Planned |
| Memory persistence across runs | Planned |

---

### Bottom Line

LLM Wiki helps you **know what you have.**
CEREBRO helps you **know what to do with it.**

Together: **information → intelligence → action.**

---

## Related Skills

- [`obsidian-vault-organizer`](https://github.com/microhustlestack) — clean and restructure a vault before scanning
- `obsidian-skills-vault-import` — import skills from the vault into OpenClaw/Hermes
- `cerebro-knowledge-export` — export insights to Notion, Google Docs, etc.

---

## License

MIT
