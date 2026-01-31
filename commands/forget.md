---
allowed-tools: Bash(python3:*)
description: "Archive or delete memories from Kiroku Memory system"
---

# /forget

Search for and manage removal of memories from the Kiroku Memory system.

## Arguments

Search query to find memories to forget:
- `--category <cat>` or `-c <cat>`: Filter by category
- `--limit <n>` or `-l <n>`: Max items to show (default: 5)
- `--force` or `-f`: Skip confirmation

## Examples

```
/forget 舊的偏好設定
/forget --category facts 過時的資訊
```

## Your Task

Run the forget script with the user's input:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forget.py <user_args>
```

Show matching memories and guide the user on how to remove them.
