#!/bin/bash
# Install Kiroku Memory launchd jobs
# Run: bash launchd/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "Installing Kiroku Memory scheduled jobs..."

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS"

# Copy plist files
for plist in nightly weekly monthly; do
    src="$SCRIPT_DIR/com.kiroku-memory.$plist.plist"
    dst="$LAUNCH_AGENTS/com.kiroku-memory.$plist.plist"

    # Unload if already loaded
    launchctl unload "$dst" 2>/dev/null || true

    # Copy and load
    cp "$src" "$dst"
    launchctl load "$dst"
    echo "✓ $plist job installed"
done

echo ""
echo "Schedule:"
echo "  nightly: 03:00 daily"
echo "  weekly:  04:00 Sunday"
echo "  monthly: 05:00 1st of month"
echo ""
echo "Logs: /tmp/kiroku-*.log"
echo ""
echo "Commands:"
echo "  launchctl list | grep kiroku  # Check status"
echo "  launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.*.plist  # Disable"
