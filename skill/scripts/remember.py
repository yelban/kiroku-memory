#!/usr/bin/env python3
"""Store a memory in Kiroku Memory system."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")


def get_project_name():
    """Detect project name from git or directory."""
    # Try git remote
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return os.path.basename(result.stdout.strip())
    except Exception:
        pass

    # Fallback to current directory name
    cwd = os.getcwd()
    if cwd != os.path.expanduser("~"):
        return os.path.basename(cwd)

    return None


def ingest(content: str, source: str, metadata: dict = None) -> dict:
    """Send content to Kiroku Memory API."""
    payload = {
        "content": content,
        "source": source,
        "metadata": metadata or {}
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{KIROKU_API}/ingest",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract(resource_id: str) -> dict:
    """Extract facts from ingested resource."""
    payload = {"resource_id": resource_id}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{KIROKU_API}/extract",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Store a memory")
    parser.add_argument("content", nargs="+", help="Memory content to store")
    parser.add_argument("--category", "-c", help="Category hint (preferences, facts, etc.)")
    parser.add_argument("--project", "-p", help="Project name (auto-detected if omitted)")
    parser.add_argument("--global", "-g", dest="is_global", action="store_true",
                        help="Store as global memory (not project-specific)")
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip fact extraction")

    args = parser.parse_args()
    content = " ".join(args.content)

    # Determine source
    if args.is_global:
        source = "global:user"
    else:
        project = args.project or get_project_name()
        source = f"project:{project}" if project else "global:user"

    # Add category hint to metadata if provided
    metadata = {}
    if args.category:
        metadata["category_hint"] = args.category

    try:
        # Ingest
        result = ingest(content, source, metadata)
        resource_id = result["resource_id"]
        print(f"✓ 已儲存記憶 [{source}]")
        print(f"  ID: {resource_id}")

        # Extract facts
        if not args.no_extract:
            try:
                extract_result = extract(resource_id)
                items_count = extract_result.get("items_created", 0)
                if items_count > 0:
                    print(f"  抽取了 {items_count} 個事實")
            except Exception as e:
                print(f"  (事實抽取跳過: {e})")

    except urllib.error.URLError as e:
        print(f"✗ 無法連接 Kiroku Memory API ({KIROKU_API})", file=sys.stderr)
        print(f"  請確認服務已啟動: docker compose up -d && uv run uvicorn kiroku_memory.api:app", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
