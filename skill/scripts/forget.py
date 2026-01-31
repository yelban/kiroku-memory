#!/usr/bin/env python3
"""Archive or delete memories from Kiroku Memory system."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")


def search_items(query: str, category: str = None, limit: int = 10) -> list:
    """Search for items to potentially forget."""
    import urllib.parse
    params = [f"query={urllib.parse.quote(query)}", f"limit={limit}"]
    if category:
        params.append(f"category={category}")

    url = f"{KIROKU_API}/retrieve?{'&'.join(params)}"
    req = urllib.request.Request(url, method="GET")

    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("items", [])


def format_item(item: dict, index: int) -> str:
    """Format item for selection display."""
    subj = item.get("subject", "")
    pred = item.get("predicate", "")
    obj = item.get("object", "")
    cat = item.get("category", "")
    item_id = item.get("id", "")[:8]

    fact = f"{subj} {pred} {obj}".strip()
    return f"  [{index}] ({item_id}) [{cat}] {fact}"


def main():
    parser = argparse.ArgumentParser(description="Archive or delete memories")
    parser.add_argument("query", nargs="+", help="Search query to find memories to forget")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Skip confirmation")
    parser.add_argument("--limit", "-l", type=int, default=5,
                        help="Max items to show (default: 5)")

    args = parser.parse_args()
    query = " ".join(args.query)

    try:
        # Search for matching items
        items = search_items(query, args.category, args.limit)

        if not items:
            print(f"找不到符合 '{query}' 的記憶")
            return

        print(f"找到 {len(items)} 筆符合的記憶：\n")
        for i, item in enumerate(items):
            print(format_item(item, i))

        print()

        # Note: Kiroku Memory API 目前沒有 delete/archive endpoint
        # 這裡提供指引讓用戶知道如何處理
        print("⚠️  目前 Kiroku Memory API 尚未實作刪除端點。")
        print("   如需刪除，請直接操作資料庫：")
        print()
        print("   # 連接資料庫")
        print("   docker exec -it memory-db psql -U postgres -d memory")
        print()
        print("   # 封存 item (設為 archived)")
        print(f"   UPDATE items SET status = 'archived' WHERE id = '<item_id>';")
        print()
        print("   # 或完全刪除")
        print(f"   DELETE FROM items WHERE id = '<item_id>';")

    except urllib.error.URLError as e:
        print(f"✗ 無法連接 Kiroku Memory API ({KIROKU_API})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
