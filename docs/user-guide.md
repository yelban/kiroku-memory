# Kiroku Memory 使用者手冊

## 1. 快速開始

### 1.1 環境需求

- Python 3.11+
- Docker (用於 PostgreSQL + pgvector)
- OpenAI API Key

### 1.2 安裝

```bash
# 進入專案目錄
cd /path/to/kiroku-memory

# 安裝依賴
uv sync

# 複製環境變數檔案
cp .env.example .env

# 編輯 .env，設定 OPENAI_API_KEY
```

### 1.3 啟動服務

```bash
# 啟動 PostgreSQL + pgvector
docker compose up -d

# 啟動 API 服務
uv run uvicorn kiroku_memory.api:app --reload

# API 將運行在 http://localhost:8000
```

### 1.4 驗證安裝

```bash
# 健康檢查
curl http://localhost:8000/health
# 預期: {"status":"ok","version":"0.1.0"}

# 詳細健康狀態
curl http://localhost:8000/health/detailed
```

## 2. 核心功能使用

### 2.1 攝取訊息 (Ingest)

將原始訊息存入記憶系統：

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "我叫小明，在 Google 當工程師，喜歡喝咖啡",
    "source": "user:xiaoming",
    "metadata": {"channel": "telegram"}
  }'
```

回應：
```json
{
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-31T12:00:00"
}
```

### 2.2 抽取事實 (Extract)

將原始訊息抽取為結構化 facts：

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

回應：
```json
{
  "resource_id": "550e8400-...",
  "items_created": 3,
  "item_ids": ["...", "...", "..."]
}
```

### 2.3 檢索記憶 (Retrieve)

Tiered retrieval - 先摘要，再 items：

```bash
# 基本檢索
curl "http://localhost:8000/retrieve?query=小明喜歡什麼"

# 指定分類
curl "http://localhost:8000/retrieve?query=工作&category=facts"

# 限制數量
curl "http://localhost:8000/retrieve?query=偏好&limit=5"
```

回應結構：
```json
{
  "query": "小明喜歡什麼",
  "categories": [
    {
      "name": "preferences",
      "summary": "小明喜歡喝咖啡，偏好使用 Mac..."
    }
  ],
  "items": [
    {
      "subject": "小明",
      "predicate": "喜歡",
      "object": "咖啡",
      "category": "preferences",
      "confidence": 0.95
    }
  ],
  "total_items": 10
}
```

### 2.4 取得 Agent Context

為 Agent system prompt 準備記憶上下文：

```bash
curl "http://localhost:8000/context"

# 指定分類
curl "http://localhost:8000/context?categories=preferences,facts"
```

回應（Markdown 格式）：
```
## User Memory Context

### Preferences
小明喜歡喝咖啡，偏好使用 Mac 電腦...

### Facts
小明在 Google 工作，是一名工程師...
```

### 2.5 生成摘要 (Summarize)

為所有分類生成 LLM 摘要：

```bash
curl -X POST http://localhost:8000/summarize
```

### 2.6 列出資料

```bash
# 列出所有分類
curl http://localhost:8000/categories

# 列出 items
curl "http://localhost:8000/items?category=preferences&status=active&limit=20"

# 列出原始資源
curl "http://localhost:8000/resources?source=user:xiaoming&limit=50"
```

## 3. 維護任務

### 3.1 手動執行

```bash
# 每日維護：合併重複、提升熱門記憶
curl -X POST http://localhost:8000/jobs/nightly

# 每週維護：時間衰減、封存舊資料
curl -X POST http://localhost:8000/jobs/weekly

# 每月維護：重建 embeddings 和 knowledge graph
curl -X POST http://localhost:8000/jobs/monthly
```

### 3.2 設定 Cron 排程

```bash
# 編輯 crontab
crontab -e

# 加入以下排程
# 每天凌晨 2 點執行 nightly job
0 2 * * * curl -X POST http://localhost:8000/jobs/nightly

# 每週日凌晨 3 點執行 weekly job
0 3 * * 0 curl -X POST http://localhost:8000/jobs/weekly

