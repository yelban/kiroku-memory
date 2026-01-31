# Kiroku Memory

> Tiered Retrieval Memory System for AI Agents

An AI Agent long-term memory system based on Rohit's "How to Build an Agent That Never Forgets" design principles.

**Core Features**:
- Hybrid Memory Stack: Combines append-only logs, structured facts, and category summaries
- Tiered Retrieval: Summaries first, drill down as needed
- Time Decay: Memory confidence decays over time
- Conflict Resolution: Automatic contradiction detection and resolution

## Quick Start

```bash
# Start PostgreSQL + pgvector
docker compose up -d

# Start API
uv run uvicorn kiroku_memory.api:app --reload

# Health check
curl http://localhost:8000/health
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/memory
OPENAI_API_KEY=sk-xxx  # Required
```

## API Endpoints

### Core
| Method | Path | Description |
|--------|------|-------------|
| POST | /ingest | Ingest raw messages |
| GET | /retrieve | Tiered retrieval |
| GET | /context | Agent prompt context |

### Intelligence
| Method | Path | Description |
|--------|------|-------------|
| POST | /extract | Extract facts |
| POST | /summarize | Generate summaries |

### Maintenance
| Method | Path | Description |
|--------|------|-------------|
| POST | /jobs/nightly | Daily maintenance |
| POST | /jobs/weekly | Weekly maintenance |
| POST | /jobs/monthly | Monthly maintenance |

### Observability
| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /metrics | Application metrics |

## Integration Example

### Using in Other Agents

```javascript
// Get memory context
const context = await fetch("http://localhost:8000/context").then(r => r.json());

// Add to system prompt
const enhancedPrompt = `${context.context}\n\n${originalPrompt}`;

// Save important info after conversation
await fetch("http://localhost:8000/ingest", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ content: "User likes...", source: "my-agent" })
});
```

## Claude Code Integration

Full Claude Code integration implemented:

```
~/.claude/skills/kiroku-memory/
├── SKILL.md              # Documentation (EN)
├── SKILL.zh-TW.md        # Traditional Chinese
├── SKILL.ja.md           # Japanese
├── scripts/              # /remember, /recall, /forget, /memory-status
├── references/           # Reference docs
└── assets/               # Install script
```

**Features**:
- SessionStart hook auto-loads memory context
- Stop hook intelligently saves important conversations
- Manual commands for memory management

See `docs/claude-code-integration.md` for details.

## Documentation

- `docs/architecture.md` - Architecture design
- `docs/development-journey.md` - Development journey
- `docs/user-guide.md` - User guide
- `docs/integration-guide.md` - Integration guide
- `docs/claude-code-integration.md` - Claude Code integration guide
- `docs/renaming-changelog.md` - Renaming changelog

## Project Structure

```
kiroku-memory/
├── kiroku_memory/       # Core module
│   ├── api.py           # FastAPI endpoints
│   ├── ingest.py        # Resource ingestion
│   ├── extract.py       # Fact extraction
│   ├── classify.py      # Classifier
│   ├── conflict.py      # Conflict resolution
│   ├── summarize.py     # Summary generation
│   ├── embedding.py     # Vector search
│   ├── observability.py # Monitoring
│   ├── db/              # Database
│   └── jobs/            # Maintenance jobs
├── tests/               # Tests
├── docs/                # Documentation
├── docker-compose.yml   # PostgreSQL config
└── pyproject.toml       # Project config
```

## Development

- Language: Python 3.11+
- Framework: FastAPI + SQLAlchemy 2.x
- Database: PostgreSQL 16 + pgvector
- Package Manager: uv
- Testing: pytest + pytest-asyncio

## Common Commands

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Type check
uv run mypy kiroku_memory/
```

## Translations

- [繁體中文](CLAUDE.zh-TW.md)
- [日本語](CLAUDE.ja.md)
