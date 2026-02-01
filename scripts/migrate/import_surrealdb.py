#!/usr/bin/env python3
"""Import JSONL data into SurrealDB"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiroku_memory.db.surrealdb import get_surreal_connection, init_surreal_db


def parse_datetime(value: str | None) -> str | None:
    """Parse datetime string to ISO format"""
    if value is None:
        return None
    # Already ISO format
    return value


async def import_resources(client, input_file: Path, batch_size: int = 100) -> int:
    """Import resources from JSONL"""
    count = 0
    batch = []

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            record_id = f"resource:{data['id']}"
            content = {
                "created_at": data["created_at"],
                "source": data["source"],
                "content": data["content"],
                "metadata": data.get("metadata", {}),
            }
            batch.append((record_id, content))
            count += 1

            if len(batch) >= batch_size:
                for rid, cont in batch:
                    await client.query(
                        "CREATE $id CONTENT $content",
                        {"id": rid, "content": cont},
                    )
                batch = []
                print(f"  Imported {count} resources...")

    # Final batch
    for rid, cont in batch:
        await client.query(
            "CREATE $id CONTENT $content",
            {"id": rid, "content": cont},
        )

    return count


async def import_items(client, input_file: Path, batch_size: int = 100) -> int:
    """Import items from JSONL"""
    count = 0
    batch = []

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            record_id = f"item:{data['id']}"
            content = {
                "created_at": data["created_at"],
                "subject": data.get("subject"),
                "predicate": data.get("predicate"),
                "object": data.get("object"),
                "category": data.get("category"),
                "confidence": data.get("confidence", 1.0),
                "status": data.get("status", "active"),
            }

            # Handle resource reference
            if data.get("resource_id"):
                content["resource"] = f"resource:{data['resource_id']}"

            # Handle supersedes reference
            if data.get("supersedes"):
                content["supersedes"] = f"item:{data['supersedes']}"

            batch.append((record_id, content))
            count += 1

            if len(batch) >= batch_size:
                for rid, cont in batch:
                    await client.query(
                        "CREATE $id CONTENT $content",
                        {"id": rid, "content": cont},
                    )
                batch = []
                print(f"  Imported {count} items...")

    # Final batch
    for rid, cont in batch:
        await client.query(
            "CREATE $id CONTENT $content",
            {"id": rid, "content": cont},
        )

    return count


async def import_categories(client, input_file: Path) -> int:
    """Import categories from JSONL"""
    count = 0

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            record_id = f"category:{data['id']}"
            content = {
                "name": data["name"],
                "summary": data.get("summary"),
                "updated_at": data.get("updated_at"),
            }
            await client.query(
                "CREATE $id CONTENT $content",
                {"id": record_id, "content": content},
            )
            count += 1

    return count


async def import_category_accesses(client, input_file: Path, batch_size: int = 100) -> int:
    """Import category accesses from JSONL"""
    count = 0
    batch = []

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            record_id = f"category_access:{data['id']}"
            content = {
                "category": data["category"],
                "accessed_at": data["accessed_at"],
                "source": data.get("source", "context"),
            }
            batch.append((record_id, content))
            count += 1

            if len(batch) >= batch_size:
                for rid, cont in batch:
                    await client.query(
                        "CREATE $id CONTENT $content",
                        {"id": rid, "content": cont},
                    )
                batch = []
                print(f"  Imported {count} category_accesses...")

    # Final batch
    for rid, cont in batch:
        await client.query(
            "CREATE $id CONTENT $content",
            {"id": rid, "content": cont},
        )

    return count


async def import_graph_edges(client, input_file: Path, batch_size: int = 100) -> int:
    """Import graph edges from JSONL"""
    count = 0
    batch = []

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            record_id = f"graph_edge:{data['id']}"
            content = {
                "subject": data["subject"],
                "predicate": data["predicate"],
                "object": data["object"],
                "weight": data.get("weight", 1.0),
                "created_at": data.get("created_at"),
            }
            batch.append((record_id, content))
            count += 1

            if len(batch) >= batch_size:
                for rid, cont in batch:
                    await client.query(
                        "CREATE $id CONTENT $content",
                        {"id": rid, "content": cont},
                    )
                batch = []
                print(f"  Imported {count} graph_edges...")

    # Final batch
    for rid, cont in batch:
        await client.query(
            "CREATE $id CONTENT $content",
            {"id": rid, "content": cont},
        )

    return count


async def import_embeddings(client, input_file: Path, batch_size: int = 50) -> int:
    """Import embeddings from JSONL (updates item records)"""
    count = 0
    batch = []

    with open(input_file) as f:
        for line in f:
            data = json.loads(line)
            if data.get("embedding"):
                item_id = f"item:{data['item_id']}"
                embedding = data["embedding"]
                batch.append((item_id, embedding))
                count += 1

                if len(batch) >= batch_size:
                    for iid, emb in batch:
                        await client.query(
                            "UPDATE $id SET embedding = $embedding, embedding_dim = $dim",
                            {"id": iid, "embedding": emb, "dim": len(emb)},
                        )
                    batch = []
                    print(f"  Imported {count} embeddings...")

    # Final batch
    for iid, emb in batch:
        await client.query(
            "UPDATE $id SET embedding = $embedding, embedding_dim = $dim",
            {"id": iid, "embedding": emb, "dim": len(emb)},
        )

    return count


async def import_all(input_dir: Path) -> dict[str, int]:
    """Import all JSONL files into SurrealDB"""
    # Initialize SurrealDB with schema
    await init_surreal_db()

    stats = {}

    async with get_surreal_connection() as client:
        # Import in order (respecting foreign keys)
        importers = [
            ("resources", "resources.jsonl", import_resources),
            ("items", "items.jsonl", import_items),
            ("categories", "categories.jsonl", import_categories),
            ("category_accesses", "category_accesses.jsonl", import_category_accesses),
            ("graph_edges", "graph_edges.jsonl", import_graph_edges),
            ("embeddings", "embeddings.jsonl", import_embeddings),
        ]

        for name, filename, importer in importers:
            input_file = input_dir / filename
            if input_file.exists():
                print(f"Importing {name}...")
                count = await importer(client, input_file)
                stats[name] = count
                print(f"  Done: {count} records")
            else:
                print(f"Skipping {name} (file not found: {input_file})")
                stats[name] = 0

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import JSONL data into SurrealDB")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("./data/export"),
        help="Input directory with JSONL files",
    )
    args = parser.parse_args()

    print(f"Importing from {args.input_dir}...")
    stats = asyncio.run(import_all(args.input_dir))

    print("\n=== Import Summary ===")
    for table, count in stats.items():
        print(f"  {table}: {count} records")


if __name__ == "__main__":
    main()
