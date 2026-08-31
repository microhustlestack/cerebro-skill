# VESTRIK // Claude Code Guidance

VESTRIK // VAULT is structured knowledge intelligence for markdown vaults.

## Engineering rule for this rebrand

Treat the VESTRIK migration as an identity/package migration only. Do not mix in parser, scoring, graph,
urgency or gap-analysis refactors. Preserve observable behavior unless a change is explicitly documented as
compatibility-related.

## Canonical interfaces

- Python: `from vestrik import VaultParser`
- CLI: `vestrik`
- Agent Skill: `name: vestrik`
- Claude install path: `~/.claude/skills/vestrik/`

The `cerebro` package and CLI remain temporary compatibility surfaces for existing users. New documentation and
examples should use VESTRIK.
