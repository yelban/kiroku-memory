#!/usr/bin/env python3
"""Export data from PostgreSQL to JSONL files for migration"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiroku_memory.db.database import async_session_factory, init_db
from kiroku_memory.db.models import Resource, Item, Category, CategoryAccess, GraphEdge, Embedding


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for UUID and datetime"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def export_table(session, model, output_file: Path, batch_size: int = 1000) -> int:
    """Export a table to JSONL file"""
    count = 0
    offset = 0

    with open(output_file, "w") as f:
        while True:
            result = await session.execute(
                select(model).offset(offset).limit(batch_size)
            )
            rows = result.scalars().all()

            if not rows:
                break

            for row in rows:
                # Convert to dict
                data = {}
                for column in row.__table__.columns:
                    value = getattr(row, column.name)
                    # Handle special column name (metadata_)
                    key = column.name
                    if key == "metadata_":
                        key = "metadata"
                    data[key] = value

                f.write(json.dumps(data, cls=JSONEncoder) + "\n")
                count += 1

            offset += batch_size
            print(f"  Exported {count} {model.__tablename__} records...")

    return count


async def export_embeddings(session, output_file: Path, batch_size: int = 1000) -> int:
    """Export embeddings table to JSONL file"""
    count = 0
    offset = 0

    with open(output_file, "w") as f:
        while True:
            result = await session.execute(
                select(Embedding).offset(offset).limit(batch_size)
            )
            rows = result.scalars().all()

            if not rows:
                break

            for row in rows:
                data = {
                    "id": row.id,
                    "item_id": row.item_id,
                    "embedding": list(row.embedding) if row.embedding else None,
                }
                f.write(json.dumps(data, cls=JSONEncoder) + "\n")
                count += 1

            offset += batch_size
            print(f"  Exported {count} embeddings records...")

    return count


async def export_all(output_dir: Path) -> dict[str, int]:
    """Export all tables to JSONL files"""
    output_dir.mkdir(parents=True, exist_ok=True)

    await init_db()

    stats = {}

    async with async_session_factory() as session:
        # Export each table
        tables = [
            (Resource, "resources.jsonl"),
            (Item, "items.jsonl"),
            (Category, "categories.jsonl"),
            (CategoryAccess, "category_accesses.jsonl"),
            (GraphEdge, "graph_edges.jsonl"),
        ]

        for model, filename in tables:
            print(f"Exporting {model.__tablename__}...")
            output_file = output_dir / filename
            count = await export_table(session, model, output_file)
            stats[model.__tablename__] = count
            print(f"  Done: {count} records")

        # Export embeddings separately (has vector column)
        print("Exporting embeddings...")
        output_file = output_dir / "embeddings.jsonl"
        count = await export_embeddings(session, output_file)
        stats["embeddings"] = count
        print(f"  Done: {count} records")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export PostgreSQL data to JSONL")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/export"),
        help="Output directory for JSONL files",
    )
    args = parser.parse_args()

    print(f"Exporting to {args.output_dir}...")
    stats = asyncio.run(export_all(args.output_dir))

    print("\n=== Export Summary ===")
    for table, count in stats.items():
        print(f"  {table}: {count} records")
    print(f"\nFiles saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
