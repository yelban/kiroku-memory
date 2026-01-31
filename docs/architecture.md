# AI Agent Memory System 架構設計

## 1. 設計理念

### 1.1 核心問題

傳統 RAG（Retrieval-Augmented Generation）在大規模應用時面臨以下挑戰：

1. **語義相似 ≠ 事實正確**：Embeddings 捕捉的是語義相似度，而非事實真實性
2. **缺乏時間上下文**：無法處理「用戶以前喜歡 A，現在喜歡 B」的情境
3. **記憶矛盾**：隨時間累積的資訊可能相互衝突
4. **擴展性不足**：當記憶達到數萬條時，檢索效能急劇下降

### 1.2 設計目標

- **Memory as Infrastructure**：將記憶視為基礎設施，而非功能
- **Persistent Identity**：跨 session 保持穩定的記憶
- **Evolving Memory**：像人類記憶一樣整合、衰減、合併
- **Tiered Retrieval**：分層檢索，摘要優先，按需深入

## 2. 架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent Memory System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  Ingest  │───▶│ Extract  │───▶│ Classify │───▶│ Conflict │   │
│  │ (Raw Log)│    │ (Facts)  │    │(Category)│    │ Resolver │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│       │                                               │          │
│       ▼                                               ▼          │
│  ┌──────────┐                                   ┌──────────┐    │
│  │Resources │                                   │  Items   │    │
│  │(append)  │                                   │ (active) │    │
│  └──────────┘                                   └──────────┘    │
│                                                      │           │
│                    ┌─────────────────────────────────┤           │
│                    │                                 │           │
│                    ▼                                 ▼           │
│              ┌──────────┐                     ┌──────────┐       │
│              │Embeddings│                     │ Summary  │       │
│              │(pgvector)│                     │ Builder  │       │
│              └──────────┘                     └──────────┘       │
│                    │                                 │           │
│                    └─────────────┬───────────────────┘           │
│                                  ▼                               │
│                           ┌──────────┐                           │
│                           │ Retrieve │                           │
│                           │ (Tiered) │                           │
│                           └──────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 資料層架構

### 3.1 Hybrid Memory Stack

採用混合架構，結合檔案系統和資料庫的優點：

| 層級 | 用途 | 儲存方式 |
|------|------|----------|
| Raw Resources | 原始訊息日誌 | PostgreSQL (append-only) |
| Items | 原子事實 | PostgreSQL + pgvector |
| Categories | 分類摘要 | PostgreSQL |
| Graph Edges | 知識圖譜關係 | PostgreSQL |
| Embeddings | 向量索引 | pgvector (HNSW) |

### 3.2 資料模型

```
┌─────────────┐       ┌─────────────┐
│  Resources  │       │ Categories  │
├─────────────┤       ├─────────────┤
│ id (UUID)   │       │ id (UUID)   │
│ created_at  │       │ name        │
│ source      │       │ summary     │
│ content     │       │ updated_at  │
│ metadata    │       └─────────────┘
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────┐
│    Items    │       │ Graph Edges │
├─────────────┤       ├─────────────┤
│ id (UUID)   │       │ id (UUID)   │
│ resource_id │       │ subject     │
│ subject     │       │ predicate   │
│ predicate   │       │ object      │
│ object      │       │ weight      │
│ category    │       │ created_at  │
│ confidence  │       └─────────────┘
│ status      │
│ supersedes  │
└──────┬──────┘
       │ 1:1
       ▼
┌─────────────┐
│ Embeddings  │
├─────────────┤
│ item_id     │
│ embedding   │
│ (VECTOR)    │
└─────────────┘
```

### 3.3 狀態機

Items 有三種狀態：

```
                    ┌─────────┐
                    │ active  │◄────────────┐
                    └────┬────┘             │
                         │                  │
            conflict     │                  │ reactivate
            detected     │                  │
                         ▼                  │
                    ┌─────────┐             │
                    │archived │─────────────┘
                    └────┬────┘
                         │
            manual       │
            delete       │
                         ▼
                    ┌─────────┐
                    │ deleted │
                    └─────────┘
```

## 4. 處理流程

### 4.1 Ingestion Pipeline

