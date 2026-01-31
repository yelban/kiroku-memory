#!/bin/bash
#
# Kiroku Memory - Claude Code Skill Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash
#
# Or run locally:
#   ./install.sh
#
# Environment variables:
#   KIROKU_API - API endpoint (default: http://localhost:8000)
#   SKILL_DIR  - Installation directory (default: ~/.claude/skills/kiroku-memory)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKILL_NAME="kiroku-memory"
SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills/$SKILL_NAME}"
SETTINGS_FILE="$HOME/.claude/settings.json"
REPO_URL="https://github.com/yelban/kiroku-memory.git"

echo "╔════════════════════════════════════════╗"
echo "║     Kiroku Memory Skill Installer      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check dependencies
check_deps() {
    local missing=()

    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi

    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}✗ Missing dependencies: ${missing[*]}${NC}"
        exit 1
    fi
}

# Detect installation source
detect_source() {
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    POTENTIAL_SKILL_SRC="$(dirname "$SCRIPT_DIR")"

    # Check if running from local skill directory
    if [ -f "$POTENTIAL_SKILL_SRC/skill.md" ] && [ -d "$POTENTIAL_SKILL_SRC/scripts" ]; then
        SKILL_SRC="$POTENTIAL_SKILL_SRC"
        echo "Installing from local: $SKILL_SRC"
    else
        # Running from piped curl, clone the repo
        echo "Downloading from repository..."
        TMP_DIR=$(mktemp -d)
        if ! git clone --depth 1 "$REPO_URL" "$TMP_DIR" 2>/dev/null; then
            echo -e "${RED}✗ Failed to clone repository${NC}"
            exit 1
        fi
        SKILL_SRC="$TMP_DIR/skill"
    fi
}

# Install skill files
install_skill() {
    echo "Installing skill to $SKILL_DIR..."

    # Create directories
    mkdir -p "$SKILL_DIR"/{scripts,references,assets}

    # Copy files
    cp "$SKILL_SRC/skill.md" "$SKILL_DIR/"
    cp "$SKILL_SRC/scripts/"*.py "$SKILL_DIR/scripts/"
    cp "$SKILL_SRC/references/"*.md "$SKILL_DIR/references/" 2>/dev/null || true
    cp "$SKILL_SRC/assets/"* "$SKILL_DIR/assets/" 2>/dev/null || true

    # Make scripts executable
    chmod +x "$SKILL_DIR/scripts/"*.py

    # Create bin/ symlinks for backward compatibility
    mkdir -p "$SKILL_DIR/bin"
    ln -sf "../scripts/remember.py" "$SKILL_DIR/bin/remember"
    ln -sf "../scripts/recall.py" "$SKILL_DIR/bin/recall"
    ln -sf "../scripts/forget.py" "$SKILL_DIR/bin/forget"
    ln -sf "../scripts/memory-status.py" "$SKILL_DIR/bin/memory-status"

    echo -e "${GREEN}✓ Skill files installed${NC}"
}

