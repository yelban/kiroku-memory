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
MAX_CONTEXT_CHARS = 2000  # Limit context size


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


def fetch_context(categories: str = None) -> str:
    """Fetch tiered context from Kiroku Memory API."""
    url = f"{KIROKU_API}/context"
    if categories:
        url += f"?categories={categories}"

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("context", "")


def main():
    try:
        # Fetch global + project context
        context = fetch_context()

        if not context or context.strip() == "":
            # No memories, exit silently
            sys.exit(0)

        # Truncate if too long
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

        # Output context - Claude Code will inject this into conversation
        print(f"""
<kiroku-memory>
{context}
</kiroku-memory>
""".strip())

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
