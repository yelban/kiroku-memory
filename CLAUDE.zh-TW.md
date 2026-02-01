# Kiroku Memory

> AI Agent 分層檢索記憶系統

基於 Rohit "How to Build an Agent That Never Forgets" 設計理念的 AI Agent 長期記憶系統。

**核心特點**：
- Hybrid Memory Stack：結合 append-only logs、結構化 facts、分類摘要
- Tiered Retrieval：摘要優先，按需深入
- Time Decay：記憶隨時間衰減
- Conflict Resolution：自動解決矛盾記憶

## 快速啟動

### 方式 A：PostgreSQL（生產環境）

```bash
# 啟動 PostgreSQL + pgvector
docker compose up -d

# 啟動 API
uv run uvicorn kiroku_memory.api:app --reload
```

### 方式 B：SurrealDB（桌面/嵌入式）

```bash
# 在 .env 設定後端
echo "BACKEND=surrealdb" >> .env

# 啟動 API（不需 Docker！）
uv run uvicorn kiroku_memory.api:app --reload
```

詳見 `docs/surrealdb-setup.md`。

## 環境變數

複製 `.env.example` 為 `.env`，設定：

```bash
# 後端選擇（postgres 或 surrealdb）
BACKEND=postgres

# PostgreSQL 設定（BACKEND=postgres 時）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/memory

# SurrealDB 設定（BACKEND=surrealdb 時）
SURREAL_URL=file://./data/kiroku
SURREAL_NAMESPACE=kiroku
SURREAL_DATABASE=memory

# Embeddings 必填
OPENAI_API_KEY=sk-xxx
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
- **SessionStart hook**：自動載入記憶上下文
- **PostToolUse hook**：長對話增量擷取（節流）
- **Stop hook**：雙階段擷取（Fast regex + Slow LLM）
- **優先級排序**：preferences > facts > goals（混合靜態+動態權重）
- **智慧截斷**：永不在分類中間截斷，保持完整性
- 手動命令管理記憶

詳見 `docs/claude-code-integration.md`。

## 文件

- `docs/architecture.md` - 架構設計
- `docs/development-journey.md` - 開發歷程
- `docs/user-guide.md` - 使用者手冊
- `docs/integration-guide.md` - 整合指南
- `docs/claude-code-integration.md` - Claude Code 整合指南
- `docs/surrealdb-setup.md` - SurrealDB 後端設定指南
- `docs/surrealdb-migration-plan.md` - Dual-backend 遷移計畫
- `docs/renaming-changelog.md` - 改名紀錄

## 專案結構

```
kiroku-memory/
├── kiroku_memory/           # 核心模組
│   ├── api.py               # FastAPI endpoints
│   ├── ingest.py            # 資源攝取
│   ├── extract.py           # Fact extraction
│   ├── classify.py          # 分類器
│   ├── conflict.py          # 衝突解決
│   ├── summarize.py         # 摘要生成
│   ├── observability.py     # 監控
│   ├── db/                  # 資料庫層
│   │   ├── entities.py      # Domain entities（後端無關）
│   │   ├── repositories/    # Repository pattern
│   │   │   ├── base.py      # 抽象介面
│   │   │   ├── factory.py   # 後端選擇
│   │   │   ├── postgres/    # PostgreSQL 實作
│   │   │   └── surrealdb/   # SurrealDB 實作
│   │   └── surrealdb/       # SurrealDB 模組
│   │       ├── connection.py
│   │       └── schema.surql
│   ├── embedding/           # Embedding 提供者
│   │   ├── base.py          # 提供者介面
│   │   ├── factory.py       # 提供者工廠
│   │   ├── openai_provider.py
│   │   └── local_provider.py
│   └── jobs/                # 維護任務
├── scripts/
│   └── migrate_backend.py   # 後端遷移 CLI
├── tests/                   # 測試
├── docs/                    # 文件
├── docker-compose.yml       # PostgreSQL 設定
└── pyproject.toml           # 專案設定
```

## 開發規範

- 語言：Python 3.11+
- 框架：FastAPI + SQLAlchemy 2.x
- 資料庫：PostgreSQL 16 + pgvector 或 SurrealDB（嵌入式）
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

## 疑難排解

### `.venv` scripts 報 "No such file or directory" 但檔案存在

原因：建立 `.venv` 時 `VIRTUAL_ENV` 環境變數指向其他專案，導致 shebang 路徑錯誤。

```bash
# 檢查 shebang
head -1 .venv/bin/uvicorn
# 若顯示其他專案路徑，需重建 venv

# 修復
unset VIRTUAL_ENV
rm -rf .venv
uv sync
```

### `/extract` 回傳空結果但 LLM 有正確回應

原因：OpenAI 有時回傳 `"object": null`，導致 Pydantic 驗證失敗。

已修復：`kiroku_memory/extract.py` 的 `ExtractedFact.object` 改為 `Optional[str]`。

## 翻譯

- [English](CLAUDE.md)
- [日本語](CLAUDE.ja.md)
