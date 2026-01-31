# Kiroku Memory

> AI Agent 分層檢索記憶系統

AI Agent 長期記憶系統，支援跨 session、跨專案的記憶管理。

## 命令

| 命令 | 說明 |
|------|------|
| `/remember <內容>` | 儲存記憶 |
| `/recall <查詢>` | 搜尋記憶 |
| `/forget <查詢>` | 刪除/封存記憶 |
| `/memory-status` | 檢視記憶狀態 |

## 使用範例

```bash
# 儲存記憶
/remember 用戶偏好深色模式

# 儲存到特定分類
/remember --category preferences 喜歡用 Neovim

# 存為全域記憶
/remember --global 暱稱叫吹吹

# 搜尋記憶
/recall 編輯器偏好

# 取得完整上下文
/recall --context

# 檢視狀態
/memory-status
```

## 記憶範圍

- **全域記憶** (`global:user`)：跨專案共享，如個人偏好
- **專案記憶** (`project:<name>`)：專案特定，如架構決策

預設行為：
- 在專案目錄 → 存到專案記憶
- 無專案上下文 → 存到全域記憶

## 分類

| 分類 | 說明 |
|------|------|
| `preferences` | 偏好設定 |
| `facts` | 事實資訊 |
| `events` | 事件活動 |
| `relationships` | 人際關係 |
| `skills` | 技能專長 |
| `goals` | 目標計畫 |

## 前置需求

Kiroku Memory 服務需執行中：

```bash
cd /path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
```

預設 API 位址：`http://localhost:8000`（可透過 `KIROKU_API` 環境變數覆蓋）

## 安裝

### 方式一：Plugin Marketplace（推薦）

```bash
# 1. 新增市集
/plugin marketplace add https://github.com/yelban/kiroku-memory.git

# 2. 安裝外掛
/plugin install kiroku-memory
```

### 方式二：npx Skills CLI

```bash
npx skills add yelban/kiroku-memory
# 或
npx add-skill yelban/kiroku-memory
# 或
npx openskills install yelban/kiroku-memory
```

### 方式三：安裝腳本

```bash
curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash
```

## 功能特色

- **自動載入**：SessionStart hook 自動注入記憶上下文
- **智慧儲存**：Stop hook 智慧儲存重要事實
- **去重複**：24 小時 TTL 防止重複儲存
- **模式匹配**：只儲存偏好、決定、事實（忽略噪音）

## 了解更多

- [架構設計](docs/architecture.md)
- [整合指南](docs/claude-code-integration.md)
- [API 參考](docs/integration-guide.md)

## 翻譯

- [English](SKILL.md)
- [日本語](SKILL.ja.md)
