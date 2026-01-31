# Kiroku Memory 整合指南

本指南說明如何將 Kiroku Memory 整合到各種 AI Agent 應用中。

## 1. Claude Code 整合

### 1.1 作為 MCP Server

將記憶系統包裝為 MCP (Model Context Protocol) Server，讓 Claude Code 直接存取。

**建立 MCP Server（`memory_mcp.py`）**：

```python
#!/usr/bin/env python3
"""Memory System MCP Server for Claude Code"""

import asyncio
import json
from mcp.server import Server
from mcp.types import Tool, TextContent

from kiroku_memory.db.database import get_session
from kiroku_memory.ingest import ingest_message
from kiroku_memory.extract import extract_and_store
from kiroku_memory.summarize import get_tiered_context
from kiroku_memory.api import retrieve_memory

app = Server("memory-system")

@app.tool("memory_ingest")
async def memory_ingest(content: str, source: str = "claude-code") -> str:
    """Ingest a message into memory system"""
    async with get_session() as session:
        resource_id = await ingest_message(session, content, source)
        item_ids = await extract_and_store(session, resource_id)
        return json.dumps({
            "resource_id": str(resource_id),
            "items_created": len(item_ids)
        })

@app.tool("memory_retrieve")
async def memory_retrieve(query: str, category: str = None, limit: int = 10) -> str:
    """Retrieve memories related to query"""
    async with get_session() as session:
        # 使用 tiered context
        context = await get_tiered_context(session)
        return context

@app.tool("memory_context")
async def memory_context(categories: str = None) -> str:
    """Get memory context for agent prompt"""
    async with get_session() as session:
        cat_list = categories.split(",") if categories else None
        return await get_tiered_context(session, cat_list)

if __name__ == "__main__":
    asyncio.run(app.run())
```

