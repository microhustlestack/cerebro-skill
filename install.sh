#!/usr/bin/env bash
# cerebro-skill installer
# Usage: bash install.sh [platform]
# Platforms: hermes, openclaw, claude-code, all (default: all)

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PLATFORM="${1:-all}"

install_hermes() {
  DEST="$HOME/.hermes/skills/research/cerebro"
  mkdir -p "$DEST/scripts" "$DEST/output"
  cp "$SKILL_DIR/SKILL.md" "$DEST/"
  cp "$SKILL_DIR/scripts/vault_parser.py" "$DEST/scripts/"
  echo "Hermes: installed to $DEST"
}

install_openclaw() {
  DEST="$HOME/.openclaw/shared-skills/cerebro"
  mkdir -p "$DEST/scripts" "$DEST/output"
  cp "$SKILL_DIR/SKILL.md" "$DEST/"
  cp "$SKILL_DIR/scripts/vault_parser.py" "$DEST/scripts/"
  echo "OpenClaw: installed to $DEST"
}

install_claude_code() {
  DEST="$HOME/.claude/skills/cerebro"
  mkdir -p "$DEST/scripts" "$DEST/output"
  cp "$SKILL_DIR/SKILL.md" "$DEST/"
  cp "$SKILL_DIR/CLAUDE.md" "$DEST/"
  cp "$SKILL_DIR/scripts/vault_parser.py" "$DEST/scripts/"
  echo "Claude Code: installed to $DEST"
}

case "$PLATFORM" in
  hermes)      install_hermes ;;
  openclaw)    install_openclaw ;;
  claude-code) install_claude_code ;;
  all)
    install_hermes
    install_openclaw
    install_claude_code
    ;;
  *)
    echo "Unknown platform: $PLATFORM"
    echo "Usage: bash install.sh [hermes|openclaw|claude-code|all]"
    exit 1
    ;;
esac

echo ""
echo "cerebro-skill v2.0.0 installed."
echo ""
echo "Quick test:"
echo "  python3 $HOME/.claude/skills/cerebro/scripts/vault_parser.py /path/to/vault"
