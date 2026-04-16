# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

This is a **skill definition** for AI agent frameworks (OpenClaw, Claude Code). It contains a single `SKILL.md` file that specifies how an agent should use the external `cerebro` CLI tool to scan and synthesize insights from markdown knowledge bases.

There is no source code, build system, or test suite — the skill is purely declarative.

## Skill Architecture

The skill acts as a bridge between an AI agent and the external `cerebro` binary:

```
Agent → SKILL.md (instructions) → cerebro binary → markdown report
```

**Workflow:**
1. Agent provides a root directory of `.md` files (e.g., an Obsidian vault)
2. Agent runs `cerebro scan <dir>` to index documents
3. Agent runs `cerebro query "<question>"` to extract relationships/themes
4. Cerebro outputs a structured markdown report (`cerebro_report.md`)

## External Dependency

The `cerebro` binary must be installed and available in `$PATH`. If absent, the skill cannot function — check with `which cerebro` before invoking.

## Output Contract

Every execution must produce a markdown report with exactly these three sections:

```
## Key Concepts
## Relationship Map
## Summary
```

If the output is missing any section, the execution is incomplete.

## Modifying the Skill

Edit `SKILL.md` only. Follow the standard skill format used across this machine's skill ecosystem (frontmatter with `name` and `description`, then `## When to Use`, steps, examples, output format, pitfalls, related skills, verification).

After editing, deploy by copying to the appropriate skills directory:
- OpenClaw shared skills: `~/.openclaw/shared-skills/`
- ZeroClaw workspace skills: `~/.zeroclaw/workspace/skills/`
- Obsidian vault (canonical source): `~/Documents/Obsidian/Skills-Vault/`