# Configure hooks in settings.json
configure_hooks() {
    echo "Configuring Claude Code hooks..."

    # Create settings.json if not exists
    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$(dirname "$SETTINGS_FILE")"
        echo '{}' > "$SETTINGS_FILE"
    fi

    # Backup existing settings
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"

    # Use Python to safely merge JSON
    python3 << 'PYTHON_SCRIPT'
import json
import os

settings_file = os.path.expanduser("~/.claude/settings.json")
skill_dir = os.path.expanduser("~/.claude/skills/kiroku-memory")

# Load existing settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Ensure hooks structure exists
if 'hooks' not in settings:
    settings['hooks'] = {}

# SessionStart hook
session_start_hook = {
    "matcher": "",
    "hooks": [{
        "type": "command",
        "command": f"python3 {skill_dir}/scripts/session-start-hook.py",
        "timeout": 5,
        "statusMessage": "Loading Kiroku Memory..."
    }]
}

# Stop hook
stop_hook = {
    "matcher": "",
    "hooks": [{
        "type": "command",
        "command": f"python3 {skill_dir}/scripts/stop-hook.py",
        "timeout": 10,
        "async": True
    }]
}

# Check if hooks already exist (avoid duplicates)
def hook_exists(hook_list, command_pattern):
    for h in hook_list:
        for inner in h.get('hooks', []):
            if command_pattern in inner.get('command', ''):
                return True
    return False

# Add SessionStart hook
if 'SessionStart' not in settings['hooks']:
    settings['hooks']['SessionStart'] = []
if not hook_exists(settings['hooks']['SessionStart'], 'kiroku-memory'):
    settings['hooks']['SessionStart'].append(session_start_hook)

# Add Stop hook
if 'Stop' not in settings['hooks']:
    settings['hooks']['Stop'] = []
if not hook_exists(settings['hooks']['Stop'], 'kiroku-memory'):
    settings['hooks']['Stop'].append(stop_hook)

# Save updated settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("Hooks configured successfully")
PYTHON_SCRIPT

    echo -e "${GREEN}✓ Hooks configured${NC}"
}

# Verify installation
verify_installation() {
    echo ""
    echo "Verifying installation..."

    local errors=0

    # Check skill files
    if [ -f "$SKILL_DIR/skill.md" ]; then
        echo -e "  ${GREEN}✓${NC} skill.md"
    else
        echo -e "  ${RED}✗${NC} skill.md missing"
        errors=$((errors + 1))
    fi

    # Check scripts
    for script in remember recall forget memory-status session-start-hook stop-hook; do
        if [ -f "$SKILL_DIR/scripts/${script}.py" ]; then
            echo -e "  ${GREEN}✓${NC} scripts/${script}.py"
        else
            echo -e "  ${RED}✗${NC} scripts/${script}.py missing"
            errors=$((errors + 1))
        fi
    done

    # Check hooks in settings
    if grep -q "kiroku-memory" "$SETTINGS_FILE" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Hooks in settings.json"
    else
        echo -e "  ${YELLOW}⚠${NC} Hooks not found in settings.json"
    fi

    return $errors
}

# Print usage instructions
print_usage() {
    echo ""
    echo "════════════════════════════════════════"
    echo -e "${GREEN}Installation complete!${NC}"
    echo "════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start Kiroku Memory service:"
    echo "   ${YELLOW}cd /path/to/kiroku-memory${NC}"
    echo "   ${YELLOW}docker compose up -d${NC}"
    echo "   ${YELLOW}uv run uvicorn kiroku_memory.api:app --reload${NC}"
    echo ""
    echo "2. Restart Claude Code to load hooks"
    echo ""
    echo "3. Test with:"
    echo "   ${YELLOW}/memory-status${NC}"
    echo "   ${YELLOW}/remember 測試記憶${NC}"
    echo "   ${YELLOW}/recall 測試${NC}"
    echo ""
    echo "Documentation: $SKILL_DIR/skill.md"
    echo ""
}

# Uninstall function
uninstall() {
    echo "Uninstalling Kiroku Memory skill..."

    # Remove skill directory
    if [ -d "$SKILL_DIR" ]; then
        rm -rf "$SKILL_DIR"
        echo -e "${GREEN}✓${NC} Removed $SKILL_DIR"
    fi

    # Remove hooks from settings (manual step)
    echo ""
    echo -e "${YELLOW}⚠${NC} Please manually remove Kiroku Memory hooks from:"
    echo "   $SETTINGS_FILE"
    echo ""
    echo "Look for entries containing 'kiroku-memory' in the 'hooks' section."
}

# Main
main() {
    # Handle uninstall flag
    if [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]; then
        uninstall
        exit 0
    fi

    check_deps
    detect_source
    install_skill
    configure_hooks

    if verify_installation; then
        print_usage
    else
        echo ""
        echo -e "${RED}Installation completed with errors. Please check above.${NC}"
        exit 1
    fi

    # Cleanup temp directory if used
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}

main "$@"
