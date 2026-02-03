#!/usr/bin/env python3
"""
Stop Hook: Analyze conversation and save important memories.

This hook runs when Claude finishes a response. It analyzes the conversation
to detect save-worthy information (preferences, decisions, facts) and
ingests them to Kiroku Memory.

Smart filtering rules:
- Analyze BOTH user messages AND assistant conclusions
- Only save explicit preferences, decisions, discoveries, or stable facts
- Ignore greetings, confirmations, trivial chat
- Require minimum content length
- Deduplicate recent saves

Phase 1 improvements (2026-02-01):
- Expanded to analyze assistant messages with conclusion markers
- Relaxed NOISE_PATTERNS (removed "請/please" filter)
- Extended SAVE_PATTERNS for discoveries, decisions, learnings
"""

import hashlib
import json
import os
import re
import subprocess
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
MAX_ASSISTANT_MESSAGES = 4     # Only analyze last N assistant messages

# CJK character detection (Chinese, Japanese Hiragana/Katakana)
CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]')


def weighted_length(content: str) -> float:
    """Calculate weighted length: CJK chars count as 2.5x, others as 1x."""
    cjk_count = len(CJK_PATTERN.findall(content))
    non_cjk = len(content) - cjk_count
    return cjk_count * 2.5 + non_cjk


# Patterns that indicate save-worthy content (user messages)
SAVE_PATTERNS = [
    # Preferences (existing)
    r"(?:I|我|用戶|user)\s*(?:喜歡|偏好|prefer|like)",
    r"(?:I|我|用戶|user)\s*(?:不喜歡|討厭|dislike|hate)",
    # Decisions (existing + new)
    r"(?:決定|decide|chosen?|selected?)",
    r"(?:選擇|採用|choose|adopt)",
    r"(?:使用|use)\s*\S+\s*(?:而非|instead of|over)",
    # Memory markers (existing)
    r"(?:記住|remember|note that)",
    # Settings/Config (existing)
    r"(?:設定|config|setting)",
    # Facts (existing)
    r"(?:工作於|work at|employed)",
    r"(?:住在|live in|located)",
    # Project decisions (existing + new)
    r"(?:專案|project)\s*(?:使用|use)",
    r"(?:架構|architecture|design)\s*(?:決定|decision)",
    # Technical discoveries (new)
    r"(?:發現|发现|discovered?|found that)",
    r"(?:解決方案|solution)\s*(?:是|:)",
    r"(?:原因是|root cause|because)",
    r"(?:問題是|the issue|the problem)",
    # Learnings (new)
    r"(?:學到|learned|學習心得)",
    r"(?:心得|經驗|experience|takeaway)",
    r"(?:原來|it turns out|actually)",
]

# Patterns that indicate noise (should NOT save)
# Note: Removed "請/please" filter to allow polite requests with valuable content
NOISE_PATTERNS = [
    r"^(?:ok|好的?|是的?|對|沒問題|understood|got it|sure|yes|no)[\s.!]*$",
    r"^(?:謝謝|thanks?|thank you)[\s.!]*$",
    r"^(?:什麼|怎麼|如何|what|how|why|when|where)\s*(?:是|意思)?",
    r"(?:error|錯誤|failed|失敗)",
]

