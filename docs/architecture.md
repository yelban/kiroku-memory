# Kiroku Memory 架構設計

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
│                        Kiroku Memory                             │
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

┌─────────────────┐
│CategoryAccesses │  ← 新增：追蹤分類使用頻率
├─────────────────┤
│ id (UUID)       │
│ category        │
│ accessed_at     │
│ source          │
└─────────────────┘
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
│ (按優先級排序的分類摘要)                  │
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

### 4.3 優先級排序與智慧截斷

#### 混合優先級模型

分類不再按字母排序，而是使用混合優先級模型：

```
priority = static_weight × dynamic_factor

dynamic_factor = 1.0 + usage_weight × usage_score + recency_weight × recency_score
```

**靜態權重（預設）**：

| 分類 | 權重 | 說明 |
|------|------|------|
| preferences | 1.0 | 最常用於個人化 |
| facts | 0.9 | 核心使用者資訊 |
| goals | 0.7 | 使用者目標 |
| skills | 0.6 | 使用者能力 |
| relationships | 0.5 | 社交脈絡 |
| events | 0.4 | 較少用於 context |

**動態因子參數**：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| usage_window_days | 30 | 計算使用頻率的時間窗口 |
| usage_norm | 10 | 歸一化使用次數 |
| usage_weight | 0.3 | 使用頻率權重 |
| recency_half_life_days | 14 | 新鮮度半衰期 |
| recency_weight | 0.2 | 新鮮度權重 |

#### 智慧截斷

當 context 超過字元上限（預設 2000）時：

```
┌─────────────────────────────────────────┐
│ 1. 按優先級排序所有分類                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│ 2. 逐一加入完整分類區塊                   │
│    (永不在分類中間截斷)                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│ 3. 超過上限時停止                         │
│    (低優先級分類被捨棄)                   │
└─────────────────────────────────────────┘
```

**雙層保護**：
- **API 層**：`/context?max_chars=2000` 參數控制
- **Hook 層**：`session-start-hook.py` 按 `### ` 標題分割

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

## 6. Repository Pattern 架構

### 6.1 設計理念

採用 Repository Pattern + Unit of Work 實現資料庫後端無關性：

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (api.py, jobs/nightly.py, jobs/weekly.py, jobs/monthly.py) │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Entities                         │
│  (ResourceEntity, ItemEntity, CategoryEntity, ...)          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository Interfaces                      │
│  (ResourceRepository, ItemRepository, CategoryRepository)    │
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│     PostgreSQL          │   │      SurrealDB          │
│   Implementation        │   │    Implementation       │
│  (SQLAlchemy 2.x)       │   │   (surrealdb.py)        │
└─────────────────────────┘   └─────────────────────────┘
```

### 6.2 Repository 介面

#### ItemRepository

| 方法 | 說明 |
|------|------|
| `get(id)` | 取得單一 item |
| `create(entity)` | 建立 item |
| `create_many(entities)` | 批次建立 items |
| `update(entity)` | 更新 item |
| `update_status(id, status)` | 更新狀態 |
| `list(category, status, limit)` | 列出 items |
| `count(category, status)` | 計數 |
| `find_potential_conflicts(subject, predicate, exclude_id)` | 尋找潛在衝突 |
| `list_duplicates()` | 列出重複項 |
| `count_by_subject_recent(subject, days)` | 計算近期主詞出現次數 |
| `list_distinct_categories(status)` | 列出不同分類 |
| `list_old_low_confidence(max_age_days, min_confidence)` | 列出舊的低信心項 |
| `get_stats_by_status()` | 按狀態統計 |
| `get_avg_confidence(status)` | 平均信心度 |
| `list_all_ids(status)` | 列出所有 ID |
| `list_archived(limit)` | 列出已封存項 |
| `get_superseding_item(archived_id)` | 取得取代項 |

#### ResourceRepository

| 方法 | 說明 |
|------|------|
| `get(id)` | 取得單一 resource |
| `create(entity)` | 建立 resource |
| `list(source, since, limit)` | 列出 resources |
| `count()` | 計數 |
| `delete_orphaned(max_age_days)` | 刪除孤立資源 |
| `list_unextracted(limit)` | 列出未萃取資源 |

#### CategoryRepository

| 方法 | 說明 |
|------|------|
| `get(id)` | 取得單一 category |
| `get_by_name(name)` | 依名稱取得 |
| `create(entity)` | 建立 category |
| `upsert(entity)` | 建立或更新 |
| `list()` | 列出所有 categories |
| `count_items_per_category(status)` | 統計各分類項目數 |

#### GraphRepository

| 方法 | 說明 |
|------|------|
| `create(entity)` | 建立邊 |
| `create_many(entities)` | 批次建立 |
| `get_by_subject(subject)` | 依主詞取得 |
| `get_neighbors(subject, depth)` | 取得鄰居節點 |
| `delete_by_subject(subject)` | 依主詞刪除 |
| `list_all()` | 列出所有邊 |
| `delete_all()` | 刪除所有邊 |
| `count()` | 計數 |
| `update_weight(subject, predicate, object, weight)` | 更新權重 |

#### EmbeddingRepository

| 方法 | 說明 |
|------|------|
| `get(item_id)` | 取得 embedding |
| `upsert(entity)` | 建立或更新 |
| `search(embedding, limit, threshold)` | 向量搜尋 |
| `delete(item_id)` | 刪除 |
| `count()` | 計數 |
| `delete_stale(active_item_ids)` | 刪除過時 embeddings |

### 6.3 Unit of Work

```python
class UnitOfWork(ABC):
    resources: ResourceRepository
    items: ItemRepository
    categories: CategoryRepository
    graph: GraphRepository
    embeddings: EmbeddingRepository
    category_accesses: CategoryAccessRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

