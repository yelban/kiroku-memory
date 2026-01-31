---
name: kiroku-memory
description: |
  AI Agent long-term memory system with cross-session, cross-project persistence.
  Triggers:
  - /remember - Store memories to system
  - /recall - Search memories
  - /forget - Delete or archive memories
  - /memory-status - Check memory system status
  - Need to persist important information from AI conversations
  - Need to share user preferences across projects
---

# Kiroku Memory

AI Agent long-term memory system. Supports cross-session, cross-project memory management.

## Commands

| Command | Description |
|---------|-------------|
| `/remember <content>` | Store a memory |
| `/recall <query>` | Search memories |
| `/forget <query>` | Delete/archive memories |
| `/memory-status` | Check memory status |

## Usage Examples

```bash
# Store a memory
/remember User prefers dark mode

# Store with category
/remember --category preferences Likes using Neovim

# Store as global memory
/remember --global Nickname is ChuiChui

# Search memories
/recall editor preferences

# Get full context
/recall --context

# Check status
/memory-status
```

## Memory Scopes

- **Global** (`global:user`): Cross-project, personal preferences
- **Project** (`project:<name>`): Project-specific, architecture decisions

Default behavior:
- In project directory → saves to project memory
- No project context → saves to global memory

## Categories

| Category | Description |
|----------|-------------|
| `preferences` | User preferences |
| `facts` | Factual information |
| `events` | Events and activities |
| `relationships` | People and connections |
| `skills` | Skills and expertise |
| `goals` | Goals and plans |

## Documentation

- [API Contract](references/api-contract.md)
- [Memory Scopes](references/scopes.md)
- [Filtering Rules](references/filtering-rules.md)
- [Retrieval Policy](references/retrieval-policy.md)

## Installation

```bash
# One-click install
curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash

# Or manual install
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory/skill/assets && ./install.sh
```

The installer creates:
- `~/.claude/skills/kiroku-memory/` - Main skill with scripts and hooks
- `~/.claude/skills/remember/` - Alias for `/remember` command
- `~/.claude/skills/recall/` - Alias for `/recall` command
- `~/.claude/skills/forget/` - Alias for `/forget` command
- `~/.claude/skills/memory-status/` - Alias for `/memory-status` command

## Prerequisites

Kiroku Memory service must be running:

```bash
cd ~/path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
```

Default API endpoint: `http://localhost:8000` (override with `KIROKU_API` env var)

## Translations

- [繁體中文](SKILL.zh-TW.md)
- [日本語](SKILL.ja.md)