# Conclusion markers for assistant messages
# Only extract content near these markers from Claude's responses
CONCLUSION_MARKERS = [
    # Solution/Discovery
    r"(?:解決方案|solution)",
    r"(?:發現|discovered?|finding)",
    r"(?:結論|conclusion)",
    # Recommendations
    r"(?:建議|recommend|suggest)",
    r"(?:核心價值|core value|key insight)",
    # Root cause
    r"(?:根因|root cause|原因是)",
    r"(?:問題在於|the issue is|the problem is)",
    # Summary markers
    r"(?:總結|summary|in summary)",
    r"(?:重點|key point|takeaway)",
    # Learning/Experience
    r"(?:學到的經驗|lessons learned)",
    r"(?:這表示|this means|this indicates)",
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


def extract_text_from_entry(entry: dict) -> str:
    """Extract text content from a transcript entry."""
    msg = entry.get("message", {})
    if isinstance(msg, dict):
        content_list = msg.get("content", [])
        for c in content_list:
            if isinstance(c, dict) and c.get("type") == "text":
                return c.get("text", "").strip()
    elif isinstance(msg, str):
        return msg.strip()
    return ""


def extract_conclusion_snippets(text: str, max_length: int = 200) -> list:
    """Extract meaningful snippets near conclusion markers from assistant text.

    Returns list of extracted snippets that contain conclusion markers.
    Each snippet is trimmed to max_length characters around the marker.
    """
    snippets = []
    text_lower = text.lower()

    for marker_pattern in CONCLUSION_MARKERS:
        matches = list(re.finditer(marker_pattern, text_lower, re.IGNORECASE))
        for match in matches:
            start = match.start()
            # Find sentence boundaries around the marker
            # Look backwards for sentence start
            sentence_start = max(0, start - 100)
            for i in range(start - 1, sentence_start, -1):
                if text[i] in '.。!！?？\n':
                    sentence_start = i + 1
                    break

            # Look forward for sentence end
            sentence_end = min(len(text), start + max_length)
            for i in range(start + len(match.group()), sentence_end):
                if i < len(text) and text[i] in '.。!！?？\n':
                    sentence_end = i + 1
                    break

            snippet = text[sentence_start:sentence_end].strip()
            if snippet and len(snippet) > 15:  # Minimum meaningful length
                snippets.append(snippet)

    # Deduplicate and limit
    seen = set()
    unique_snippets = []
    for s in snippets:
        s_hash = s[:50]  # Use prefix for dedup
        if s_hash not in seen:
            seen.add(s_hash)
            unique_snippets.append(s)
        if len(unique_snippets) >= 3:
            break

    return unique_snippets


def extract_saveable_content(transcript_path: str) -> list:
    """Extract save-worthy content from transcript.

    Analyzes both user and assistant messages:
    - User messages: Apply SAVE_PATTERNS matching
    - Assistant messages: Extract conclusion marker snippets from last N messages
    """
    user_candidates = []
    assistant_entries = []

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")

                    if entry_type == "user":
                        content = extract_text_from_entry(entry)
                        if content and should_save(content):
                            user_candidates.append(("user", content))

                    elif entry_type == "assistant":
                        content = extract_text_from_entry(entry)
                        if content:
                            assistant_entries.append(content)

                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    # Process last N assistant messages for conclusion markers
    assistant_candidates = []
    for text in assistant_entries[-MAX_ASSISTANT_MESSAGES:]:
        snippets = extract_conclusion_snippets(text)
        for snippet in snippets:
            if weighted_length(snippet) >= MIN_LENGTH_WITH_PATTERN:
                assistant_candidates.append(("assistant", snippet))

    # Combine candidates: user first, then assistant
    all_candidates = user_candidates + assistant_candidates

    # Return unique candidates, last 5 only (increased from 3)
    seen = set()
    unique = []
    for role, content in reversed(all_candidates):
        content_key = content[:100]  # Use prefix for dedup
        if content_key not in seen:
            seen.add(content_key)
            unique.append((role, content))
        if len(unique) >= 5:
            break

    return list(reversed(unique))


def parse_content_to_spo(content: str) -> dict:
    """Parse content into subject-predicate-object format.

    Simple heuristic parsing - more sophisticated parsing can be done by LLM hook.
    """
    content = content.strip()

    # Common verb patterns (English)
    en_patterns = [
        r'^(.+?)\s+(is|are|was|were|has|have|had|likes?|prefers?|wants?|needs?|uses?|works?|lives?|chose|decided?|discovered?)\s+(.+)$',
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

    # Fallback: use content as object
    return {
        "subject": "User",
        "predicate": "noted",
        "object": content[:200],  # Limit length
    }


def detect_category(content: str) -> str:
    """Auto-detect category from content."""
    content_lower = content.lower()
    if any(w in content_lower for w in ["喜歡", "偏好", "prefer", "like", "favorite"]):
        return "preferences"
    elif any(w in content_lower for w in ["想要", "目標", "goal", "want", "plan"]):
        return "goals"
    elif any(w in content_lower for w in ["發現", "discover", "found", "learned"]):
        return "facts"
    elif any(w in content_lower for w in ["決定", "decide", "chose", "選擇"]):
        return "facts"
    return "facts"


def ingest_memory(content: str, source: str, role: str = "user") -> bool:
    """Store memory via POST /v2/items (no OpenAI required)."""
    try:
        parsed = parse_content_to_spo(content)
        category = detect_category(content)

        payload = {
            "subject": parsed["subject"],
            "predicate": parsed["predicate"],
            "object": parsed["object"],
            "category": category,
            "confidence": 0.8 if role == "assistant" else 1.0,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{KIROKU_API}/v2/items",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            return True

    except Exception:
        return False


def spawn_llm_worker(transcript_path: str, source: str):
    """Spawn async LLM worker for deep analysis (Phase 2).

    The worker runs in background and does not block the hook.
    """
    try:
        llm_script = Path(__file__).with_name("stop-hook-llm.py")

        if not llm_script.exists():
            return

        # Spawn detached subprocess
        subprocess.Popen(
            [
                sys.executable,
                str(llm_script),
                "--transcript", transcript_path,
                "--source", source
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )
    except Exception:
        # Silently fail - don't block the hook
        pass


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

        # === Phase 1: Fast path (regex-based) ===
        # Extract saveable content (now includes assistant conclusions)
        candidates = extract_saveable_content(transcript_path)

        # Save each candidate
        saved_count = 0
        for role, content in candidates:
            if is_duplicate(content, source, recent):
                continue

            if ingest_memory(content, source, role):
                mark_saved(content, source, recent)
                saved_count += 1

        # === Phase 2: Slow path (async LLM analysis) ===
        # Spawn background worker for deep analysis
        spawn_llm_worker(transcript_path, source)

        # Silent success
        sys.exit(0)

    except Exception as e:
        # Log error but don't block
        print(f"<!-- Kiroku Memory Stop Hook: {e} -->", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
