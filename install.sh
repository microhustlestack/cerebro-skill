#!/usr/bin/env bash
#
# CEREBRO installer.
#
#   bash install.sh              # install package + deploy skill everywhere detected
#   bash install.sh claude       # one target only
#   bash install.sh hermes openclaw
#
# Targets: claude | hermes | openclaw | package
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info() { printf '  %s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }

install_package() {
  info "Installing cerebro package (Python $(python3 --version 2>&1 | cut -d' ' -f2))"
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
    warn "Python 3.11+ required; found $(python3 --version 2>&1)"
    return 1
  fi
  # --user keeps this out of system site-packages; falls back for managed envs.
  python3 -m pip install -e "$REPO_DIR" --user --quiet \
    || python3 -m pip install -e "$REPO_DIR" --user --quiet --break-system-packages
  if command -v cerebro >/dev/null 2>&1; then
    ok "cerebro entrypoint: $(command -v cerebro)"
  else
    warn "cerebro installed but not on PATH — add ~/.local/bin to PATH"
    warn "or invoke via: python3 $REPO_DIR/scripts/vault_parser.py"
  fi
}

deploy_skill() {
  local name="$1" dest="$2"
  mkdir -p "$dest/scripts"
  cp "$REPO_DIR/SKILL.md" "$dest/SKILL.md"
  cp "$REPO_DIR/scripts/vault_parser.py" "$dest/scripts/vault_parser.py"
  cp -r "$REPO_DIR/src" "$dest/src"
  ok "$name -> $dest"
}

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  targets=(package claude hermes openclaw)
fi

echo "CEREBRO installer"
echo

for target in "${targets[@]}"; do
  case "$target" in
    package)
      install_package || warn "package install failed; skill files still deployable"
      ;;
    claude)
      deploy_skill "Claude Code" "$HOME/.claude/skills/cerebro"
      ;;
    hermes)
      if [ -d "$HOME/.hermes" ]; then
        deploy_skill "Hermes" "$HOME/.hermes/skills/research/cerebro"
      else
        info "Hermes not detected, skipping"
      fi
      ;;
    openclaw)
      if [ -d "$HOME/.openclaw" ]; then
        deploy_skill "OpenClaw" "$HOME/.openclaw/shared-skills/cerebro"
      else
        info "OpenClaw not detected, skipping"
      fi
      ;;
    *)
      warn "unknown target: $target (use: package|claude|hermes|openclaw)"
      ;;
  esac
done

echo
echo "Done. Try:"
echo "  cerebro /path/to/your/vault --gaps --report cerebro_report.md"
