#!/usr/bin/env python3
"""Search memories in Kiroku Memory system."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")


def get_project_name():
    """Detect project name from git or directory."""
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

    cwd = os.getcwd()
    if cwd != os.path.expanduser("~"):
        return os.path.basename(cwd)
    return None


def retrieve(query: str, category: str = None, limit: int = 10) -> dict:
    """Search Kiroku Memory API."""
    params = [f"query={urllib.parse.quote(query)}", f"limit={limit}"]
    if category:
        params.append(f"category={category}")

    url = f"{KIROKU_API}/retrieve?{'&'.join(params)}"
    req = urllib.request.Request(url, method="GET")

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_context(categories: str = None) -> dict:
    """Get tiered context."""
    url = f"{KIROKU_API}/context"
    if categories:
        url += f"?categories={categories}"

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_item(item: dict, show_source: bool = False) -> str:
    """Format a single item for display."""
    subj = item.get("subject", "")
    pred = item.get("predicate", "")
    obj = item.get("object", "")
    cat = item.get("category", "")
    conf = item.get("confidence", 0)
    created = item.get("created_at", "")

    # Format date
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            date_str = dt.strftime("%m/%d")
        except Exception:
            date_str = ""
    else:
        date_str = ""

    # Build fact string
    fact = f"{subj} {pred} {obj}".strip()
    if not fact:
        fact = "(無內容)"

    # Confidence indicator
    if conf >= 0.8:
        conf_icon = "●"
    elif conf >= 0.5:
        conf_icon = "◐"
    else:
        conf_icon = "○"

    line = f"  {conf_icon} [{cat}] {fact}"
    if date_str:
        line += f" ({date_str})"

    return line


def main():
    parser = argparse.ArgumentParser(description="Search memories")
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--project", "-p", action="store_true",
                        help="Only search current project memories")
    parser.add_argument("--global", "-g", dest="is_global", action="store_true",
                        help="Only search global memories")
    parser.add_argument("--limit", "-l", type=int, default=10,
                        help="Max results (default: 10)")
    parser.add_argument("--context", action="store_true",
                        help="Show full tiered context instead of search")

    args = parser.parse_args()

    try:
        if args.context:
            # Show tiered context
            result = get_context(args.category)
            context = result.get("context", "")
            if context:
                print("=== Kiroku Memory Context ===\n")
                print(context)
            else:
                print("(記憶庫為空)")
            return

        # Search mode
        query = " ".join(args.query) if args.query else ""
        if not query:
            query = "*"  # Match all

        result = retrieve(query, args.category, args.limit)

        # Filter by source if requested
        items = result.get("items", [])
        categories = result.get("categories", [])
        total = result.get("total_items", 0)

        # Display categories/summaries
        if categories:
            print("=== 分類摘要 ===")
            for cat in categories:
                name = cat.get("name", "")
                summary = cat.get("summary", "")
                if summary:
                    print(f"\n【{name}】")
                    # Truncate long summaries
                    if len(summary) > 200:
                        summary = summary[:200] + "..."
                    print(f"  {summary}")
            print()

        # Display items
        if items:
            print(f"=== 記憶項目 ({len(items)}/{total}) ===")
            for item in items:
                print(format_item(item))
        else:
            print("(無符合的記憶)")

    except urllib.error.URLError as e:
        print(f"✗ 無法連接 Kiroku Memory API ({KIROKU_API})", file=sys.stderr)
        print(f"  請確認服務已啟動", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import urllib.parse
    main()
