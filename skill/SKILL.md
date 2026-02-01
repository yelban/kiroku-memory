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

| Category | Priority | Description |
|----------|----------|-------------|
| `preferences` | 1.0 | User preferences (highest priority) |
| `facts` | 0.9 | Factual information |
| `goals` | 0.7 | Goals and plans |
| `skills` | 0.6 | Skills and expertise |
| `relationships` | 0.5 | People and connections |
| `events` | 0.4 | Events and activities (lowest priority) |

## Priority Ordering & Smart Truncation

### Hybrid Priority Model

Categories are ordered by priority, not alphabetically:
- **Static weight**: Base priority defined above
- **Dynamic factors**: Usage frequency + recency

```
priority = static_weight × (1.0 + usage_weight × usage_score + recency_weight × recency_score)
```

### Smart Truncation

When context exceeds limit (default 2000 chars):
- **Never truncates mid-category**: Drops complete categories instead
- **Priority-based**: Lower priority categories dropped first
- **Maintains formatting**: No broken markdown

## Documentation

- [API Contract](references/api-contract.md)
- [Memory Scopes](references/scopes.md)
- [Filtering Rules](references/filtering-rules.md)
- [Retrieval Policy](references/retrieval-policy.md)

## Auto-Save: Two-Phase Memory Capture

Stop Hook uses a **Fast + Slow** dual-phase architecture:

### Phase 1: Fast Path (<1s, sync)

Regex-based pattern matching for immediate capture:

| Pattern Type | Examples |
|--------------|----------|
| Preferences | `I prefer...`, `I like...` |
| Decisions | `decided to use...`, `chose...` |
| Discoveries | `discovered...`, `found that...`, `solution is...` |
| Learnings | `learned...`, `root cause...`, `the issue was...` |

Also extracts **conclusion markers** from Claude's responses:
- `解決方案/Solution`, `發現/Discovery`, `結論/Conclusion`
- `建議/Recommendation`, `根因/Root cause`

### Phase 2: Slow Path (5-15s, async)

Background LLM analysis using Claude CLI:

- Runs in detached subprocess (doesn't block Claude Code)
- Analyzes last 6 user + 4 assistant messages
- Extracts up to 5 memories with type/confidence
- Memory types: `discovery`, `decision`, `learning`, `preference`, `fact`
- Logs to `~/.cache/kiroku-memory/llm-worker.log`

Both phases share a 24-hour deduplication cache.

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