# 每月 1 號凌晨 4 點執行 monthly job
0 4 1 * * curl -X POST http://localhost:8000/jobs/monthly
```

## 4. 監控與除錯

### 4.1 Metrics

```bash
curl http://localhost:8000/metrics
```

回應：
```json
{
  "counters": {
    "ingest_count": 150,
    "extract_count": 120,
    "retrieve_count": 500,
    "error_count": 2
  },
  "latencies": {
    "retrieve_p50": 15.5,
    "retrieve_p95": 45.2,
    "retrieve_p99": 120.0
  },
  "gauges": {
    "active_items": 1500,
    "total_resources": 200,
    "total_embeddings": 1500
  }
}
```

### 4.2 重設 Metrics

```bash
curl -X POST http://localhost:8000/metrics/reset
```

### 4.3 詳細健康檢查

```bash
curl http://localhost:8000/health/detailed
```

回應：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:00:00",
  "checks": {
    "database": {"status": "ok"},
    "data": {
      "active_items": 1500,
      "resources": 200,
      "embeddings": 1500
    }
  }
}
```

## 5. 分類說明

系統預設 6 個分類：

| 分類 | 說明 | 範例 |
|------|------|------|
| `preferences` | 偏好設定 | 喜歡咖啡、使用 VSCode |
| `facts` | 事實資訊 | 在 Google 工作、住台北 |
| `events` | 事件活動 | 下週有會議、去年去過日本 |
| `relationships` | 人際關係 | 認識 John、老闆是 Mary |
| `skills` | 技能專長 | 會 Python、正在學 Rust |
| `goals` | 目標計畫 | 想買房、計畫創業 |

## 6. 最佳實踐

### 6.1 訊息攝取

- **結構化 source**：使用 `platform:user_id` 格式，如 `telegram:123456`
- **加入 metadata**：記錄來源頻道、時間等
- **批次處理**：大量資料時使用 `/process` endpoint

### 6.2 檢索優化

- **先用 context**：Agent 應先取得 `/context`，必要時再 `/retrieve`
- **指定分類**：明確分類可加快檢索
- **適當 limit**：不要一次取太多 items

### 6.3 維護排程

- **Nightly**：每日執行，保持記憶整潔
- **Weekly**：每週執行，控制資料量
- **Monthly**：每月執行，重建索引確保品質

## 7. 故障排除

### 7.1 API 無回應

```bash
# 檢查服務狀態
curl http://localhost:8000/health

# 檢查 Docker 容器
docker ps

# 重啟服務
docker compose restart
uv run uvicorn kiroku_memory.api:app --reload
```

### 7.2 Extraction 失敗

```bash
# 確認 OpenAI API key
grep OPENAI_API_KEY .env

# 檢查 API 配額
# 訪問 https://platform.openai.com/usage
```

### 7.3 資料庫連線問題

```bash
# 檢查 PostgreSQL 容器
docker logs memory-db

# 重建資料庫
docker compose down -v
docker compose up -d
```

## 8. 進階設定

### 8.1 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `DATABASE_URL` | postgresql+asyncpg://... | 資料庫連線 |
| `OPENAI_API_KEY` | (必填) | OpenAI API 金鑰 |
| `EMBEDDING_MODEL` | text-embedding-3-small | Embedding 模型 |
| `EMBEDDING_DIMENSIONS` | 1536 | 向量維度 |
| `REDIS_URL` | redis://localhost:6379/0 | Redis (未來用) |
| `DEBUG` | false | 除錯模式 |

### 8.2 自訂分類

編輯 `kiroku_memory/classify.py`：

```python
DEFAULT_CATEGORIES = [
    ("preferences", "User preferences..."),
    ("facts", "Factual information..."),
    # 加入新分類
    ("custom", "Your custom category..."),
]
```

### 8.3 調整時間衰減

編輯 `kiroku_memory/jobs/weekly.py`：

```python
DEFAULT_HALF_LIFE_DAYS = 30  # 調整半衰期
MAX_AGE_DAYS = 90  # 調整最大保留天數
```
