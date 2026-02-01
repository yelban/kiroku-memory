#!/usr/bin/env python3
"""
Stop Hook: Analyze conversation and save important memories.

This hook runs when Claude finishes a response. It analyzes the conversation
to detect save-worthy information (preferences, decisions, facts) and
ingests them to Kiroku Memory.

Smart filtering rules:
- Only save explicit preferences, decisions, or stable facts
- Ignore greetings, confirmations, trivial chat
- Require minimum content length
- Deduplicate recent saves
"""

import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")
CACHE_DIR = Path.home() / ".cache" / "kiroku-memory"
CACHE_FILE = CACHE_DIR / "recent_saves.json"
MIN_LENGTH_WITH_PATTERN = 10   # Weighted length threshold when SAVE_PATTERN matched
MIN_LENGTH_NO_PATTERN = 35     # Weighted length threshold for unmatched content
DEDUP_HOURS = 24

# CJK character detection (Chinese, Japanese Hiragana/Katakana)
CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]')


def weighted_length(content: str) -> float:
    """Calculate weighted length: CJK chars count as 2.5x, others as 1x."""
    cjk_count = len(CJK_PATTERN.findall(content))
    non_cjk = len(content) - cjk_count
    return cjk_count * 2.5 + non_cjk

# Patterns that indicate save-worthy content
SAVE_PATTERNS = [
    r"(?:I|我|用戶|user)\s*(?:喜歡|偏好|prefer|like)",
    r"(?:I|我|用戶|user)\s*(?:不喜歡|討厭|dislike|hate)",
    r"(?:決定|decide|chosen?|selected?)",
    r"(?:記住|remember|note that)",
    r"(?:設定|config|setting)",
    r"(?:工作於|work at|employed)",
    r"(?:住在|live in|located)",
    r"(?:專案|project)\s*(?:使用|use)",
    r"(?:架構|architecture|design)\s*(?:決定|decision)",
]

# Patterns that indicate noise (should NOT save)
NOISE_PATTERNS = [
    r"^(?:ok|好的?|是的?|對|沒問題|understood|got it|sure|yes|no)[\s.!]*$",
    r"^(?:謝謝|thanks?|thank you)[\s.!]*$",
    r"^(?:請|please|can you|could you)",
    r"^(?:什麼|怎麼|如何|what|how|why|when|where)\s*(?:是|意思)?",
    r"(?:error|錯誤|failed|失敗)",
]


def get_project_name(cwd: str) -> str:
    """Extract project name from cwd."""
    if cwd:
        return os.path.basename(cwd)
    return None


def load_recent_saves() -> dict:
    """Load recently saved content hashes."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"saves": [], "last_cleanup": datetime.now().isoformat()}


def save_recent_saves(data: dict):
    """Save recent content hashes."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def content_hash(content: str, source: str) -> str:
    """Generate hash for deduplication."""
    return hashlib.md5(f"{source}:{content}".encode()).hexdigest()


def is_duplicate(content: str, source: str, recent: dict) -> bool:
    """Check if content was recently saved."""
    h = content_hash(content, source)
    now = datetime.now()

    # Clean old entries
    cutoff = now.timestamp() - (DEDUP_HOURS * 3600)
    recent["saves"] = [
        s for s in recent["saves"]
        if s.get("ts", 0) > cutoff
    ]

    # Check for duplicate
    for s in recent["saves"]:
        if s.get("hash") == h:
            return True

    return False


def mark_saved(content: str, source: str, recent: dict):
    """Mark content as saved."""
    recent["saves"].append({
        "hash": content_hash(content, source),
        "ts": datetime.now().timestamp()
    })
    save_recent_saves(recent)


def should_save(content: str) -> bool:
    """Determine if content is worth saving.

    Pattern-first, weighted-length-second approach:
    1. Reject noise patterns immediately
    2. Calculate weighted length (CJK chars count as 2.5x)
    3. If SAVE_PATTERN matched → lower threshold
    4. No pattern matched → higher threshold
    """
    content_lower = content.lower().strip()
    w_len = weighted_length(content)

    # 1. Check noise patterns first - reject immediately
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return False

    # 2. Check save patterns - if matched, use lower threshold
    for pattern in SAVE_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return w_len >= MIN_LENGTH_WITH_PATTERN

    # 3. No pattern matched - use higher threshold
    return w_len >= MIN_LENGTH_NO_PATTERN


def extract_saveable_content(transcript_path: str) -> list:
    """Extract save-worthy content from transcript."""
    candidates = []

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    role = entry.get("role", "")
                    content = ""

                    # Extract text content
                    if role == "user":
                        msg = entry.get("message", {})
                        if isinstance(msg, dict):
                            content_list = msg.get("content", [])
                            for c in content_list:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    content = c.get("text", "")
                                    break
                        elif isinstance(msg, str):
                            content = msg

                    if content and should_save(content):
                        candidates.append(content)

                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    # Return unique candidates, last 3 only
    seen = set()
    unique = []
    for c in reversed(candidates):
        if c not in seen:
            seen.add(c)
            unique.append(c)
        if len(unique) >= 3:
            break

    return list(reversed(unique))


def ingest_memory(content: str, source: str) -> bool:
    """Send content to Kiroku Memory API."""
    try:
        payload = {
            "content": content,
            "source": source,
            "metadata": {"auto_saved": True, "hook": "stop"}
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{KIROKU_API}/ingest",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            resource_id = result.get("resource_id")

            # Try to extract facts (non-blocking)
            if resource_id:
                try:
                    extract_payload = json.dumps({"resource_id": resource_id}).encode()
                    extract_req = urllib.request.Request(
                        f"{KIROKU_API}/extract",
                        data=extract_payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(extract_req, timeout=10)
                except Exception:
                    pass

            return True

    except Exception:
        return False


def main():
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        cwd = input_data.get("cwd", "")
        transcript_path = input_data.get("transcript_path", "")

        if not transcript_path or not os.path.exists(transcript_path):
            sys.exit(0)

        # Determine source
        project = get_project_name(cwd)
        source = f"project:{project}" if project else "global:user"

        # Load recent saves for deduplication
        recent = load_recent_saves()

        # Extract saveable content
        candidates = extract_saveable_content(transcript_path)

        # Save each candidate
        saved_count = 0
        for content in candidates:
            if is_duplicate(content, source, recent):
                continue

            if ingest_memory(content, source):
                mark_saved(content, source, recent)
                saved_count += 1

        # Silent success
        sys.exit(0)

    except Exception as e:
        # Log error but don't block
        print(f"<!-- Kiroku Memory Stop Hook: {e} -->", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
