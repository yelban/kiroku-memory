# AI Agent Memory System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Language**: [English](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

A production-ready memory system for AI agents that implements persistent, evolving memory with tiered retrieval. Built on the principles from Rohit's "How to Build an Agent That Never Forgets" and community feedback.

## Why This Project?

Traditional RAG (Retrieval-Augmented Generation) faces fundamental challenges at scale:

- **Semantic similarity ≠ Factual truth**: Embeddings capture similarity, not correctness
- **No temporal context**: Cannot handle "user liked A before, now prefers B"
- **Memory contradictions**: Information accumulated over time may conflict
- **Scalability issues**: Retrieval performance degrades with tens of thousands of memories

This system addresses these challenges with a **Hybrid Memory Stack** architecture.

## Features

- **Append-only Raw Logs**: Immutable provenance tracking
- **Atomic Facts Extraction**: LLM-powered structured fact extraction (subject-predicate-object)
- **Category-based Organization**: 6 default categories with evolving summaries
- **Tiered Retrieval**: Summaries first, drill down to facts when needed
- **Conflict Resolution**: Automatic detection and archival of contradicting facts
- **Time Decay**: Exponential decay of memory confidence over time
- **Vector Search**: pgvector-powered semantic similarity search
- **Knowledge Graph**: Relationship mapping between entities
- **Scheduled Maintenance**: Nightly, weekly, and monthly maintenance jobs
- **Production Ready**: Structured logging, metrics, and health checks

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent Memory System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  Ingest  │───▶│ Extract  │───▶│ Classify │───▶│ Conflict │   │
│  │ (Raw Log)│    │ (Facts)  │    │(Category)│    │ Resolver │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│       │                                               │          │
│       ▼                                               ▼          │
│  ┌──────────┐                                   ┌──────────┐    │
│  │Resources │                                   │  Items   │    │
│  │(immutable)│                                  │ (active) │    │
│  └──────────┘                                   └──────────┘    │
│                                                      │           │
│                    ┌─────────────────────────────────┤           │
│                    │                                 │           │
│                    ▼                                 ▼           │
│              ┌──────────┐                     ┌──────────┐       │
│              │Embeddings│                     │ Summary  │       │
│              │(pgvector)│                     │ Builder  │       │
│              └──────────┘                     └──────────┘       │
│                    │                                 │           │
│                    └─────────────┬───────────────────┘           │
│                                  ▼                               │
│                           ┌──────────┐                           │
│                           │ Retrieve │                           │
│                           │ (Tiered) │                           │
│                           └──────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL + pgvector)
- OpenAI API Key

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/ai-agent-memory.git
cd ai-agent-memory

# Install dependencies using uv
uv sync

# Copy environment file
cp .env.example .env

# Edit .env and set your OPENAI_API_KEY
```

### Start Services

```bash
# Start PostgreSQL with pgvector
docker compose up -d

# Start the API server
uv run uvicorn memory.api:app --reload

# The API will be available at http://localhost:8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}

# Detailed health status
curl http://localhost:8000/health/detailed
```

## Usage

### Basic Workflow

#### 1. Ingest a Message

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My name is John and I work at Google as a software engineer. I prefer using Neovim.",
    "source": "user:john",
    "metadata": {"channel": "chat"}
  }'
```

#### 2. Extract Facts

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "YOUR_RESOURCE_ID"}'
```

This extracts structured facts like:
- `John` `works at` `Google` (category: facts)
- `John` `is a` `software engineer` (category: facts)
- `John` `prefers` `Neovim` (category: preferences)

#### 3. Generate Summaries

```bash
curl -X POST http://localhost:8000/summarize
```

#### 4. Retrieve Memories

```bash
# Tiered retrieval (summaries + items)
curl "http://localhost:8000/retrieve?query=What%20does%20John%20do"

# Get context for agent prompt
curl "http://localhost:8000/context"
```

### API Endpoints

#### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Ingest raw message into memory |
| GET | `/resources` | List raw resources |
| GET | `/resources/{id}` | Get specific resource |
| GET | `/retrieve` | Tiered memory retrieval |
| GET | `/items` | List extracted items |
| GET | `/categories` | List categories with summaries |

#### Intelligence Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/extract` | Extract facts from resource |
| POST | `/process` | Batch process pending resources |
| POST | `/summarize` | Build category summaries |
| GET | `/context` | Get memory context for agent prompt |

