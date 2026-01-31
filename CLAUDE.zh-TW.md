# Kiroku Memory

> Tiered Retrieval Memory System for AI Agents

這是一個 AI Agent 長期記憶系統，基於 Rohit 的 "How to Build an Agent That Never Forgets" 設計理念實作。

**核心特點**：
- Hybrid Memory Stack：結合 append-only logs、結構化 facts、分類摘要
- Tiered Retrieval：摘要優先，按需深入
- Time Decay：記憶隨時間衰減
- Conflict Resolution：自動解決矛盾記憶

## 快速啟動

```bash
# 啟動 PostgreSQL + pgvector
docker compose up -d

# 啟動 API
uv run uvicorn kiroku_memory.api:app --reload

# 健康檢查
curl http://localhost:8000/health
```

## 環境變數

複製 `.env.example` 為 `.env`，設定：

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/memory
OPENAI_API_KEY=sk-xxx  # 必填
```

## API 端點

### 核心功能
| Method | Path | 功能 |
|--------|------|------|
| POST | /ingest | 攝取原始訊息 |
| GET | /retrieve | Tiered 檢索 |
| GET | /context | Agent prompt 上下文 |

### 智慧功能
| Method | Path | 功能 |
|--------|------|------|
| POST | /extract | 抽取 facts |
| POST | /summarize | 生成摘要 |

### 維護任務
| Method | Path | 功能 |
|--------|------|------|
| POST | /jobs/nightly | 每日維護 |
| POST | /jobs/weekly | 每週維護 |
| POST | /jobs/monthly | 每月維護 |

### 監控
| Method | Path | 功能 |
|--------|------|------|
| GET | /health | 健康檢查 |
| GET | /metrics | 應用指標 |

## 整合範例

### 在其他 Agent 中使用

```javascript
// 取得記憶上下文
const context = await fetch("http://localhost:8000/context").then(r => r.json());

// 加入 system prompt
const enhancedPrompt = `${context.context}\n\n${originalPrompt}`;

// 對話後儲存重要資訊
await fetch("http://localhost:8000/ingest", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ content: "用戶喜歡...", source: "my-agent" })
});
```

## Claude Code 整合

已實作完整的 Claude Code 整合：

```
~/.claude/skills/kiroku-memory/
├── SKILL.md              # 使用說明（EN）
├── SKILL.zh-TW.md        # 繁體中文
├── SKILL.ja.md           # 日本語
├── scripts/              # /remember, /recall, /forget, /memory-status
├── references/           # 詳細文件
└── assets/               # 安裝腳本
```

**功能**：
- SessionStart hook 自動載入記憶上下文
- Stop hook 智慧儲存重要對話
- 手動命令管理記憶

詳見 `docs/claude-code-integration.md`

## 文件

- `docs/architecture.md` - 架構設計
- `docs/development-journey.md` - 開發歷程
- `docs/user-guide.md` - 使用者手冊
- `docs/integration-guide.md` - 整合指南
- `docs/claude-code-integration.md` - Claude Code 整合指南
- `docs/renaming-changelog.md` - 改名紀錄

## 專案結構

```
kiroku-memory/
├── kiroku_memory/       # 核心模組
│   ├── api.py           # FastAPI endpoints
│   ├── ingest.py        # 資源攝取
│   ├── extract.py       # Fact extraction
│   ├── classify.py      # 分類器
│   ├── conflict.py      # 衝突解決
│   ├── summarize.py     # 摘要生成
│   ├── embedding.py     # 向量搜尋
│   ├── observability.py # 監控
│   ├── db/              # 資料庫
│   └── jobs/            # 維護任務
├── tests/               # 測試
├── docs/                # 文件
├── docker-compose.yml   # PostgreSQL 設定
└── pyproject.toml       # 專案設定
```

## 開發規範

- 語言：Python 3.11+
- 框架：FastAPI + SQLAlchemy 2.x
- 資料庫：PostgreSQL 16 + pgvector
- 依賴管理：uv
- 測試：pytest + pytest-asyncio

## 常用命令

```bash
# 執行測試
uv run pytest

# 格式化
uv run ruff format .

# 型別檢查
uv run mypy kiroku_memory/
```

## 翻譯

- [English](CLAUDE.md)
- [日本語](CLAUDE.ja.md)