**設定 Claude Code（`~/.claude/mcp.json`）**：

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["run", "python", "/path/to/kiroku-memory/memory_mcp.py"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://...",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

### 1.2 作為 Skill

建立 Claude Code Skill 讓使用者透過 `/memory` 命令使用。

**建立 Skill 目錄（`~/.claude/skills/memory-system/`）**：

```
memory-system/
├── skill.md
└── scripts/
    ├── ingest.py
    ├── retrieve.py
    └── context.py
```

**skill.md**：

```markdown
# Memory System Skill

使用者記憶管理系統。

## 命令

- `/memory save <內容>` - 儲存記憶
- `/memory search <查詢>` - 搜尋記憶
- `/memory context` - 取得記憶上下文

## 使用方式

\`\`\`bash
# 儲存記憶
uv run python ~/.claude/skills/memory-system/scripts/ingest.py "用戶喜歡咖啡"

# 搜尋記憶
uv run python ~/.claude/skills/memory-system/scripts/retrieve.py "喜歡什麼"

# 取得上下文
uv run python ~/.claude/skills/memory-system/scripts/context.py
\`\`\`
```

**scripts/ingest.py**：

```python
#!/usr/bin/env python3
import sys
import asyncio
import httpx

async def main():
    content = " ".join(sys.argv[1:])
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/ingest",
            json={"content": content, "source": "claude-code-skill"}
        )
        data = response.json()

        # Extract facts
        await client.post(
            "http://localhost:8000/extract",
            json={"resource_id": data["resource_id"]}
        )

        print(f"已儲存記憶: {data['resource_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.3 在 CLAUDE.md 中使用

在專案 `CLAUDE.md` 中加入記憶系統指引：

```markdown
## Memory System

本專案使用 Kiroku Memory 管理長期記憶。

### 啟動服務

\`\`\`bash
cd /path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
\`\`\`

### 每次對話前

1. 取得記憶上下文：
\`\`\`bash
curl http://localhost:8000/context
\`\`\`

2. 將上下文加入 system prompt

### 對話結束後

將重要資訊存入記憶：
\`\`\`bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "source": "project:xxx"}'
\`\`\`
```

## 2. Codex CLI 整合

### 2.1 自動載入記憶

在執行 Codex 前取得記憶上下文：

```bash
#!/bin/bash
# codex-with-memory.sh

# 取得記憶上下文
MEMORY_CONTEXT=$(curl -s http://localhost:8000/context | jq -r '.context')

# 建立增強版 prompt
ENHANCED_PROMPT="$MEMORY_CONTEXT

---

$1"

# 執行 Codex
codex -m gpt-5.2-codex "$ENHANCED_PROMPT"
```

### 2.2 對話後儲存

```bash
#!/bin/bash
# save-to-memory.sh

# 從 Codex 輸出中提取關鍵資訊並儲存
CONTENT="$1"
curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$CONTENT\", \"source\": \"codex\"}"
```

## 3. Telegram Bot 整合

### 3.1 修改 bot.mjs

在現有的 `bot.mjs` 中加入記憶功能：

```javascript
import "dotenv/config";
import TelegramBot from "node-telegram-bot-api";
import { query } from "@anthropic-ai/claude-agent-sdk";

const MEMORY_API = "http://localhost:8000";

// 取得記憶上下文
async function getMemoryContext(userId) {
  try {
    const response = await fetch(`${MEMORY_API}/context`);
    const data = await response.json();
    return data.context;
  } catch (error) {
    console.error("Failed to get memory context:", error);
    return "";
  }
}

// 儲存對話到記憶
async function saveToMemory(userId, content) {
  try {
    // Ingest
    const ingestRes = await fetch(`${MEMORY_API}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        source: `telegram:${userId}`,
        metadata: { platform: "telegram" }
      })
    });
    const ingestData = await ingestRes.json();

    // Extract
    await fetch(`${MEMORY_API}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resource_id: ingestData.resource_id })
    });
  } catch (error) {
    console.error("Failed to save memory:", error);
  }
}

// 增強版 system prompt
async function getEnhancedSystemPrompt(userId) {
  const memoryContext = await getMemoryContext(userId);
  return `你是一個友善的 AI 助手。

${memoryContext}

語言規範：
- 一律使用繁體中文（台灣用語）回覆`;
}

// 處理消息
bot.on("message", async (msg) => {
  if (!msg.text || msg.text.startsWith("/")) return;

  const chatId = msg.chat.id;
  const userId = msg.from.id;

  bot.sendChatAction(chatId, "typing");

  try {
    // 取得包含記憶的 system prompt
    const systemPrompt = await getEnhancedSystemPrompt(userId);

    let response = "";
    for await (const message of query({
      prompt: msg.text,
      options: {
        model: MODEL,
        systemPrompt,
        // ...其他選項
      },
    })) {
      if ("result" in message) {
        response = message.result;
      }
    }

    // 儲存用戶訊息到記憶
    await saveToMemory(userId, msg.text);

    // 傳送回覆
    await bot.sendMessage(chatId, response);
  } catch (error) {
    console.error("Error:", error.message);
    await bot.sendMessage(chatId, `出錯了: ${error.message}`);
  }
});

// /remember 命令 - 手動儲存記憶
bot.onText(/\/remember (.+)/, async (msg, match) => {
  const userId = msg.from.id;
  const content = match[1];

  await saveToMemory(userId, content);
  await bot.sendMessage(msg.chat.id, "已記住！");
});

// /recall 命令 - 搜尋記憶
bot.onText(/\/recall (.+)/, async (msg, match) => {
  const query = match[1];

  try {
    const response = await fetch(
      `${MEMORY_API}/retrieve?query=${encodeURIComponent(query)}&limit=5`
    );
    const data = await response.json();

    let reply = "找到以下記憶：\n\n";
    for (const item of data.items) {
      reply += `• ${item.subject} ${item.predicate} ${item.object}\n`;
    }

    await bot.sendMessage(msg.chat.id, reply);
  } catch (error) {
    await bot.sendMessage(msg.chat.id, "搜尋失敗");
  }
});
```

## 4. LINE Bot 整合

### 4.1 修改 line-bot.mjs

在現有的 `line-bot.mjs` 中加入記憶功能：

```javascript
const MEMORY_API = "http://localhost:8000";

// 記憶管理函數（同 Telegram）
async function getMemoryContext(userId) {
  // ...同上
}

async function saveToMemory(userId, content) {
  // ...同上，但 source 改為 `line:${userId}`
}

// 處理文字訊息
async function handleTextMessage(event) {
  const userId = event.source.userId;
  const text = event.message.text;

  // 取得記憶上下文
  const memoryContext = await getMemoryContext(userId);

  // 增強 system prompt
  const systemPrompt = `${SYSTEM_PROMPT}\n\n${memoryContext}`;

  // 呼叫 Claude
  let response = "";
  for await (const message of query({
    prompt: text,
    options: {
      model: MODEL,
      systemPrompt,
      // ...
    },
  })) {
    if ("result" in message) {
      response = message.result;
    }
  }

  // 儲存到記憶
  await saveToMemory(userId, text);

  return { type: "text", text: response };
}

// 記憶相關命令
if (text.startsWith("/remember ")) {
  const content = text.slice(10);
  await saveToMemory(userId, content);
  return { type: "text", text: "已記住！" };
}

if (text.startsWith("/recall ")) {
  const query = text.slice(8);
  const response = await fetch(
    `${MEMORY_API}/retrieve?query=${encodeURIComponent(query)}&limit=5`
  );
  const data = await response.json();

  let reply = "找到以下記憶：\n";
  for (const item of data.items) {
    reply += `• ${item.subject} ${item.predicate} ${item.object}\n`;
  }

  return { type: "text", text: reply };
}
```

## 5. 通用整合模式

### 5.1 Python 客戶端

```python
import httpx
from dataclasses import dataclass

@dataclass
class MemoryClient:
    base_url: str = "http://localhost:8000"

    async def ingest(self, content: str, source: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/ingest",
                json={"content": content, "source": source}
            )
            data = response.json()

            # Auto extract
            await client.post(
                f"{self.base_url}/extract",
                json={"resource_id": data["resource_id"]}
            )

            return data["resource_id"]

    async def retrieve(self, query: str, limit: int = 10) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/retrieve",
                params={"query": query, "limit": limit}
            )
            return response.json()

    async def get_context(self, categories: list[str] = None) -> str:
        async with httpx.AsyncClient() as client:
            params = {}
            if categories:
                params["categories"] = ",".join(categories)
            response = await client.get(
                f"{self.base_url}/context",
                params=params
            )
            return response.json()["context"]

# 使用範例
async def main():
    memory = MemoryClient()

    # 儲存
    await memory.ingest("用戶喜歡深色模式", "my-agent")

    # 取得上下文
    context = await memory.get_context()
    print(context)

    # 搜尋
    results = await memory.retrieve("喜歡什麼")
    print(results)
```

### 5.2 JavaScript/TypeScript 客戶端

```typescript
class MemoryClient {
  constructor(private baseUrl = "http://localhost:8000") {}

  async ingest(content: string, source: string): Promise<string> {
    const ingestRes = await fetch(`${this.baseUrl}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, source })
    });
    const data = await ingestRes.json();

    // Auto extract
    await fetch(`${this.baseUrl}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resource_id: data.resource_id })
    });

    return data.resource_id;
  }

  async retrieve(query: string, limit = 10): Promise<any> {
    const params = new URLSearchParams({ query, limit: String(limit) });
    const response = await fetch(`${this.baseUrl}/retrieve?${params}`);
    return response.json();
  }

  async getContext(categories?: string[]): Promise<string> {
    const params = new URLSearchParams();
    if (categories) {
      params.set("categories", categories.join(","));
    }
    const response = await fetch(`${this.baseUrl}/context?${params}`);
    const data = await response.json();
    return data.context;
  }
}

// 使用範例
const memory = new MemoryClient();

// 在 Agent 對話前
const context = await memory.getContext();
const enhancedPrompt = `${context}\n\n${userMessage}`;

// 對話後儲存
await memory.ingest(userMessage, "my-agent");
```

## 6. 最佳實踐

### 6.1 何時儲存記憶

- ✅ 用戶明確表達的偏好
- ✅ 重要的事實資訊
- ✅ 約定或計畫
- ❌ 閒聊內容
- ❌ 一次性查詢

### 6.2 如何使用上下文

1. **對話開始時**：取得 `/context` 加入 system prompt
2. **特定查詢時**：使用 `/retrieve` 搜尋相關記憶
3. **需要詳情時**：使用 `/items` 取得完整 facts

### 6.3 記憶隔離

使用 `source` 欄位區分不同用戶/平台：

```
telegram:123456
line:U1234567890
claude-code:project-name
```

## 7. 效能考量

### 7.1 快取策略

- Category summaries 可以快取（更新頻率低）
- Context 可以在對話開始時取得一次
- 不需要每條訊息都 retrieve

### 7.2 批次處理

大量訊息時使用 `/process` 而非逐條 `/extract`：

```bash
# 批次處理未處理的 resources
curl -X POST "http://localhost:8000/process?limit=100"
```

### 7.3 分類過濾

明確分類可減少資料量：

```bash
# 只取得偏好相關的上下文
curl "http://localhost:8000/context?categories=preferences"
```
