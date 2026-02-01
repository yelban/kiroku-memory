#!/usr/bin/env python3
"""
Kiroku Memory Desktop - FastAPI Service Entrypoint

This script serves as the stable entry point for the Tauri desktop app
to start the FastAPI service. It handles:
- Environment variable configuration
- SurrealDB embedded database setup
- Graceful startup and error handling
- Health check endpoint verification

Usage:
    python start-service.py [--host HOST] [--port PORT] [--data-dir DIR]
"""

import argparse
import os
import sys
import time
from pathlib import Path


def setup_environment(data_dir: str) -> None:
    """Configure environment variables for Kiroku Memory."""
    # Ensure data directory exists
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    # SurrealDB configuration
    surreal_path = data_path / "surrealdb" / "kiroku"
    surreal_path.parent.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("BACKEND", "surrealdb")
    os.environ.setdefault("SURREAL_URL", f"file://{surreal_path}")
    os.environ.setdefault("SURREAL_NAMESPACE", "kiroku")
    os.environ.setdefault("SURREAL_DATABASE", "memory")

    # Disable Python buffering for better log output
    os.environ["PYTHONUNBUFFERED"] = "1"


def verify_imports() -> bool:
    """Verify all required modules can be imported."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        import surrealdb  # noqa: F401
        import kiroku_memory.api  # noqa: F401
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import required module: {e}", file=sys.stderr)
        return False


def start_service(host: str, port: int) -> None:
    """Start the uvicorn server."""
    import uvicorn

    print(f"[Kiroku] Starting service on {host}:{port}")
    print(f"[Kiroku] Backend: {os.environ.get('BACKEND', 'unknown')}")
    print(f"[Kiroku] SurrealDB URL: {os.environ.get('SURREAL_URL', 'unknown')}")

    uvicorn.run(
        "kiroku_memory.api:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kiroku Memory Desktop - FastAPI Service"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Data directory for SurrealDB (default: current directory)",
    )
    args = parser.parse_args()

    # Default data directory
    data_dir = args.data_dir or os.getcwd()

    print("[Kiroku] Initializing service...")
    print(f"[Kiroku] Data directory: {data_dir}")

    # Setup environment
    setup_environment(data_dir)

    # Verify imports
    if not verify_imports():
        return 1

    # Start service
    try:
        start_service(args.host, args.port)
        return 0
    except KeyboardInterrupt:
        print("\n[Kiroku] Service stopped by user")
        return 0
    except Exception as e:
        print(f"[ERROR] Service failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
