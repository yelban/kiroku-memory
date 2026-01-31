---
allowed-tools: Bash(python3:*)
description: "Store a memory in Kiroku Memory system"
---

# /remember

Store information in the Kiroku Memory system for long-term persistence.

## Arguments

The content to remember, with optional flags:
- `--category <cat>` or `-c <cat>`: Category hint (preferences, facts, events, relationships, skills, goals)
- `--global` or `-g`: Store as global memory (cross-project)
- `--project <name>` or `-p <name>`: Specify project name

## Examples

```
/remember 用戶偏好深色模式
/remember --category preferences 喜歡用 Neovim
/remember --global 暱稱叫吹吹
```

## Your Task

Run the remember script with the user's input:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/remember.py <user_args>
```

Report the result to the user. If the API is not available, suggest starting the Kiroku Memory service.