**使用範例**：

```python
async with get_unit_of_work() as uow:
    # 建立 resource
    resource_id = await uow.resources.create(entity)

    # 建立 items
    item_ids = await uow.items.create_many(items)

    # 提交事務
    await uow.commit()
```

### 6.4 後端選擇

透過 `BACKEND` 環境變數選擇：

```python
# kiroku_memory/db/repositories/factory.py
def get_unit_of_work() -> UnitOfWork:
    if settings.backend == "surrealdb":
        return SurrealUnitOfWork()
    else:
        return PostgresUnitOfWork()
```

## 7. 技術棧

| 組件 | 技術選擇 | 理由 |
|------|----------|------|
| Language | Python 3.11+ | ML/NLP 生態系統完整 |
| API | FastAPI | 高效能 async |
| Database | PostgreSQL 16 / SurrealDB | 雙後端支援 |
| Vector | pgvector / SurrealDB builtin | 與主資料庫整合 |
| ORM | SQLAlchemy 2.x | PostgreSQL 後端 |
| Pattern | Repository + UnitOfWork | 後端無關抽象 |
| Embeddings | OpenAI | text-embedding-3-small |
| Desktop | Tauri v2 + React | 跨平台桌面應用 |

## 8. API 設計

### 8.1 核心端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /ingest | 攝取原始訊息 |
| GET | /retrieve | Tiered 檢索 |
| GET | /items | 列出 items |
| GET | /categories | 列出分類 |
| GET | /context | Agent prompt 用的上下文（支援優先級排序、智慧截斷） |

#### `/context` 端點參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| categories | null | 逗號分隔的分類列表（可選） |
| max_chars | null | 最大字元數（按完整分類截斷） |
| max_items_per_category | 10 | 每分類最多項目數 |

### 8.2 Intelligence 端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /extract | 抽取 facts |
| POST | /summarize | 建立摘要 |

### 8.3 Maintenance 端點

| Method | Path | 功能 |
|--------|------|------|
| POST | /jobs/nightly | 每日維護 |
| POST | /jobs/weekly | 每週維護 |
| POST | /jobs/monthly | 每月維護 |

### 8.4 Observability 端點

| Method | Path | 功能 |
|--------|------|------|
| GET | /health | 基本健康檢查 |
| GET | /health/detailed | 詳細健康狀態 |
| GET | /metrics | 應用程式指標 |

## 9. 擴展考量

### 9.1 當前規模

- 目標：1K - 100K messages
- 單機部署足夠

### 9.2 未來擴展

- **超過 100K**：考慮分層摘要（hierarchical summaries）
- **多用戶**：加入 user_id 欄位隔離
- **高併發**：改用 Redis 佇列處理 extraction
- **分散式**：考慮 Qdrant 或 Pinecone 替代 pgvector

## 10. 安全考量

- 敏感資訊過濾（未實作，需根據需求添加）
- API key 環境變數管理
- 無用戶認證（適用於內部服務）

## 11. 參考資料

- Rohit's "How to Build an Agent That Never Forgets"
- LC-OS / Rishi Sood's Context Engineering Papers
- MemoraX Repository
