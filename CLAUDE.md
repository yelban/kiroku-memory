# Kiroku Memory

> Tiered Retrieval Memory System for AI Agents

An AI Agent long-term memory system based on Rohit's "How to Build an Agent That Never Forgets" design principles.

**Core Features**:
- Hybrid Memory Stack: Combines append-only logs, structured facts, and category summaries
- Tiered Retrieval: Summaries first, drill down as needed
- Time Decay: Memory confidence decays over time
- Conflict Resolution: Automatic contradiction detection and resolution

## Quick Start

### Option A: PostgreSQL (Production)

```bash
# Start PostgreSQL + pgvector
docker compose up -d

# Start API
uv run uvicorn kiroku_memory.api:app --reload
```

### Option B: SurrealDB (Desktop/Embedded)

```bash
# Install SurrealDB dependency
uv sync --extra surrealdb

# Configure backend
echo "BACKEND=surrealdb" >> .env

# Start API (no Docker needed!)
uv run uvicorn kiroku_memory.api:app --reload
```

See `docs/surrealdb-setup.md` for detailed setup guide.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Backend selection (postgres or surrealdb)
BACKEND=postgres

# PostgreSQL settings (when BACKEND=postgres)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/memory

# SurrealDB settings (when BACKEND=surrealdb)
SURREAL_URL=file://./data/kiroku
SURREAL_NAMESPACE=kiroku
SURREAL_DATABASE=memory

# Optional - only needed for semantic search (embeddings)
OPENAI_API_KEY=sk-xxx
```

## API Endpoints

### Core
| Method | Path | Description |
|--------|------|-------------|
| POST | /ingest | Ingest raw messages |
| POST | /v2/items | Store structured memory (no OpenAI needed) |
| GET | /retrieve | Tiered retrieval |
| GET | /context | Agent prompt context |

### Intelligence (requires OpenAI)
| Method | Path | Description |
|--------|------|-------------|
| POST | /extract | Extract facts (requires OpenAI) |
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
- **SessionStart hook**: Auto-loads memory context
- **PostToolUse hook**: Incremental capture during long conversations (throttled)
- **Stop hook**: Two-phase capture (Fast regex + Slow LLM)
- **Priority ordering**: preferences > facts > goals (hybrid static+dynamic weights)
- **Smart truncation**: Never truncates mid-category, maintains completeness
- Manual commands for memory management

See `docs/claude-code-integration.md` for details.

## Documentation

- `docs/architecture.md` - Architecture design
- `docs/development-journey.md` - Development journey
- `docs/user-guide.md` - User guide
- `docs/integration-guide.md` - Integration guide
- `docs/claude-code-integration.md` - Claude Code integration guide
- `docs/surrealdb-setup.md` - SurrealDB backend setup guide
- `docs/surrealdb-migration-plan.md` - Dual-backend migration plan
- `docs/renaming-changelog.md` - Renaming changelog

## Project Structure

```
kiroku-memory/
├── kiroku_memory/           # Core module
│   ├── api.py               # FastAPI endpoints
│   ├── ingest.py            # Resource ingestion
│   ├── extract.py           # Fact extraction
│   ├── classify.py          # Classifier
│   ├── conflict.py          # Conflict resolution
│   ├── summarize.py         # Summary generation
│   ├── observability.py     # Monitoring
│   ├── db/                  # Database layer
│   │   ├── entities.py      # Domain entities (backend-agnostic)
│   │   ├── repositories/    # Repository pattern
│   │   │   ├── base.py      # Abstract interfaces
│   │   │   ├── factory.py   # Backend selection
│   │   │   ├── postgres/    # PostgreSQL implementation
│   │   │   └── surrealdb/   # SurrealDB implementation
│   │   └── surrealdb/       # SurrealDB module
│   │       ├── connection.py
│   │       └── schema.surql
│   ├── embedding/           # Embedding providers
│   │   ├── base.py          # Provider interface
│   │   ├── factory.py       # Provider factory
│   │   ├── openai_provider.py
│   │   └── local_provider.py
│   └── jobs/                # Maintenance jobs
├── scripts/
│   └── migrate_backend.py   # Backend migration CLI
├── tests/                   # Tests
├── docs/                    # Documentation
├── docker-compose.yml       # PostgreSQL config
└── pyproject.toml           # Project config
```

## Development

### Desktop App 版本檔案

發布前須同步更新以下檔案的版本號：

| 檔案 | 欄位 |
|------|------|
| `desktop/package.json` | `"version"` |
| `desktop/src-tauri/Cargo.toml` | `version` |
| `desktop/src-tauri/tauri.conf.json` | `"version"` |

**注意**：Release 產出檔名由 git tag 決定，但建議保持 tag 與上述檔案版本一致。

### Tech Stack

- Language: Python 3.11+
- Framework: FastAPI + SQLAlchemy 2.x
- Database: PostgreSQL 16 + pgvector OR SurrealDB (embedded)
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

## Troubleshooting

### `.venv` scripts report "No such file or directory" but file exists

Cause: `VIRTUAL_ENV` env var pointed to another project when `.venv` was created, causing incorrect shebang paths.

```bash
# Check shebang
head -1 .venv/bin/uvicorn
# If it shows another project's path, rebuild venv

# Fix
unset VIRTUAL_ENV
rm -rf .venv
uv sync
```

### `/extract` returns empty items but LLM responded correctly

Cause: OpenAI sometimes returns `"object": null` in extracted facts, causing Pydantic validation failure.

Fixed in `kiroku_memory/extract.py`: `ExtractedFact.object` is now `Optional[str]`.

## Translations

- [繁體中文](CLAUDE.zh-TW.md)
- [日本語](CLAUDE.ja.md)
