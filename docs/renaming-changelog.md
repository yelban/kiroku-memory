# Kiroku Memory 改名記錄

**日期**：2026-01-31

## 命名變更對照

| 項目 | 舊名稱 | 新名稱 |
|------|--------|--------|
| GitHub Repo | ai-agent-memory | kiroku-memory |
| 顯示名稱 | AI Agent Memory System | Kiroku Memory |
| Python 套件 | memory | kiroku_memory |
| Docker Volume | memory_data | kiroku_memory_data |
| Tagline | - | Tiered Retrieval Memory System for AI Agents |

## 修改的檔案

### 目錄結構

```
memory/ → kiroku_memory/
```

### pyproject.toml

```diff
- name = "ai-agent-memory"
+ name = "kiroku-memory"

- packages = ["memory"]
+ packages = ["kiroku_memory"]

- description = "AI Agent Memory System - Hybrid memory stack with vector search"
+ description = "Kiroku Memory - Tiered Retrieval Memory System for AI Agents"
```

### README 系列 (3 檔)

- `README.md`
- `README.zh-TW.md`
- `README.ja.md`

變更內容：
- H1 標題：`# Kiroku Memory`
- Tagline：`> Tiered Retrieval Memory System for AI Agents`
- Clone URL：`github.com/yelban/kiroku-memory.git`
- uvicorn 指令：`kiroku_memory.api:app`
- 架構圖標題
- 專案結構圖
- MCP 整合範例的 import

### CLAUDE.md

```diff
- # AI Agent Memory System
+ # Kiroku Memory
+ > Tiered Retrieval Memory System for AI Agents

- uv run uvicorn memory.api:app --reload
+ uv run uvicorn kiroku_memory.api:app --reload

- old-frand/
- ├── memory/
+ kiroku-memory/
+ ├── kiroku_memory/

- uv run mypy memory/
+ uv run mypy kiroku_memory/
```

### docker-compose.yml

```diff
  volumes:
-   - memory_data:/var/lib/postgresql/data
-   - ./memory/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
+   - kiroku_memory_data:/var/lib/postgresql/data
+   - ./kiroku_memory/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql

  volumes:
-   memory_data:
+   kiroku_memory_data:
```

### docs/ (3 檔)

#### docs/integration-guide.md

```diff
- # AI Agent Memory System 整合指南
+ # Kiroku Memory 整合指南

- from memory.db.database import get_session
+ from kiroku_memory.db.database import get_session

- cd /path/to/old-frand
+ cd /path/to/kiroku-memory

- 本專案使用 AI Agent Memory System 管理長期記憶
+ 本專案使用 Kiroku Memory 管理長期記憶
```

#### docs/user-guide.md

```diff
- # AI Agent Memory System 使用者手冊
+ # Kiroku Memory 使用者手冊

- cd /path/to/old-frand
+ cd /path/to/kiroku-memory

- uv run uvicorn memory.api:app --reload
+ uv run uvicorn kiroku_memory.api:app --reload

- 編輯 `memory/classify.py`
+ 編輯 `kiroku_memory/classify.py`
```

#### docs/architecture.md

```diff
- # AI Agent Memory System 架構設計
+ # Kiroku Memory 架構設計

- │                     AI Agent Memory System                       │
+ │                        Kiroku Memory                             │
```

### tests/test_models.py

```diff
- from memory.db.models import Resource, Item, Category, GraphEdge
+ from kiroku_memory.db.models import Resource, Item, Category, GraphEdge
```

### kiroku_memory/api.py

```diff
  app = FastAPI(
-     title="AI Agent Memory API",
-     description="Tiered retrieval with vector search and knowledge graph",
+     title="Kiroku Memory API",
+     description="Tiered Retrieval Memory System for AI Agents",
      version="0.1.0",
  )
```

### SESSION_STATE.md

```diff
- # Session State - AI Agent Memory System
+ # Session State - Kiroku Memory

- old-frand/
- ├── memory/
+ kiroku-memory/
+ ├── kiroku_memory/

所有 Task 路徑引用從 memory/ 改為 kiroku_memory/
```

## 驗證結果

```bash
# 重新安裝依賴
uv sync
# ✓ kiroku-memory==0.1.0 installed

# 執行測試
uv run python -m pytest tests/test_models.py -v
# ✓ 4 passed

# 驗證 API 模組
uv run python -c "from kiroku_memory.api import app; print(app.title)"
# ✓ Kiroku Memory API
```

## 注意事項

### 內部 imports

Python 模組內部使用**相對 import**，無需修改：

```python
# kiroku_memory/api.py
from .db.database import get_session
from .db.models import Resource, Item, Category
```

### 資料庫

- 資料庫名稱仍為 `memory`（未修改）
- 如需修改，編輯 `docker-compose.yml` 的 `POSTGRES_DB`

### 舊版本相容

如果有其他專案依賴 `from memory.xxx import`，需要更新為 `from kiroku_memory.xxx import`。
