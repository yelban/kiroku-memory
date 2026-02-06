#!/usr/bin/env python3
"""
Backend Migration CLI

Migrate data between PostgreSQL and SurrealDB backends.

Usage:
    # Full migration from PostgreSQL to SurrealDB
    python scripts/migrate_backend.py migrate --from postgres --to surrealdb

    # Export only
    python scripts/migrate_backend.py export --backend postgres

    # Import only
    python scripts/migrate_backend.py import --backend surrealdb

    # Verify data counts match
    python scripts/migrate_backend.py verify
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def cmd_export(args):
    """Export data from a backend"""
    from scripts.migrate.export_postgres import export_all

    if args.backend != "postgres":
        print(f"Export from {args.backend} not yet implemented")
        return 1

    print(f"Exporting from {args.backend} to {args.output_dir}...")
    stats = await export_all(Path(args.output_dir))

    print("\n=== Export Complete ===")
    total = sum(stats.values())
    print(f"Total records exported: {total}")
    return 0


async def cmd_import(args):
    """Import data into a backend"""
    from scripts.migrate.import_surrealdb import import_all

    if args.backend != "surrealdb":
        print(f"Import to {args.backend} not yet implemented")
        return 1

    print(f"Importing from {args.input_dir} to {args.backend}...")
    stats = await import_all(Path(args.input_dir))

    print("\n=== Import Complete ===")
    total = sum(stats.values())
    print(f"Total records imported: {total}")
    return 0


async def cmd_migrate(args):
    """Full migration from one backend to another"""
    from scripts.migrate.export_postgres import export_all
    from scripts.migrate.import_surrealdb import import_all

    if args.from_backend != "postgres" or args.to_backend != "surrealdb":
        print(f"Migration from {args.from_backend} to {args.to_backend} not yet implemented")
        return 1

    data_dir = Path(args.data_dir)

    # Step 1: Export
    print(f"\n{'='*50}")
    print("Step 1: Exporting from PostgreSQL...")
    print('='*50)
    export_stats = await export_all(data_dir)

    # Step 2: Import
    print(f"\n{'='*50}")
    print("Step 2: Importing to SurrealDB...")
    print('='*50)
    import_stats = await import_all(data_dir)

    # Step 3: Verify
    print(f"\n{'='*50}")
    print("Step 3: Verification")
    print('='*50)

    all_match = True
    for table in export_stats:
        exported = export_stats.get(table, 0)
        imported = import_stats.get(table, 0)
        status = "✓" if exported == imported else "✗"
        if exported != imported:
            all_match = False
        print(f"  {status} {table}: {exported} exported, {imported} imported")

    if all_match:
        print("\n✓ Migration completed successfully!")
    else:
        print("\n⚠ Migration completed with discrepancies")
        return 1

    return 0


async def cmd_verify(args):
    """Verify data counts between backends"""
    from kiroku_memory.db.config import settings
    from kiroku_memory.db.repositories.factory import get_unit_of_work

    # Get counts from current backend
    original_backend = settings.backend

    counts = {}

    # PostgreSQL counts
    settings.backend = "postgres"
    try:
        from kiroku_memory.db.database import init_db
        await init_db()
        async with get_unit_of_work() as uow:
            counts["postgres"] = {
                "items": await uow.items.count(),
                "categories": len(await uow.items.list_distinct_categories(status="active")),
            }
    except Exception as e:
        print(f"Error getting PostgreSQL counts: {e}")
        counts["postgres"] = None

    # SurrealDB counts
    settings.backend = "surrealdb"
    try:
        from kiroku_memory.db.surrealdb import init_surreal_db
        await init_surreal_db()
        async with get_unit_of_work() as uow:
            counts["surrealdb"] = {
                "items": await uow.items.count(),
                "categories": len(await uow.items.list_distinct_categories(status="active")),
            }
    except Exception as e:
        print(f"Error getting SurrealDB counts: {e}")
        counts["surrealdb"] = None

    # Restore original backend
    settings.backend = original_backend

    print("\n=== Backend Data Counts ===")
    for backend, data in counts.items():
        if data:
            print(f"\n{backend}:")
            for table, count in data.items():
                print(f"  {table}: {count}")
        else:
            print(f"\n{backend}: Unable to connect")

    # Compare
    if counts.get("postgres") and counts.get("surrealdb"):
        print("\n=== Comparison ===")
        all_match = True
        for table in counts["postgres"]:
            pg = counts["postgres"].get(table, 0)
            sr = counts["surrealdb"].get(table, 0)
            status = "✓" if pg == sr else "✗"
            if pg != sr:
                all_match = False
            print(f"  {status} {table}: PostgreSQL={pg}, SurrealDB={sr}")

        if all_match:
            print("\n✓ All counts match!")
        else:
            print("\n⚠ Counts do not match")
            return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Backend Migration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data from a backend")
    export_parser.add_argument(
        "--backend",
        choices=["postgres", "surrealdb"],
        default="postgres",
        help="Backend to export from",
    )
    export_parser.add_argument(
        "--output-dir",
        default="./data/export",
        help="Output directory for exported data",
    )

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data into a backend")
    import_parser.add_argument(
        "--backend",
        choices=["postgres", "surrealdb"],
        default="surrealdb",
        help="Backend to import into",
    )
    import_parser.add_argument(
        "--input-dir",
        default="./data/export",
        help="Input directory with exported data",
    )

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Full migration between backends")
    migrate_parser.add_argument(
        "--from",
        dest="from_backend",
        choices=["postgres", "surrealdb"],
        default="postgres",
        help="Source backend",
    )
    migrate_parser.add_argument(
        "--to",
        dest="to_backend",
        choices=["postgres", "surrealdb"],
        default="surrealdb",
        help="Target backend",
    )
    migrate_parser.add_argument(
        "--data-dir",
        default="./data/export",
        help="Temporary directory for exported data",
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify data counts between backends")

    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "export":
        return asyncio.run(cmd_export(args))
    elif args.command == "import":
        return asyncio.run(cmd_import(args))
    elif args.command == "migrate":
        return asyncio.run(cmd_migrate(args))
    elif args.command == "verify":
        return asyncio.run(cmd_verify(args))


if __name__ == "__main__":
    sys.exit(main() or 0)
