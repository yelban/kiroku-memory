#!/usr/bin/env python3
"""
Stop Hook LLM Worker: Deep analysis of conversation using Claude CLI.

This script runs asynchronously (spawned by stop-hook.py) to perform
deeper analysis of conversation content using Claude CLI.

Features:
- Extracts last N messages from both user and assistant
- Uses Claude CLI for intelligent memory evaluation
- Parses JSON output and ingests to Kiroku Memory
- Shares deduplication cache with stop-hook.py

Usage:
    python3 stop-hook-llm.py --transcript /path/to/transcript.jsonl --source project:name

Phase 2 implementation (2026-02-01)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")
CACHE_DIR = Path.home() / ".cache" / "kiroku-memory"
CACHE_FILE = CACHE_DIR / "recent_saves.json"
LOG_FILE = CACHE_DIR / "llm-worker.log"
DEDUP_HOURS = 24

# Analysis limits
MAX_USER_MESSAGES = 10
MAX_ASSISTANT_MESSAGES = 8
MAX_MEMORIES = 5
MAX_TRANSCRIPT_CHARS = 12000  # Limit transcript size for Claude CLI

# Claude CLI prompt template - outputs structured SPO format for direct storage
MEMORY_EXTRACTION_PROMPT = """You are an assistant that extracts durable memories from a conversation.
Return JSON only. No prose. No markdown code blocks.

Input:
<conversation>
{transcript}
</conversation>

Extract up to {max_memories} memories that are:
- technical discoveries/solutions (e.g., "discovered that systemMessage displays hook output")
- decisions/architecture choices (e.g., "decided to use PostgreSQL over MongoDB")
- learning insights/root causes (e.g., "root cause of the bug was incorrect async handling")
- user preferences (e.g., "user prefers dark mode")
- stable facts about the user or project (e.g., "user works at Google")

Rules:
- Extract as subject-predicate-object triples
- subject: who or what the memory is about
- predicate: the relation/action verb
- object: the value, target, or complement
- Ignore greetings, questions, and ephemeral task requests
- Focus on information that would be useful in future sessions
- If none found, return {{"memories": []}}

Output JSON schema (respond with this exact structure):
{{
  "memories": [
    {{
      "subject": "the subject (who/what)",
      "predicate": "the verb/relation",
      "object": "the value/target",
      "category": "preferences|facts|goals|discoveries",
      "confidence": 0.8
    }}
  ]
}}"""


def log(message: str):
    """Append to log file for debugging."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def load_recent_saves() -> dict:
    """Load recently saved content hashes (shared with stop-hook.py)."""
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


def parse_transcript(transcript_path: str, offset: int = 0) -> tuple[list, list]:
    """Parse transcript and extract user/assistant messages.

    Args:
        transcript_path: Path to the transcript JSONL file
        offset: Skip first N messages (for incremental processing)

    Returns:
        tuple: (user_messages, assistant_messages)
    """
    user_messages = []
    assistant_messages = []
    message_count = 0

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")

                    if entry_type not in ("user", "assistant"):
                        continue

                    message_count += 1

                    # Skip messages before offset (already processed)
                    if message_count <= offset:
                        continue

                    text = extract_text_from_entry(entry)
                    if not text:
                        continue

                    if entry_type == "user":
                        user_messages.append(text)
                    elif entry_type == "assistant":
                        assistant_messages.append(text)

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        log(f"Error parsing transcript: {e}")

    return user_messages, assistant_messages


def build_transcript_snippet(user_messages: list, assistant_messages: list) -> str:
    """Build a condensed transcript snippet for Claude CLI.

    Takes last N messages from each role and interleaves them.
    """
    # Take last N from each
    recent_user = user_messages[-MAX_USER_MESSAGES:]
    recent_assistant = assistant_messages[-MAX_ASSISTANT_MESSAGES:]

    # Build interleaved conversation
    lines = []

    # Add user messages
    for i, msg in enumerate(recent_user):
        # Truncate very long messages
        if len(msg) > 500:
            msg = msg[:500] + "..."
        lines.append(f"[User {i+1}]: {msg}")

    # Add assistant messages (summaries of key parts)
    for i, msg in enumerate(recent_assistant):
        # Truncate very long messages
        if len(msg) > 1000:
            msg = msg[:1000] + "..."
        lines.append(f"[Assistant {i+1}]: {msg}")

    snippet = "\n\n".join(lines)

    # Final truncation if needed
    if len(snippet) > MAX_TRANSCRIPT_CHARS:
        snippet = snippet[:MAX_TRANSCRIPT_CHARS] + "\n...(truncated)"

    return snippet


