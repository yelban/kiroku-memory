# Kiroku Memory

> AI Agent 分層檢索記憶系統

**唯一具備原生桌面 App、100% 本地儲存、自動衝突解決的 AI 記憶系統。**

<p align="center">
  <img src="cover.png" alt="Kiroku Memory" width="600">
</p>

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-2.x-purple.svg)](https://surrealdb.com/)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue.svg)](https://polyformproject.org/licenses/noncommercial/1.0.0/)

**語言**: [English](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

---

## 🚀 三步驟快速開始

> **不需要 Docker、不需要 Python、不需要設定。** 下載即用！

```
1️⃣  下載 → 從 GitHub Releases 下載 Kiroku Memory.app
2️⃣  安裝 → npx skills add yelban/kiroku-memory
3️⃣  重啟 → 重啟 Claude Code，開始享受持久記憶！
```

**[⬇️ 下載桌面應用程式](https://github.com/yelban/kiroku-memory/releases)**

---

## 🎯 為什麼選擇 Kiroku？

| | **Kiroku** | **mem0** | **claude-mem** |
|---|:---:|:---:|:---:|
| 🖥️ 桌面 GUI | ✅ 原生 App | ❌ 雲端 | ❌ 僅 Web |
| 🔒 100% 本地 | ✅ | ❌ 雲端優先 | ✅ |
| 🔄 衝突解決 | ✅ | ❌ | ❌ |
| ⏰ 時間衰減 | ✅ | ❌ | ❌ |

**核心差異：**
- **原生桌面 App** — 視覺化記憶瀏覽器，不只是 CLI
- **完全本地** — 資料永遠不離開你的電腦
- **智慧記憶** — 自動偵測矛盾，信心度隨時間衰減

---

一個可用於生產環境的 AI Agent 記憶系統，實現持久化、可演進的記憶與分層檢索功能。基於 Rohit 的「How to Build an Agent That Never Forgets」文章及社群回饋所設計。

## 為什麼需要這個專案？

傳統 RAG（Retrieval-Augmented Generation）在大規模應用時面臨根本性挑戰：

- **語義相似 ≠ 事實正確**：Embeddings 捕捉的是相似度，而非正確性
- **缺乏時間脈絡**：無法處理「用戶以前喜歡 A，現在喜歡 B」的情境
- **記憶矛盾**：隨時間累積的資訊可能相互衝突
- **擴展性問題**：當記憶達到數萬條時，檢索效能急劇下降

本系統透過 **Hybrid Memory Stack（混合記憶堆疊）** 架構解決這些挑戰。

## 為什麼記憶重要：專家觀點

AI Agent 與認知科學領域的頂尖研究者，一致強調持久記憶的關鍵價值：

### Lilian Weng（OpenAI 研究科學家）

在她的經典文章 *"LLM Powered Autonomous Agents"* 中指出，記憶是 Agent 的核心組件：

> 記憶讓 Agent 超越無狀態互動，能夠跨 session 累積知識。

Kiroku 透過 **Tiered Retrieval（分層檢索）** 實現這一點 — 先摘要、再鑽取 — 避免傳統 RAG 的語義偏差問題。

### Harrison Chase（LangChain 創辦人）

他提出 Agent 記憶的三個層次：**Episodic**（事件）、**Semantic**（事實）、**Procedural**（技能）。

| LangChain 概念 | Kiroku 實作 |
|----------------|-------------|
| Episodic | `events` 分類 |
| Semantic | `facts`、`preferences` 分類 |
| Procedural | `skills` 分類 |

額外價值：**Conflict Resolution** 自動偵測矛盾事實，**跨專案共享** 透過 `global:user` scope 實現。

### Daniel Kahneman（諾貝爾獎得主，認知心理學家）

《快思慢想》區分系統一（直覺）與系統二（分析）。

**Kiroku 實作：**

| 模式 | 功能 | 效益 |
|------|-------------|------|
| 系統一 | 自動載入上下文 | Claude 開機就「認識你」 |
| 系統二 | `/remember` 指令 | 明確標記重要資訊 |

**實際效果**：不用每次都說「我偏好用 uv 管理 Python」。

### 核心價值

這些專家的觀點匯聚成一個洞見：**記憶讓 AI 從「工具」進化為「夥伴」**。

- **連續性** — 對話不再是孤島
- **個人化** — AI 真正「認識」你
- **效率** — 省去重複解釋的認知負擔
- **演化** — 記憶累積，AI 越用越懂你

## ✨ 功能特點

- **只增不改的原始日誌**：不可變的來源追蹤
- **原子事實抽取**：LLM 驅動的結構化事實抽取（主詞-謂詞-受詞）
- **分類式組織**：6 個預設分類，帶有可演進的摘要
- **分層檢索**：摘要優先，按需深入到事實
- **衝突解決**：自動偵測並封存矛盾的事實
- **時間衰減**：記憶信心度隨時間指數衰減
- **向量搜尋**：pgvector 驅動的語義相似度搜尋
- **知識圖譜**：實體間的關係映射
- **排程維護**：每日、每週、每月維護任務
- **生產就緒**：結構化日誌、指標監控、健康檢查

## 架構

```mermaid
flowchart TB
    subgraph KM["Kiroku Memory"]
        direction TB

        Ingest["攝取<br/>(原始 Log)"] --> Resources[("資源<br/>(不可變)")]

        Resources --> Extract["抽取<br/>(事實)"]
        Extract --> Classify["分類<br/>(Category)"]
        Classify --> Conflict["衝突<br/>解決"]
        Conflict --> Items[("項目<br/>(活躍)")]

        Items --> Embeddings["嵌入向量<br/>(pgvector)"]
        Items --> Summary["摘要<br/>建構"]

        Embeddings --> Retrieve["檢索<br/>(分層+優先級)"]
        Summary --> Retrieve
    end
```

## 桌面應用程式

最簡單的 Kiroku Memory 使用方式 — 不需要 Docker，不需要 Python 環境。

### 下載

從 [GitHub Releases](https://github.com/yelban/kiroku-memory/releases) 下載適合你平台的版本：

| 平台 | 架構 | 格式 |
|------|------|------|
| macOS | Apple Silicon (M1/M2/M3) | `.dmg` |
| macOS | Intel | `.dmg` |
| Windows | x86_64 | `.msi` |
| Linux | x86_64 | `.AppImage` |

### 使用方式

1. **安裝**：雙擊下載的檔案進行安裝
2. **執行**：從應用程式中啟動「Kiroku Memory」
3. **設定**（選用）：點擊設定圖示新增 OpenAI API Key 以啟用語義搜尋

桌面應用程式使用內嵌的 SurrealDB — 所有資料都儲存在本機，不需要任何外部相依。

### 特色

- **零設定**：開箱即用，不需要 Docker 或資料庫設定
- **內嵌資料庫**：SurrealDB 將資料儲存在應用程式資料目錄
- **跨平台**：macOS、Windows、Linux 原生應用程式
- **相同 API**：完整 REST API 可在 `http://127.0.0.1:8000` 使用

---

## 快速開始（開發者）

適合想從原始碼執行或自訂系統的開發者。

### 環境需求

- Python 3.11+
- Docker（用於 PostgreSQL + pgvector）**或** SurrealDB（嵌入式，不需 Docker）
- OpenAI API Key

> **初次安裝？** 請參閱[詳細安裝指南](docs/installation-guide.zh-TW.md)，有完整的步驟說明。

### 安裝

```bash
# 複製儲存庫
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory

# 使用 uv 安裝依賴
uv sync

# 複製環境變數檔案
cp .env.example .env

# 編輯 .env 並設定 OPENAI_API_KEY
```

### 啟動服務

#### 方式 A：PostgreSQL（生產環境）

```bash
# 啟動 PostgreSQL + pgvector
docker compose up -d

# 啟動 API 伺服器
uv run uvicorn kiroku_memory.api:app --reload

# API 將運行在 http://localhost:8000
```

#### 方式 B：SurrealDB（桌面/嵌入式，不需 Docker！）

```bash
# 在 .env 中設定後端
echo "BACKEND=surrealdb" >> .env

# 啟動 API 伺服器（不需 Docker！）
uv run uvicorn kiroku_memory.api:app --reload

# 資料儲存於 ./data/kiroku/
```

### 驗證安裝

```bash
# 健康檢查
curl http://localhost:8000/health
# 預期回應: {"status":"ok","version":"0.1.0"}

# 詳細健康狀態
curl http://localhost:8000/health/detailed
```

## 使用方式

### 基本工作流程

#### 1. 攝取訊息

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "我叫小明，在 Google 當軟體工程師。我偏好使用 Neovim。",
    "source": "user:xiaoming",
    "metadata": {"channel": "chat"}
  }'
```

#### 2. 抽取事實

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "你的_RESOURCE_ID"}'
```

這會抽取出結構化事實，例如：
- `小明` `工作於` `Google`（分類：facts）
- `小明` `是` `軟體工程師`（分類：facts）
- `小明` `偏好` `Neovim`（分類：preferences）

#### 3. 生成摘要

```bash
curl -X POST http://localhost:8000/summarize
```

#### 4. 檢索記憶

```bash
# 分層檢索（摘要 + 項目）
curl "http://localhost:8000/retrieve?query=小明做什麼工作"

# 取得 Agent prompt 用的上下文
curl "http://localhost:8000/context"
```

### API 端點

#### 核心端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/ingest` | 攝取原始訊息 |
| GET | `/resources` | 列出原始資源 |
| GET | `/resources/{id}` | 取得特定資源 |
| GET | `/retrieve` | 分層記憶檢索 |
| GET | `/items` | 列出抽取的項目 |
| GET | `/categories` | 列出分類及摘要 |

#### 智慧端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/extract` | 從資源抽取事實 |
| POST | `/process` | 批次處理待處理資源 |
| POST | `/summarize` | 建立分類摘要 |
| GET | `/context` | 取得 Agent prompt 用的記憶上下文 |

#### 維護端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/jobs/nightly` | 執行每日整合 |
| POST | `/jobs/weekly` | 執行每週維護 |
| POST | `/jobs/monthly` | 執行每月重建索引 |

#### 可觀測性端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 基本健康檢查 |
| GET | `/health/detailed` | 詳細健康狀態 |
| GET | `/metrics` | 應用程式指標 |
| POST | `/metrics/reset` | 重設指標 |

### 排程任務 (macOS)

安裝 launchd 自動維護任務：

```bash
bash launchd/install.sh
```

| 任務 | 排程 | 說明 |
|------|------|------|
| nightly | 每日 03:00 | 衰減計算、清理、摘要更新 |
| weekly | 週日 04:00 | 封存、壓縮 |
| monthly | 每月1日 05:00 | embeddings 重建、graph 重建 |

驗證安裝：

```bash
launchctl list | grep kiroku
```

## 整合

### 與 Claude Code 整合（推薦）

#### 方式一：npx Skills CLI（最簡單）

```bash
npx skills add yelban/kiroku-memory
```

#### 方式二：Plugin Marketplace

```bash
# 步驟 1：新增市集
/plugin marketplace add https://github.com/yelban/kiroku-memory.git

# 步驟 2：安裝外掛
/plugin install kiroku-memory
```

#### 方式三：手動安裝

```bash
# 一鍵安裝
curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash

# 或 clone 後安裝
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory/skill/assets && ./install.sh
```

安裝後重啟 Claude Code，即可使用：

```bash
/remember 用戶偏好深色模式          # 儲存記憶
/recall 編輯器偏好                  # 搜尋記憶
/memory-status                      # 檢查狀態
```

**功能特色：**
- **自動載入**：SessionStart hook 自動注入記憶上下文
- **智慧儲存**：Stop hook 自動儲存重要事實
- **優先級排序**：preferences > facts > goals（混合靜態+動態權重）
- **智慧截斷**：永不在分類中間截斷，保持完整性
- **跨專案**：全域記憶 + 專案記憶範圍

#### 驗證 Hooks 運作狀態

當 Hooks 正常運作時，對話開始會出現：

```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context

### Preferences
...
</kiroku-memory>
```

這表示：
- ✅ SessionStart hook 成功執行
- ✅ API 服務已連接
- ✅ 記憶上下文已注入

若記憶內容為空（只有分類標題），代表尚未儲存任何記憶，可用 `/remember` 手動儲存。

#### 自動儲存：雙階段記憶捕捉

Stop Hook 採用**快思慢想**雙階段架構：

**Phase 1: Fast Path (<1s, 同步)**

Regex 模式匹配，立即捕捉：

| 模式類型 | 範例 | 最小加權長度 |
|---------|------|-------------|
| 偏好 | `我喜歡...`、`偏好...` | 10 |
| 決定 | `決定使用...`、`選擇...` | 10 |
| 發現 | `發現...`、`解決方案是...` | 10 |
| 學習 | `學到...`、`原因是...`、`問題在於...` | 10 |
| 事實 | `工作於...`、`住在...` | 10 |
| 無模式 | 一般內容 | 35 |

同時從 Claude 回應中擷取**結論標記**：
- `解決方案`、`發現`、`結論`、`建議`、`根因`

> **加權長度計算**：CJK 字元 × 2.5 + 其他字元 × 1

**Phase 2: Slow Path (5-15s, 非同步)**

背景 LLM 分析，使用 Claude CLI：
- 在脫離的 subprocess 中執行（不阻塞 Claude Code）
- 分析最近 6 則 user + 4 則 assistant 訊息
- 擷取最多 5 條記憶，含類型/信心度
- 記憶類型：`discovery`、`decision`、`learning`、`preference`、`fact`

**會過濾掉的雜訊：**
- 短回覆：`好的`、`OK`、`謝謝`
- 問句：`什麼是...`、`怎麼做...`
- 錯誤訊息：`錯誤`、`失敗`

#### 增量擷取 (PostToolUse Hook)

長對話中，記憶會在對話期間增量擷取：

- **觸發時機**：每次工具調用後，搭配節流機制
- **節流條件**：間隔 ≥5 分鐘 且 ≥10 條新訊息
- **Offset 追蹤**：只分析上次擷取後的新訊息
- **智慧跳過**：內容太短時自動跳過

這樣可以分散擷取負載，確保早期對話內容不會遺漏。

詳見 [Claude Code 整合指南](docs/claude-code-integration.md)。

### 與 MCP Server 整合（進階）

建立自訂 MCP 伺服器：

```python
# memory_mcp.py
from mcp.server import Server
from kiroku_memory.db.database import get_session
from kiroku_memory.summarize import get_tiered_context

app = Server("memory-system")

@app.tool("memory_context")
async def memory_context():
    async with get_session() as session:
        return await get_tiered_context(session)
```

在 `~/.claude/mcp.json` 中設定：

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["run", "python", "memory_mcp.py"]
    }
  }
}
```

### 與聊天機器人整合（Telegram/LINE）

```javascript
const MEMORY_API = "http://localhost:8000";

