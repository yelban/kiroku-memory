#!/usr/bin/env python3
"""Store a memory in Kiroku Memory system.

Updated 2026-02-02:
- Use POST /v2/items to store structured memories directly
- No longer requires OpenAI API key for fact extraction
- Parse content into subject-predicate-object format
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

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


def parse_content(content: str, category_hint: str = None) -> dict:
    """Parse content into subject-predicate-object format.

    Supports patterns like:
    - "User likes dark mode" -> subject="User", predicate="likes", object="dark mode"
    - "吹吹喜歡冰美式" -> subject="吹吹", predicate="喜歡", object="冰美式"
    - "The API uses REST" -> subject="The API", predicate="uses", object="REST"

    Falls back to using the whole content as object if parsing fails.
    """
    content = content.strip()

    # Common verb patterns (English)
    en_patterns = [
        r'^(.+?)\s+(is|are|was|were|has|have|had|likes?|prefers?|wants?|needs?|uses?|works?|lives?|chose|decided?|discovered?)\s+(.+)$',
        r'^(.+?)\s+(should|will|can|must|would)\s+(.+)$',
    ]

    # Common verb patterns (Chinese)
    zh_patterns = [
        r'^(.+?)(是|喜歡|偏好|想要|需要|使用|住在|工作於|選擇|決定|發現|正在)(.+)$',
    ]

    # Try English patterns
    for pattern in en_patterns:
        match = re.match(pattern, content, re.IGNORECASE)
        if match:
            return {
                "subject": match.group(1).strip(),
                "predicate": match.group(2).strip(),
                "object": match.group(3).strip(),
            }

    # Try Chinese patterns
    for pattern in zh_patterns:
        match = re.match(pattern, content)
        if match:
            return {
                "subject": match.group(1).strip(),
                "predicate": match.group(2).strip(),
                "object": match.group(3).strip(),
            }

    # Fallback: treat entire content as a fact
    # Try to extract subject from common patterns
    subject = "User"
    if content.lower().startswith(("the ", "a ", "an ")):
        # Technical fact about something
        words = content.split()
        if len(words) >= 2:
            subject = " ".join(words[:2])
            content = " ".join(words[2:]) if len(words) > 2 else content

    return {
        "subject": subject,
        "predicate": "noted",
        "object": content,
    }


def store_item(subject: str, predicate: str, obj: str, category: str = None) -> dict:
    """Store structured memory item via POST /v2/items."""
    payload = {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "category": category or "facts",
        "confidence": 1.0,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{KIROKU_API}/v2/items",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Store a memory")
    parser.add_argument("content", nargs="+", help="Memory content to store")
    parser.add_argument("--category", "-c", help="Category (preferences, facts, goals, etc.)")
    parser.add_argument("--subject", "-s", help="Subject (who/what the memory is about)")
    parser.add_argument("--predicate", help="Predicate (action/relation)")
    parser.add_argument("--object", "-o", dest="obj", help="Object (value/target)")
    parser.add_argument("--project", "-p", help="Project name (for logging)")
    parser.add_argument("--global", "-g", dest="is_global", action="store_true",
                        help="Mark as global memory (for logging)")

    args = parser.parse_args()
    content = " ".join(args.content)

    # Determine scope for logging
    if args.is_global:
        scope = "global"
    else:
        project = args.project or get_project_name()
        scope = f"project:{project}" if project else "global"

    # If structured args provided, use them directly
    if args.subject and args.predicate and args.obj:
        parsed = {
            "subject": args.subject,
            "predicate": args.predicate,
            "object": args.obj,
        }
    else:
        # Auto-parse content
        parsed = parse_content(content, args.category)

    # Determine category
    category = args.category
    if not category:
        # Auto-detect from content
        content_lower = content.lower()
        if any(w in content_lower for w in ["喜歡", "偏好", "prefer", "like", "favorite"]):
            category = "preferences"
        elif any(w in content_lower for w in ["想要", "目標", "goal", "want", "plan"]):
            category = "goals"
        else:
            category = "facts"

    try:
        result = store_item(
            subject=parsed["subject"],
            predicate=parsed["predicate"],
            obj=parsed["object"],
            category=category,
        )

        print(f"✓ 已儲存記憶 [{scope}]")
        print(f"  {parsed['subject']} {parsed['predicate']} {parsed['object']}")
        print(f"  分類: {category}")
        print(f"  ID: {result.get('id', 'unknown')}")

    except urllib.error.URLError as e:
        print(f"✗ 無法連接 Kiroku Memory API ({KIROKU_API})", file=sys.stderr)
        print(f"  請確認服務已啟動", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
