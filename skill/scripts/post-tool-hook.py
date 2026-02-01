#!/usr/bin/env python3
"""PostToolUse Hook with throttling for incremental memory capture.

Triggers memory extraction periodically during long conversations,
not just at /exit. Uses throttling to avoid excessive API calls.

Throttle conditions (all must be met):
- At least MIN_INTERVAL_SECONDS since last capture
- At least MIN_NEW_MESSAGES new messages since last capture
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from hashlib import md5

# === Configuration ===
MIN_INTERVAL_SECONDS = 300  # 5 minutes minimum between captures
MIN_NEW_MESSAGES = 10  # At least 10 new messages to trigger
CACHE_DIR = Path.home() / ".cache" / "kiroku-memory"
THROTTLE_FILE = CACHE_DIR / "throttle-state.json"
LOG_FILE = CACHE_DIR / "post-tool-hook.log"

# API endpoint
KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")


def log(message: str):
    """Append to log file for debugging."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def get_session_key(transcript_path: str) -> str:
    """Generate a unique key for this session based on transcript path."""
    return md5(transcript_path.encode()).hexdigest()[:12]


def load_throttle_state() -> dict:
    """Load throttle state from cache."""
    try:
        if THROTTLE_FILE.exists():
            with open(THROTTLE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"sessions": {}}


def save_throttle_state(state: dict):
    """Save throttle state to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(THROTTLE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def count_messages(transcript_path: str) -> int:
    """Count user and assistant messages in transcript."""
    count = 0
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")
                    if entry_type in ("user", "assistant"):
                        count += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return count


def should_trigger(session_key: str, current_count: int, state: dict) -> tuple[bool, str]:
    """Check if we should trigger memory capture.

    Returns:
        (should_trigger, reason)
    """
    session_state = state.get("sessions", {}).get(session_key, {})

    # First time for this session
    if not session_state:
        return False, "first_session_skip"  # Skip first trigger, wait for more content

    last_capture = session_state.get("last_capture")
    last_count = session_state.get("message_count", 0)

    # Check time interval
    if last_capture:
        last_time = datetime.fromisoformat(last_capture)
        elapsed = (datetime.now() - last_time).total_seconds()
        if elapsed < MIN_INTERVAL_SECONDS:
            return False, f"too_soon_{int(elapsed)}s"

    # Check message count
    new_messages = current_count - last_count
    if new_messages < MIN_NEW_MESSAGES:
        return False, f"too_few_messages_{new_messages}"

    return True, f"ok_{new_messages}_new_messages"


def get_project_name(cwd: str) -> str:
    """Extract project name from working directory."""
    if not cwd:
        return ""
    return Path(cwd).name


def spawn_incremental_worker(transcript_path: str, source: str, offset: int):
    """Spawn background worker for incremental memory extraction."""
    try:
        llm_script = Path(__file__).parent / "stop-hook-llm.py"
        if not llm_script.exists():
            log(f"LLM script not found: {llm_script}")
            return

        # Pass offset to worker for incremental processing
        subprocess.Popen(
            [
                sys.executable,
                str(llm_script),
                "--transcript", transcript_path,
                "--source", source,
                "--offset", str(offset),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Fully detach from parent
        )
        log(f"Spawned incremental worker with offset={offset}")
    except Exception as e:
        log(f"Failed to spawn worker: {e}")


def main():
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        cwd = input_data.get("cwd", "")
        transcript_path = input_data.get("transcript_path", "")
        tool_name = input_data.get("tool_name", "")

        # Skip if no transcript
        if not transcript_path or not os.path.exists(transcript_path):
            sys.exit(0)

        session_key = get_session_key(transcript_path)
        current_count = count_messages(transcript_path)

        # Load throttle state
        state = load_throttle_state()

        # Initialize session if first time
        if session_key not in state.get("sessions", {}):
            state.setdefault("sessions", {})[session_key] = {
                "last_capture": None,
                "message_count": current_count,
                "transcript_path": transcript_path
            }
            save_throttle_state(state)
            log(f"Session {session_key} initialized with {current_count} messages")
            sys.exit(0)

        # Check throttle conditions
        should, reason = should_trigger(session_key, current_count, state)

        if not should:
            # Silently skip
            sys.exit(0)

        log(f"Triggering incremental capture: {reason}")

        # Get last processed offset
        last_count = state["sessions"][session_key].get("message_count", 0)

        # Determine source
        project = get_project_name(cwd)
        source = f"project:{project}" if project else "global:user"

        # Spawn background worker with offset
        spawn_incremental_worker(transcript_path, source, last_count)

        # Update throttle state
        state["sessions"][session_key] = {
            "last_capture": datetime.now().isoformat(),
            "message_count": current_count,
            "transcript_path": transcript_path
        }
        save_throttle_state(state)

        sys.exit(0)

    except Exception as e:
        log(f"Error: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