```
User Message
     │
     ▼
┌─────────────────┐
│ 1. Store Raw    │  → resources table (immutable)
│    Resource     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Extract      │  → LLM 抽取 subject-predicate-object
│    Facts        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Classify     │  → 分配到 6 個預設分類之一
│    Category     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Resolve      │  → 檢測並解決衝突
│    Conflicts    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Generate     │  → OpenAI embeddings
│    Embedding    │
└────────┬────────┘
         │
         ▼
     items table
```

### 4.2 Retrieval Pipeline

```
Query
  │
  ▼
┌─────────────────────────────────────────┐
│ Tier 1: Category Summaries              │  ← 快速上下文
│ (最新更新的分類摘要)                      │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│ Tier 2: Relevant Items                  │  ← 詳細事實
│ (按時間排序的 active items)              │
└────────────────────┬────────────────────┘
                     │
                     ▼ (optional)
┌─────────────────────────────────────────┐
│ Tier 3: Vector Similarity Search        │  ← 語義搜尋
│ (pgvector cosine similarity)            │
└─────────────────────────────────────────┘
```

## 5. 維護機制

### 5.1 Nightly Job (每日)

- **合併重複**：相同 subject-predicate-object 的 items
- **提升熱門**：近期活躍的 items 增加 confidence
- **更新摘要**：重新生成分類摘要

### 5.2 Weekly Job (每週)

- **時間衰減**：套用指數衰減公式降低 confidence
- **封存舊資料**：低 confidence + 超過 90 天 → archived
- **壓縮相似**：合併語義相近的 items
- **清理孤兒**：刪除無關聯的 resources

### 5.3 Monthly Job (每月)

- **重建 Embeddings**：重新計算所有 active items 的向量
- **重建 Graph**：根據 items 重新構建知識圖譜
- **優化索引**：VACUUM ANALYZE

### 5.4 時間衰減公式

```python
def time_decay_score(created_at, half_life_days=30):
    age_days = (now - created_at).days
    return 0.5 ** (age_days / half_life_days)
```

## 6. 技術棧

| 組件 | 技術選擇 | 理由 |
|------|----------|------|
| Language | Python 3.11+ | ML/NLP 生態系統完整 |
| API | FastAPI | 高效能 async |
| Database | PostgreSQL 16 | 成熟穩定 |
| Vector | pgvector | 與 PostgreSQL 整合良好 |
| ORM | SQLAlchemy 2.x | Async 支援完整 |
| Migrations | Alembic | 標準選擇 |
| Embeddings | OpenAI | text-embedding-3-small |
| Queue | Redis (optional) | 未來擴展用 |

## 7. API 設計

### 7.1 核心端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /ingest | 攝取原始訊息 |
| GET | /retrieve | Tiered 檢索 |
| GET | /items | 列出 items |
| GET | /categories | 列出分類 |
| GET | /context | Agent prompt 用的上下文 |

### 7.2 Intelligence 端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /extract | 抽取 facts |
| POST | /summarize | 建立摘要 |

### 7.3 Maintenance 端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /jobs/nightly | 每日維護 |
| POST | /jobs/weekly | 每週維護 |
| POST | /jobs/monthly | 每月維護 |

### 7.4 Observability 端點

| Method | Path | 功能 |
|--------|------|------|
| GET | /health | 基本健康檢查 |
| GET | /health/detailed | 詳細健康狀態 |
| GET | /metrics | 應用程式指標 |

## 8. 擴展考量

### 8.1 當前規模

- 目標：1K - 100K messages
- 單機部署足夠

### 8.2 未來擴展

- **超過 100K**：考慮分層摘要（hierarchical summaries）
- **多用戶**：加入 user_id 欄位隔離
- **高併發**：改用 Redis 佇列處理 extraction
- **分散式**：考慮 Qdrant 或 Pinecone 替代 pgvector

## 9. 安全考量

- 敏感資訊過濾（未實作，需根據需求添加）
- API key 環境變數管理
- 無用戶認證（適用於內部服務）

## 10. 參考資料

- Rohit's "How to Build an Agent That Never Forgets"
- LC-OS / Rishi Sood's Context Engineering Papers
- MemoraX Repository
