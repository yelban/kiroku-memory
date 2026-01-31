# Kiroku Memory API Contract

## Base URL

```
http://localhost:8000
```

## Endpoints

### POST /ingest
儲存原始訊息到記憶系統。

**Request:**
```json
{
  "content": "用戶喜歡深色模式",
  "source": "project:kiroku-memory",
  "metadata": {"category_hint": "preferences"}
}
```

**Response:**
```json
{
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-31T12:00:00"
}
```

**curl 範例:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"content":"用戶喜歡深色模式","source":"global:user"}'
```

---

### POST /extract
從資源抽取結構化事實。

**Request:**
```json
{
  "resource_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "resource_id": "550e8400-...",
  "items_created": 1,
  "item_ids": ["..."]
}
```

---

### GET /retrieve
分層檢索記憶（摘要 + 事實）。

**Parameters:**
- `query` (required): 搜尋關鍵字
- `category` (optional): 分類過濾
- `limit` (optional): 最大結果數，預設 20

**Response:**
```json
{
  "query": "深色模式",
  "categories": [
    {
      "id": "...",
      "name": "preferences",
      "summary": "用戶偏好深色模式...",
      "updated_at": "2026-01-31T12:00:00"
    }
  ],
  "items": [
    {
      "id": "...",
      "subject": "用戶",
      "predicate": "喜歡",
      "object": "深色模式",
      "category": "preferences",
      "confidence": 0.9,
      "status": "active",
      "created_at": "2026-01-31T12:00:00"
    }
  ],
  "total_items": 1
}
```

**curl 範例:**
```bash
curl "http://localhost:8000/retrieve?query=深色模式&limit=5"
```

---

### GET /context
取得 Agent prompt 用的記憶上下文。

**Parameters:**
- `categories` (optional): 逗號分隔的分類列表

**Response:**
```json
{
  "context": "## User Memory Context\n\n### Preferences\n用戶偏好深色模式..."
}
```

**curl 範例:**
```bash
curl "http://localhost:8000/context"
curl "http://localhost:8000/context?categories=preferences,facts"
```

---

### GET /health
基本健康檢查。

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### GET /health/detailed
詳細健康狀態，含記憶統計。

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:00:00",
  "checks": {
    "database": {"status": "ok"},
    "data": {
      "active_items": 150,
      "resources": 50,
      "embeddings": 150
    }
  }
}
```

---

### GET /metrics
應用程式指標。

**Response:**
```json
{
  "counters": {
    "ingest_count": 100,
    "extract_count": 80,
    "retrieve_count": 500,
    "error_count": 2
  },
  "latencies": {
    "retrieve_p50": 15.5,
    "retrieve_p95": 45.2
  },
  "gauges": {
    "active_items": 150,
    "total_resources": 50
  }
}
```

---

### GET /categories
列出所有分類。

**Response:**
```json
[
  {
    "id": "...",
    "name": "preferences",
    "summary": "...",
    "updated_at": "2026-01-31T12:00:00"
  }
]
```

---

## Source 格式

| 範圍 | 格式 | 範例 |
|------|------|------|
| 全域 | `global:user` | 個人偏好、通用知識 |
| 專案 | `project:<name>` | `project:kiroku-memory` |

## 分類

- `preferences` - 偏好設定
- `facts` - 事實資訊
- `events` - 事件活動
- `relationships` - 人際關係
- `skills` - 技能專長
- `goals` - 目標計畫
