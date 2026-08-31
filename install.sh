#!/usr/bin/env bash
# VESTRIK installer
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info() { printf '  %s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }

install_package() {
  info "Installing VESTRIK package (Python $(python3 --version 2>&1 | cut -d' ' -f2))"
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
    warn "Python 3.11+ required; found $(python3 --version 2>&1)"
    return 1
  fi
  python3 -m pip install -e "$REPO_DIR" --user --quiet \
    || python3 -m pip install -e "$REPO_DIR" --user --quiet --break-system-packages
  if command -v vestrik >/dev/null 2>&1; then
    ok "vestrik entrypoint: $(command -v vestrik)"
  else
    warn "vestrik installed but not on PATH — add ~/.local/bin to PATH"
  fi
}

deploy_skill() {
  local name="$1" dest="$2"
  mkdir -p "$dest"
  cp "$REPO_DIR/SKILL.md" "$dest/SKILL.md"
  cp -r "$REPO_DIR/src" "$dest/src"
  ok "$name -> $dest"
}

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then targets=(package claude hermes openclaw); fi

echo "VESTRIK // installer"
echo
for target in "${targets[@]}"; do
  case "$target" in
    package) install_package || warn "package install failed; skill files still deployable" ;;
    claude) deploy_skill "Claude Code" "$HOME/.claude/skills/vestrik" ;;
    hermes)
      if [ -d "$HOME/.hermes" ]; then deploy_skill "Hermes" "$HOME/.hermes/skills/research/vestrik"; else info "Hermes not detected, skipping"; fi ;;
    openclaw)
      if [ -d "$HOME/.openclaw" ]; then deploy_skill "OpenClaw" "$HOME/.openclaw/shared-skills/vestrik"; else info "OpenClaw not detected, skipping"; fi ;;
    *) warn "unknown target: $target (use: package|claude|hermes|openclaw)" ;;
  esac
done

echo
echo "Done. Try:"
echo "  vestrik /path/to/your/vault --gaps --report vestrik_report.md"
