#!/usr/bin/env bash
# Install / update the macOS launchd job that runs one tracker tick every N minutes.
#   ./scripts/install_launchd.sh            # uses config.json interval (fixed -> minutes, adaptive -> min)
#   ./scripts/install_launchd.sh uninstall
set -euo pipefail

LABEL="com.goldtracker.ahmedabad"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="${PYTHON:-$(command -v python3)}"

if [[ "${1:-}" == "uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "uninstalled $LABEL"
  exit 0
fi

MINUTES="$("$PY" - "$REPO/config.json" <<'EOF'
import json, sys
iv = json.load(open(sys.argv[1])).get("interval", {})
print(iv.get("min", 30) if iv.get("mode") == "adaptive" else iv.get("minutes", 30))
EOF
)"
SECONDS_=$(( MINUTES * 60 ))
mkdir -p "$REPO/state" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string><string>-m</string><string>goldtracker</string><string>run</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartInterval</key><integer>$SECONDS_</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/state/launchd.log</string>
  <key>StandardErrorPath</key><string>$REPO/state/launchd.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>PYTHONUNBUFFERED</key><string>1</string></dict>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL -> every $MINUTES min, python=$PY"
echo "logs:   tail -f $REPO/state/launchd.log"
echo "status: launchctl print gui/$(id -u)/$LABEL | head -20"
