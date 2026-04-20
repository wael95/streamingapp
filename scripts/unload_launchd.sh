#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/Library/LaunchAgents"
for name in com.user.stockagent.bridge com.user.stockagent.agent; do
  OUT="$DEST/$name.plist"
  if [ -f "$OUT" ]; then
    launchctl unload -w "$OUT" || true
    rm -f "$OUT"
    echo "unloaded: $OUT"
  fi
done