#### Maintenance Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs/nightly` | Run nightly consolidation |
| POST | `/jobs/weekly` | Run weekly maintenance |
| POST | `/jobs/monthly` | Run monthly re-indexing |

#### Observability Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Detailed health status |
| GET | `/metrics` | Application metrics |
| POST | `/metrics/reset` | Reset metrics |

## Integration

### With Claude Code (MCP Server)

Create an MCP server to integrate with Claude Code:

```python
# memory_mcp.py
from mcp.server import Server
from memory.db.database import get_session
from memory.summarize import get_tiered_context

app = Server("memory-system")

@app.tool("memory_context")
async def memory_context():
    async with get_session() as session:
        return await get_tiered_context(session)
```

Configure in `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["run", "python", "memory_mcp.py"]
    }
  }
}
```

### With Chat Bots (Telegram/LINE)

```javascript
const MEMORY_API = "http://localhost:8000";

// Get memory context before responding
async function getMemoryContext(userId) {
  const response = await fetch(`${MEMORY_API}/context`);
  const data = await response.json();
  return data.context;
}

// Save important information after conversation
async function saveToMemory(userId, content) {
  await fetch(`${MEMORY_API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      source: `bot:${userId}`
    })
  });
}

// Use in your bot
const memoryContext = await getMemoryContext(userId);
const enhancedPrompt = `${memoryContext}\n\n${SYSTEM_PROMPT}`;
```

See [Integration Guide](docs/integration-guide.md) for detailed examples.

## Maintenance

### Scheduled Jobs

Set up cron jobs for automatic maintenance:

```bash
# Nightly: Merge duplicates, promote hot memories
0 2 * * * curl -X POST http://localhost:8000/jobs/nightly

# Weekly: Apply time decay, archive old items
0 3 * * 0 curl -X POST http://localhost:8000/jobs/weekly

# Monthly: Rebuild embeddings and knowledge graph
0 4 1 * * curl -X POST http://localhost:8000/jobs/monthly
```

### Time Decay

Memories decay exponentially with a configurable half-life (default: 30 days):

```python
def time_decay_score(created_at, half_life_days=30):
    age_days = (now - created_at).days
    return 0.5 ** (age_days / half_life_days)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `OPENAI_API_KEY` | (required) | OpenAI API key for embeddings |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Vector dimensions |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (for future use) |
| `DEBUG` | `false` | Enable debug mode |

## Project Structure

```
.
├── memory/
│   ├── api.py              # FastAPI endpoints
│   ├── ingest.py           # Resource ingestion
│   ├── extract.py          # Fact extraction (LLM)
│   ├── classify.py         # Category classification
│   ├── conflict.py         # Conflict resolution
│   ├── summarize.py        # Summary generation
│   ├── embedding.py        # Vector search
│   ├── observability.py    # Metrics & logging
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── schema.sql      # PostgreSQL schema
│   │   ├── database.py     # Connection management
│   │   └── config.py       # Settings
│   └── jobs/
│       ├── nightly.py      # Daily maintenance
│       ├── weekly.py       # Weekly maintenance
│       └── monthly.py      # Monthly maintenance
├── tests/
│   ├── test_models.py
│   └── load/
│       └── test_retrieval.py
├── docs/
│   ├── architecture.md
│   ├── development-journey.md
│   ├── user-guide.md
│   └── integration-guide.md
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Documentation

- [Architecture Design](docs/architecture.md) - System architecture and design decisions
- [Development Journey](docs/development-journey.md) - From idea to implementation
- [User Guide](docs/user-guide.md) - Comprehensive usage guide
- [Integration Guide](docs/integration-guide.md) - Integration with Claude Code, Codex, and chat bots

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI + asyncio
- **Database**: PostgreSQL 16 + pgvector
- **ORM**: SQLAlchemy 2.x
- **Embeddings**: OpenAI text-embedding-3-small
- **Package Manager**: uv

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Rohit (@rohit4verse) for the original "How to Build an Agent That Never Forgets" article
- MemoraX team for open-source implementation reference
- Rishi Sood for LC-OS Context Engineering papers
- The community for valuable feedback and suggestions

## Related Projects

- [MemoraX](https://github.com/MemoraXLabs/MemoraX) - Another implementation of agent memory
- [mem0](https://github.com/mem0ai/mem0) - Memory layer for AI applications
