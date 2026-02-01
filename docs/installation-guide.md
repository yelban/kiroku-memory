# Installation Guide

> Step-by-step instructions for installing Kiroku Memory on macOS

**Language**: [English](installation-guide.md) | [繁體中文](installation-guide.zh-TW.md) | [日本語](installation-guide.ja.md)

---

## Prerequisites

- **macOS** (currently supported)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

---

## Step 1: Install Docker Desktop

Docker runs the PostgreSQL database that Kiroku Memory needs.

1. Download from: https://www.docker.com/products/docker-desktop
2. Open the downloaded `.dmg` file
3. Drag Docker to Applications
4. Launch Docker from Applications
5. Wait for Docker to fully start

**Success indicator**: You'll see a whale icon 🐳 in the menu bar (top-right of screen)

**Troubleshooting**:
- If Docker asks for permissions, click "OK" to grant them
- First launch may take 1-2 minutes to initialize

---

## Step 2: Install uv (Python Package Manager)

uv is a fast Python package manager we use instead of pip.

Open Terminal and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation completes, **restart Terminal** or run:

```bash
source ~/.zshrc
```

**Verify installation**:

```bash
uv --version
```

Should output something like: `uv 0.5.x`

---

## Step 3: Download Kiroku Memory

Choose a directory for the project (e.g., `~/projects`):

```bash
# Create projects directory if it doesn't exist
mkdir -p ~/projects
cd ~/projects

# Clone the repository
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory
```

---

## Step 4: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Open in your editor
open -e .env   # Opens in TextEdit
# Or use: nano .env / vim .env / code .env
```

**Edit the file and set your OpenAI API Key**:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Save and close the file.

---

## Step 5: Start the Database

```bash
docker compose up -d
```

**Success indicator**:
```
✔ Container kiroku-memory-db  Started
```

**Troubleshooting**:
- If you see "Cannot connect to the Docker daemon", make sure Docker Desktop is running
- First run downloads the PostgreSQL image (~400MB), please wait

---

## Step 6: Install Python Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all required packages.

**Success indicator**: No errors, ends with packages installed

---

## Step 7: Start the API Service

```bash
uv run uvicorn kiroku_memory.api:app --reload
```

**Success indicator**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

**Keep this terminal open** - the API runs in the foreground.

**Verify it's working** (in a new terminal):

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok","version":"0.1.0"}
```

---

## Step 8: Install Claude Code Skill

Open a **new terminal window** (keep the API running), then:

```bash
cd ~/projects/kiroku-memory
./skill/assets/install.sh
```

This copies the skill files to `~/.claude/skills/kiroku-memory/`.

---

## Step 9: Restart Claude Code

1. Close Claude Code completely
2. Reopen Claude Code

**Success indicator**: At conversation start, you'll see:
```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context
...
</kiroku-memory>
```

---

## Installation Complete! 🎉

You can now use:

| Command | Description |
|---------|-------------|
| `/remember <text>` | Store a memory |
| `/recall <query>` | Search memories |
| `/memory-status` | Check system status |

---

## Advanced: Auto-Start API Service (launchd)

Don't want to manually start the API every time? Use launchd to auto-start at login.

### Create the plist file

```bash
cat > ~/Library/LaunchAgents/com.kiroku-memory.api.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kiroku-memory.api</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/.local/bin/uv</string>
        <string>run</string>
        <string>uvicorn</string>
        <string>kiroku_memory.api:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/projects/kiroku-memory</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/YOUR_USERNAME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/kiroku-api.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/kiroku-api.err</string>
</dict>
</plist>
EOF
```

**Important**: Replace `YOUR_USERNAME` with your actual macOS username.

Find your username:
```bash
whoami
```

### Edit the plist file

```bash
# Replace YOUR_USERNAME with actual username
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### Load the service

```bash
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### Verify it's running

```bash
# Check service status
launchctl list | grep kiroku

# Test the API
curl http://localhost:8000/health
```

### View logs

```bash
# Standard output
tail -f /tmp/kiroku-api.log

# Error log
tail -f /tmp/kiroku-api.err
```

### Stop/Unload the service

```bash
# Stop and unload
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# To restart after changes
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

---

## Troubleshooting

### "Connection refused" when accessing API

1. Check if Docker is running (whale icon in menu bar)
2. Check if database container is running: `docker ps`
3. Check if API is running: `curl http://localhost:8000/health`

### "uv: command not found"

Restart your terminal, or run:
```bash
source ~/.zshrc
```

### "OPENAI_API_KEY not set"

Make sure you've:
1. Created the `.env` file: `cp .env.example .env`
2. Added your actual API key (not the placeholder)

### API starts but immediately exits

Check the error log:
```bash
cat /tmp/kiroku-api.err
```

Common causes:
- Invalid OpenAI API key
- Database not running
- Port 8000 already in use

### launchd service not starting

1. Check for plist syntax errors:
   ```bash
   plutil -lint ~/Library/LaunchAgents/com.kiroku-memory.api.plist
   ```

2. Verify paths exist:
   ```bash
   ls -la ~/.local/bin/uv
   ls -la ~/projects/kiroku-memory
   ```

---

## Uninstallation

```bash
# Stop launchd service (if installed)
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist 2>/dev/null
rm ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# Remove Claude Code skill
rm -rf ~/.claude/skills/kiroku-memory

# Stop and remove Docker container
cd ~/projects/kiroku-memory
docker compose down -v

# Remove project directory
rm -rf ~/projects/kiroku-memory
```
