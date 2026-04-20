#!/usr/bin/env bash
# Install both launchd agents into ~/Library/LaunchAgents and load them.
# Safe to re-run — it replaces existing installs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents"
mkdir -p "$DEST" "$REPO_ROOT/logs"

for name in com.user.stockagent.bridge com.user.stockagent.agent; do
  SRC="$REPO_ROOT/launchd/$name.plist"
  OUT="$DEST/$name.plist"
  sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$SRC" > "$OUT"
  launchctl unload -w "$OUT" 2>/dev/null || true
  launchctl load -w "$OUT"
  echo "loaded: $OUT"
done

echo "tail -f $REPO_ROOT/logs/*.log"
