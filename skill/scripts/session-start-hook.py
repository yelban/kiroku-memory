#!/usr/bin/env python3
"""
SessionStart Hook: Load Kiroku Memory context at conversation start.

This hook fetches memory context from Kiroku Memory API and outputs it
to stdout, which Claude Code will inject into the conversation context.
"""

import json
import os
import sys
import urllib.request
import urllib.error

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")
MAX_CONTEXT_CHARS = int(os.environ.get("KIROKU_MAX_CONTEXT_CHARS", "12000"))  # ~4000 tokens


def get_project_name():
    """Detect project name from cwd in hook input."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
        cwd = input_data.get("cwd", "")

        if cwd:
            return os.path.basename(cwd)
    except Exception:
        pass

    return None


def fetch_context(categories: str = None, max_chars: int = None) -> str:
    """Fetch tiered context from Kiroku Memory API."""
    url = f"{KIROKU_API}/context"
    params = []
    if categories:
        params.append(f"categories={categories}")
    if max_chars:
        params.append(f"max_chars={max_chars}")
    if params:
        url += "?" + "&".join(params)

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("context", "")


def count_categories(context: str) -> int:
    """Count category headings (### Category) in context."""
    return context.count("### ")


def main():
    try:
        # Fetch global + project context (API handles smart truncation)
        context = fetch_context(max_chars=MAX_CONTEXT_CHARS)

        if not context or context.strip() == "":
            # No memories, exit silently
            sys.exit(0)

        # Count categories
        category_count = count_categories(context)

        # Output JSON with systemMessage (shown to user) and context
        output = {
            "systemMessage": f"✓ Kiroku Memory: {category_count} categories loaded",
            "result": f"<kiroku-memory>\n{context}\n</kiroku-memory>"
        }
        print(json.dumps(output))

        sys.exit(0)

    except urllib.error.URLError:
        # API not available, silently continue
        sys.exit(0)
    except Exception as e:
        # Log error but don't block
        print(f"<!-- Kiroku Memory: {e} -->", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
