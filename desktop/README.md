# Kiroku Memory Desktop

> A standalone macOS application for AI Agent long-term memory management

[繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

## What is Kiroku Memory?

Kiroku Memory is an AI Agent memory system that stores, organizes, and retrieves information across sessions. Unlike traditional chatbots that forget everything after each conversation, Kiroku Memory enables persistent memory.

**Desktop App Features:**
- **Zero Configuration** - No Python, Docker, or database setup required
- **One-Click Launch** - Double-click to start using immediately
- **Secure Storage** - API keys stored in macOS Keychain
- **Embedded Database** - SurrealDB runs locally, your data stays private

## Installation

### Option 1: Download DMG (Recommended)

1. Download `Kiroku Memory_x.x.x_aarch64.dmg` from [Releases](https://github.com/yelban/kiroku-memory/releases)
2. Open the DMG file
3. Drag **Kiroku Memory** to your **Applications** folder
4. Launch from Applications

#### macOS: First Launch (Unsigned App)

The app is not signed with an Apple Developer certificate. On first launch, macOS will block it.

**If you see "damaged and can't be opened":**

Run this command in Terminal to remove the quarantine attribute:

```bash
xattr -cr /Applications/Kiroku\ Memory.app
```

**If you see "can't be opened because Apple cannot check it":**

1. Right-click (or Control-click) on **Kiroku Memory.app**
2. Select **Open** from the context menu
3. Click **Open** in the dialog

Or go to **System Settings** → **Privacy & Security** → Click **Open Anyway**

After allowing once, the app will open normally in the future.

### Option 2: Build from Source

```bash
# Clone repository
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory

# Build Python runtime (first time only)
bash tools/packaging/build-python.sh

# Build Desktop App
cd desktop
npm install
npm run tauri build
```

The built app will be at: `desktop/src-tauri/target/release/bundle/macos/Kiroku Memory.app`

## Getting Started

### 1. Launch the App

Double-click **Kiroku Memory.app**. The app will:
- Start the embedded Python service automatically
- Initialize the local SurrealDB database
- Display a green status indicator when ready

### 2. Configure OpenAI API Key (Optional)

**Most features work without an API key.** Only configure if you need semantic search:

| Feature | Without API Key | With API Key |
|---------|-----------------|--------------|
| Store memories | ✅ | ✅ |
| Browse memories | ✅ | ✅ |
| Keyword search | ✅ | ✅ |
| **Semantic search** | ❌ | ✅ |

To enable semantic search:

1. Go to **Settings** tab
2. Enter your OpenAI API Key
3. Click **Save**

Your key is securely stored in macOS Keychain, not in plain text files.

### 3. Start Using

**Status Dashboard**
- View service health and version
- Monitor memory statistics
- Check database status

**Memory Browser**
- Browse stored memories
- Search by keyword
- Filter by category (preferences, facts, goals, etc.)
- View detailed memory information

**Settings**
- Configure OpenAI API Key (optional)
- Toggle auto-start service

**Maintenance**
- Restart service
- View data directory location
- Open Finder at data location

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                   Kiroku Memory.app                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   React     │    │   Tauri     │    │   Python    │ │
│  │   Frontend  │◄──►│   (Rust)    │◄──►│   FastAPI   │ │
│  │             │    │             │    │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                              │          │
│                                              ▼          │
│                                        ┌─────────────┐ │
│                                        │  SurrealDB  │ │
│                                        │  (embedded) │ │
│                                        └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Technology Stack:**
- **Frontend**: React 19 + Vite + Tailwind CSS + shadcn/ui
- **Shell**: Tauri v2 (Rust)
- **Backend**: Python 3.11 (bundled) + FastAPI
- **Database**: SurrealDB (embedded, file-based)

## Data Storage

All data is stored locally on your machine:

```
~/Library/Application Support/com.kiroku.memory/
├── surrealdb/
│   └── kiroku/          # Database files
└── settings.json        # App settings (non-sensitive)
```

OpenAI API Key is stored separately in **macOS Keychain** for security.

## Integration with Claude Code

Kiroku Memory Desktop works alongside the [Claude Code Skill](../skill/SKILL.md):

| Feature | Desktop App | Claude Code Skill |
|---------|-------------|-------------------|
| Memory Storage | Local SurrealDB | Same API |
| Memory Retrieval | GUI Browser | `/recall` command |
| Auto-capture | Manual | SessionStart/Stop hooks |
| Use Case | Visual management | In-conversation memory |

Both can connect to the same API at `http://127.0.0.1:8000`.

## Troubleshooting

### Service Won't Start

1. Check if port 8000 is in use:
   ```bash
   lsof -i :8000
   ```
2. Try restarting from Maintenance tab
3. Check Console.app for error logs

### Memory Not Appearing

1. Ensure service status shows "Running" (green indicator)
2. Check if OpenAI API Key is configured (required for extraction)
3. Try manual refresh in Memory Browser

### App Crashes on Launch

1. Delete app data and try again:
   ```bash
   rm -rf ~/Library/Application\ Support/com.kiroku.memory/
   ```
2. Re-download and reinstall the app

## System Requirements

- **OS**: macOS 10.15 (Catalina) or later
- **Architecture**: Apple Silicon (aarch64) or Intel (x86_64)
- **Disk Space**: ~200 MB for app + data
- **RAM**: 512 MB minimum

## Privacy & Security

- **All data stays local** - No cloud sync, no telemetry
- **API keys in Keychain** - Never stored in plain text
- **No network required** - Works fully offline (except OpenAI features)

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Related

- [Kiroku Memory API Documentation](../docs/user-guide.md)
- [Claude Code Integration](../docs/claude-code-integration.md)
- [Architecture Overview](../docs/architecture.md)
