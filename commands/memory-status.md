---
allowed-tools: Bash(python3:*)
description: "Check Kiroku Memory system status"
---

# /memory-status

Display the status of the Kiroku Memory system including service health, statistics, and categories.

## Your Task

Run the memory-status script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-status.py
```

Display the results to the user. If the service is not running, provide instructions to start it:

```bash
cd ~/path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
```