def call_claude_cli(prompt: str) -> dict | None:
    """Call Claude CLI and parse JSON response.

    Returns:
        dict with memories array, or None on failure
    """
    try:
        # Use claude CLI with JSON output
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        if result.returncode != 0:
            log(f"Claude CLI error: {result.stderr}")
            return None

        # Parse the output
        output = result.stdout.strip()

        # Claude CLI --output-format json wraps response in:
        # {"type":"result", "result": "actual response text", ...}
        try:
            wrapper = json.loads(output)
            if isinstance(wrapper, dict) and "result" in wrapper:
                # Extract the actual response from the wrapper
                response_text = wrapper.get("result", "")
                log(f"Extracted response ({len(response_text)} chars)")
            else:
                response_text = output
        except json.JSONDecodeError:
            response_text = output
            log("Failed to parse wrapper, using raw output")

        # Try to extract memories JSON from the response
        # Claude might wrap it in markdown code blocks
        json_match = re.search(r'\{[\s\S]*"memories"[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            return data

        # Log actual response for debugging
        log(f"Response text: {response_text[:500]}")
        return None

    except subprocess.TimeoutExpired:
        log("Claude CLI timeout")
        return None
    except json.JSONDecodeError as e:
        log(f"JSON parse error: {e}")
        return None
    except FileNotFoundError:
        log("Claude CLI not found")
        return None
    except Exception as e:
        log(f"Claude CLI exception: {e}")
        return None


def store_memory_item(subject: str, predicate: str, obj: str, category: str, confidence: float) -> bool:
    """Store memory via POST /v2/items (no OpenAI required)."""
    import urllib.request
    import urllib.error

    try:
        payload = {
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "category": category or "facts",
            "confidence": confidence,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{KIROKU_API}/v2/items",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            return True

    except Exception as e:
        log(f"Store error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="LLM-based memory extraction")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSONL")
    parser.add_argument("--source", required=True, help="Memory source (e.g., project:name)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N messages (incremental)")
    args = parser.parse_args()

    mode = "incremental" if args.offset > 0 else "full"
    log(f"Starting LLM analysis for {args.source} (mode={mode}, offset={args.offset})")

    # Validate transcript exists
    if not os.path.exists(args.transcript):
        log(f"Transcript not found: {args.transcript}")
        sys.exit(0)

    # Parse transcript (with offset for incremental processing)
    user_messages, assistant_messages = parse_transcript(args.transcript, args.offset)

    if not user_messages and not assistant_messages:
        log("No messages found in transcript")
        sys.exit(0)

    log(f"Found {len(user_messages)} user, {len(assistant_messages)} assistant messages")

    # Build transcript snippet
    snippet = build_transcript_snippet(user_messages, assistant_messages)

    if len(snippet) < 50:
        log("Transcript too short for analysis")
        sys.exit(0)

    # Build prompt
    prompt = MEMORY_EXTRACTION_PROMPT.format(
        transcript=snippet,
        max_memories=MAX_MEMORIES
    )

    # Call Claude CLI
    log("Calling Claude CLI...")
    result = call_claude_cli(prompt)

    if not result or "memories" not in result:
        log("No memories extracted from Claude CLI")
        sys.exit(0)

    memories = result.get("memories", [])
    log(f"Claude extracted {len(memories)} memories")

    # Load dedup cache
    recent = load_recent_saves()

    # Store each memory via POST /v2/items
    saved_count = 0
    for memory in memories:
        subject = memory.get("subject", "").strip()
        predicate = memory.get("predicate", "").strip()
        obj = memory.get("object", "").strip()

        if not subject or not predicate or not obj:
            continue

        category = memory.get("category", "facts")
        confidence = memory.get("confidence", 0.8)

        # Skip low confidence
        if confidence < 0.6:
            log(f"Skipping low confidence ({confidence}): {subject} {predicate}")
            continue

        # Check duplicate using subject+predicate+object as content
        content_key = f"{subject} {predicate} {obj}"
        if is_duplicate(content_key, args.source, recent):
            log(f"Duplicate skipped: {content_key[:50]}")
            continue

        # Store via /v2/items
        if store_memory_item(subject, predicate, obj, category, confidence):
            mark_saved(content_key, args.source, recent)
            saved_count += 1
            log(f"Saved ({category}): {subject} {predicate} {obj[:30]}")

    log(f"LLM analysis complete: {saved_count} memories saved")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(0)  # Always exit cleanly
