# SurrealDB Backend Setup Guide

Kiroku Memory supports SurrealDB as an alternative to PostgreSQL. SurrealDB with SurrealKV provides an embedded, file-based database that requires no external services.

## Why SurrealDB?

| Feature | PostgreSQL + pgvector | SurrealDB |
|---------|----------------------|-----------|
| Deployment | Requires Docker/service | Embedded (zero config) |
| Storage | External database | Local files (SurrealKV) |
| Vector search | pgvector extension | Native HNSW index |
| Graph queries | Requires joins | Native RELATE edges |
| Best for | Production servers | Desktop apps, local dev |

## Installation

### 1. Install SurrealDB dependency

```bash
# Add surrealdb optional dependency
uv sync --extra surrealdb
```

### 2. Configure environment

Edit `.env`:

```bash
# Switch to SurrealDB backend
BACKEND=surrealdb

# SurrealDB settings (optional, defaults shown)
SURREAL_URL=file://./data/kiroku
SURREAL_NAMESPACE=kiroku
SURREAL_DATABASE=memory
```

### 3. Start the API

```bash
uv run uvicorn kiroku_memory.api:app --reload
```

The schema is automatically initialized on first startup.

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND` | `postgres` | Database backend (`postgres` or `surrealdb`) |
| `SURREAL_URL` | `file://./data/kiroku` | SurrealDB connection URL |
| `SURREAL_NAMESPACE` | `kiroku` | SurrealDB namespace |
| `SURREAL_DATABASE` | `memory` | SurrealDB database name |

### Connection URL formats

```bash
# Embedded (SurrealKV) - recommended for desktop
SURREAL_URL=file://./data/kiroku

# Absolute path
SURREAL_URL=file:///Users/me/kiroku-data

# Remote SurrealDB server (if needed)
SURREAL_URL=ws://localhost:8000
```

## Data Migration

### From PostgreSQL to SurrealDB

```bash
# Full migration
python scripts/migrate_backend.py migrate --from postgres --to surrealdb

# Or step by step:
# 1. Export from PostgreSQL
python scripts/migrate_backend.py export --backend postgres

# 2. Import to SurrealDB
python scripts/migrate_backend.py import --backend surrealdb

# 3. Verify
python scripts/migrate_backend.py verify
```

### Data location

SurrealDB data is stored at the path specified in `SURREAL_URL`:

```
./data/kiroku/        # Default location
├── ...               # SurrealKV data files
```

## API Compatibility

All `/v2/*` endpoints work identically with both backends:

- `POST /v2/ingest` - Ingest resources
- `GET /v2/resources` - List resources
- `GET /v2/items` - List items
- `GET /v2/categories` - List categories
- `GET /v2/stats` - Get statistics (shows current backend)

## Testing

Run tests against SurrealDB:

```bash
# Unit tests
uv run pytest tests/repositories/test_surrealdb_repos.py -v

# Integration tests (both backends)
uv run pytest tests/integration/ -v
```

## Troubleshooting

### "surrealdb module not found"

Install the optional dependency:
```bash
uv sync --extra surrealdb
```

### "Schema not initialized"

The schema is auto-initialized on startup. If issues persist:
```bash
# Force reinitialize
python -c "
import asyncio
from kiroku_memory.db.surrealdb import init_surreal_db
asyncio.run(init_surreal_db(force=True))
"
```

### Performance tuning

For large datasets, consider:
- Increasing batch sizes in migration scripts
- Using SSD storage for SurrealKV data directory
- Adjusting HNSW index parameters in `schema.surql`

## Schema Reference

See `kiroku_memory/db/surrealdb/schema.surql` for the full schema definition including:

- Resource, Item, Category tables
- HNSW vector index (1536 dimensions, cosine distance)
- Graph edge tables with native RELATE support
- Helper functions for vector search and graph traversal