// 回覆前取得記憶上下文
async function getMemoryContext(userId) {
  const response = await fetch(`${MEMORY_API}/context`);
  const data = await response.json();
  return data.context;
}

// 對話後儲存重要資訊
async function saveToMemory(userId, content) {
  await fetch(`${MEMORY_API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      source: `bot:${userId}`
    })
  });
}

// 在機器人中使用
const memoryContext = await getMemoryContext(userId);
const enhancedPrompt = `${memoryContext}\n\n${SYSTEM_PROMPT}`;
```

詳細範例請參閱 [整合指南](docs/integration-guide.md)。

## 維護

### 排程任務

設定 cron 任務進行自動維護：

```bash
# 每日：合併重複、提升熱門記憶
0 2 * * * curl -X POST http://localhost:8000/jobs/nightly

# 每週：套用時間衰減、封存舊項目
0 3 * * 0 curl -X POST http://localhost:8000/jobs/weekly

# 每月：重建嵌入向量和知識圖譜
0 4 1 * * curl -X POST http://localhost:8000/jobs/monthly
```

### 時間衰減

記憶會以可設定的半衰期（預設：30 天）指數衰減：

```python
def time_decay_score(created_at, half_life_days=30):
    age_days = (now - created_at).days
    return 0.5 ** (age_days / half_life_days)
```

## 設定

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `BACKEND` | `postgres` | 後端選擇：`postgres` 或 `surrealdb` |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 連線字串 |
| `SURREAL_URL` | `file://./data/kiroku` | SurrealDB URL（file:// 為嵌入式） |
| `SURREAL_NAMESPACE` | `kiroku` | SurrealDB 命名空間 |
| `SURREAL_DATABASE` | `memory` | SurrealDB 資料庫名稱 |
| `OPENAI_API_KEY` | （必填） | OpenAI API 金鑰 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI 嵌入模型 |
| `EMBEDDING_DIMENSIONS` | `1536` | 向量維度 |
| `DEBUG` | `false` | 啟用除錯模式 |

## 專案結構

```
.
├── kiroku_memory/
│   ├── api.py              # FastAPI 端點
│   ├── ingest.py           # 資源攝取
│   ├── extract.py          # 事實抽取（LLM）
│   ├── classify.py         # 分類器
│   ├── conflict.py         # 衝突解決
│   ├── summarize.py        # 摘要生成
│   ├── embedding.py        # 向量搜尋
│   ├── observability.py    # 指標與日誌
│   ├── db/
│   │   ├── models.py       # SQLAlchemy 模型
│   │   ├── schema.sql      # PostgreSQL 結構
│   │   ├── database.py     # 連線管理
│   │   └── config.py       # 設定
│   └── jobs/
│       ├── nightly.py      # 每日維護
│       ├── weekly.py       # 每週維護
│       └── monthly.py      # 每月維護
├── tests/
│   ├── test_models.py
│   └── load/
│       └── test_retrieval.py
├── docs/
│   ├── architecture.md
│   ├── development-journey.md
│   ├── user-guide.md
│   └── integration-guide.md
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## 文件

- [安裝指南](docs/installation-guide.zh-TW.md) - 適合初學者的詳細安裝步驟
- [架構設計](docs/architecture.md) - 系統架構與設計決策
- [開發歷程](docs/development-journey.md) - 從點子到實作
- [使用者手冊](docs/user-guide.md) - 完整使用指南
- [整合指南](docs/integration-guide.md) - 與 Claude Code、Codex、聊天機器人整合

## 技術棧

- **語言**：Python 3.11+
- **框架**：FastAPI + asyncio
- **資料庫**：PostgreSQL 16 + pgvector **或** SurrealDB（嵌入式）
- **ORM**：SQLAlchemy 2.x / SurrealDB Python SDK
- **嵌入向量**：OpenAI text-embedding-3-small
- **套件管理**：uv

## 貢獻

歡迎貢獻！請在提交 pull request 前閱讀我們的貢獻指南。

## 授權

本專案採用 [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) 授權。

**免費使用**：個人用途、學術研究、非營利組織、評估測試。

**商業使用**：請聯繫 yelban@gmail.com 取得授權。

## 致謝

- Rohit (@rohit4verse) 的原創文章「How to Build an Agent That Never Forgets」
- MemoraX 團隊的開源實作參考
- Rishi Sood 的 LC-OS Context Engineering 論文
- 社群的寶貴回饋與建議

## 相關專案

- [MemoraX](https://github.com/MemoraXLabs/MemoraX) - Agent 記憶的另一種實作
- [mem0](https://github.com/mem0ai/mem0) - AI 應用的記憶層
