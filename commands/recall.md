---
allowed-tools: Bash(python3:*)
description: "Search memories in Kiroku Memory system"
---

# /recall

Search and retrieve memories from the Kiroku Memory system.

## Arguments

Search query with optional flags:
- `--category <cat>` or `-c <cat>`: Filter by category
- `--project` or `-p`: Only search current project memories
- `--global` or `-g`: Only search global memories
- `--limit <n>` or `-l <n>`: Max results (default: 10)
- `--context`: Show full tiered context instead of search

## Examples

```
/recall 編輯器偏好
/recall --category preferences
/recall --context
/recall --project 資料庫設計
```

## Your Task

Run the recall script with the user's input:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recall.py <user_args>
```

Display the results to the user in a readable format.
