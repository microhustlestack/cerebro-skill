#!/usr/bin/env bash
#
# CEREBRO installer.
#
#   bash install.sh              # package + Claude; detected Hermes/OpenClaw
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
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    python3 -m pip install -e "$REPO_DIR" --quiet || return 1
  else
    # --user keeps this out of system site-packages; the second form supports
    # distributions that enforce PEP 668 for the system interpreter.
    python3 -m pip install -e "$REPO_DIR" --user --quiet \
      || python3 -m pip install -e "$REPO_DIR" --user --quiet --break-system-packages \
      || return 1
  fi
  python3 -c 'import cerebro; print("  installed cerebro " + cerebro.__version__)' \
    || return 1
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
auto_targets=0
if [ ${#targets[@]} -eq 0 ]; then
  targets=(package claude hermes openclaw)
  auto_targets=1
fi

echo "CEREBRO installer"
echo

status=0
package_installed=0

for target in "${targets[@]}"; do
  case "$target" in
    package)
      if install_package; then
        package_installed=1
      else
        warn "package install failed; skill files were not affected"
        status=1
      fi
      ;;
    claude)
      deploy_skill "Claude Code" "$HOME/.claude/skills/cerebro"
      ;;
    hermes)
      if [ -d "$HOME/.hermes" ] || [ "$auto_targets" -eq 0 ]; then
        deploy_skill "Hermes" "$HOME/.hermes/skills/research/cerebro"
      else
        info "Hermes not detected, skipping"
      fi
      ;;
    openclaw)
      if [ -d "$HOME/.openclaw" ] || [ "$auto_targets" -eq 0 ]; then
        deploy_skill "OpenClaw" "$HOME/.openclaw/shared-skills/cerebro"
      else
        info "OpenClaw not detected, skipping"
      fi
      ;;
    *)
      warn "unknown target: $target (use: package|claude|hermes|openclaw)"
      status=1
      ;;
  esac
done

echo
if [ "$status" -eq 0 ]; then
  echo "Done."
  if [ "$package_installed" -eq 1 ]; then
    echo "Try: cerebro /path/to/your/vault --gaps --report cerebro_report.md"
  else
    echo "The requested agent skill target is ready."
  fi
else
  warn "Completed with errors; review the messages above"
fi

exit "$status"
