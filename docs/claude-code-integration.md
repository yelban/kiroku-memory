# Claude Code 整合指南

本文件說明如何將 Kiroku Memory 與 Claude Code 整合，實現跨 session、跨專案的 AI 記憶能力。

## 概述

整合後的功能：

| 功能 | 說明 |
|------|------|
| **自動載入** | 對話開始時自動注入記憶上下文 |
| **智慧儲存** | 對話結束時自動儲存重要資訊 |
| **手動命令** | `/remember`, `/recall`, `/forget`, `/memory-status` |
| **雙層記憶** | 全域記憶 + 專案記憶 |

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
# Vercel Skills CLI
npx skills add yelban/kiroku-memory

# 或 add-skill CLI
npx add-skill yelban/kiroku-memory

# 或 OpenSkills
npx openskills install yelban/kiroku-memory
```

### 方式三：手動安裝腳本

```bash
# 一鍵安裝
curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash

# 或 clone 後安裝
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory/skill/assets && ./install.sh
```

### 啟動 Kiroku Memory 服務

安裝後需啟動後端服務：

```bash
cd ~/path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
```

### 安裝後檔案結構

#### Plugin 結構（專案內）

```
kiroku-memory/
├── .claude-plugin/
│   └── marketplace.json  # 個人市集定義
├── hooks/
│   ├── hooks.json        # Hook 定義
│   ├── session-start-hook.py
│   └── stop-hook.py
├── commands/
│   ├── remember.md
│   ├── recall.md
│   ├── forget.md
│   └── memory-status.md
├── scripts/
│   ├── remember.py
│   ├── recall.py
│   ├── forget.py
│   └── memory-status.py
└── skill/                # Claude Code Skill
    ├── SKILL.md          # 英文（主要）
    ├── SKILL.zh-TW.md    # 繁體中文
    ├── SKILL.ja.md       # 日本語
    ├── scripts/
    ├── references/
    └── assets/install.sh
```

#### 安裝後位置

```
~/.claude/skills/kiroku-memory/
├── SKILL.md              # 英文（主要）
├── SKILL.zh-TW.md        # 繁體中文
├── SKILL.ja.md           # 日本語
├── scripts/
│   ├── remember.py
│   ├── recall.py
│   ├── forget.py
│   ├── memory-status.py
│   ├── session-start-hook.py
│   └── stop-hook.py
├── references/
└── assets/
```

### Hook 設定

安裝腳本會自動加入 `~/.claude/settings.json`：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/kiroku-memory/scripts/session-start-hook.py",
            "timeout": 5,
            "statusMessage": "Loading Kiroku Memory..."
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/kiroku-memory/scripts/stop-hook.py",
            "timeout": 10,
            "async": true
          }
        ]
      }
    ]
  }
}
```

## 使用方式

### 自動功能（Hooks）

#### SessionStart Hook

- **觸發時機**：每次開啟新對話
- **功能**：從 Kiroku Memory API 取得記憶上下文，注入到對話中
- **輸出格式**：

```xml
<kiroku-memory>
## User Memory Context

### Preferences
用戶偏好深色模式，喜歡使用 Neovim...

### Facts
用戶在 Google 工作，是軟體工程師...
</kiroku-memory>
```

#### Stop Hook

- **觸發時機**：每次 Claude 完成回應
- **功能**：分析對話內容，儲存重要資訊
- **智慧過濾**：
  - ✓ 儲存：偏好、決定、事實
  - ✗ 忽略：問候、確認、問題

### 手動命令

#### /remember

儲存記憶到系統。

```bash
# 基本用法
/remember 用戶喜歡深色模式

# 指定分類
/remember --category preferences 喜歡用 Neovim

# 存為全域記憶
/remember --global 暱稱叫吹吹
```

#### /recall

搜尋記憶。

```bash
# 搜尋
/recall 編輯器偏好

# 取得完整 context
/recall --context

# 限制分類
/recall --category preferences
```

#### /forget

刪除或封存記憶。

```bash
/forget 舊的偏好
```

#### /memory-status

檢視記憶系統狀態。

```bash
/memory-status
```

輸出範例：
```
=== Kiroku Memory 狀態 ===

服務狀態: ✓ ok (v0.1.0)
API 位址: http://localhost:8000

--- 記憶統計 ---
  原始資源: 122
  活躍項目: 1513
  嵌入向量: 13

--- 分類 ---
  ✓ preferences
  ✓ facts
  ✓ events
  ...
```

## 記憶範圍

### 全域記憶 (`global:user`)

- 跨專案共享
- 個人偏好、通用知識
- 使用 `--global` 旗標

### 專案記憶 (`project:<name>`)

- 專案特定
- 架構決策、技術選型
- 自動偵測專案名稱

### 自動偵測邏輯

1. Git 專案：使用 git 根目錄名稱
2. 一般目錄：使用當前目錄名稱
3. 家目錄：使用 `global:user`

## 智慧過濾規則

### 會儲存的內容

| 類型 | 模式範例 |
|------|----------|
| 偏好 | `我喜歡...`, `偏好...` |
| 決定 | `決定使用...`, `選擇...` |
| 事實 | `工作於...`, `住在...` |
| 專案 | `專案使用...`, `架構決定...` |

### 不會儲存的內容

| 類型 | 範例 |
|------|------|
| 確認 | `ok`, `好的`, `沒問題` |
| 感謝 | `謝謝`, `thanks` |
| 問題 | `什麼是...`, `怎麼...` |

### 其他條件

- 最小長度：50 字元
- 去重複：24 小時內不重複儲存
- 數量限制：每次對話最多 3 筆

## 運作狀態驗證

### 確認 Hooks 正在運作

當 Hooks 正常運作時，對話開始會看到類似訊息：

```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context

### Events
Past or scheduled events, activities, appointments

### Facts
Factual information about the user or their environment
...
</kiroku-memory>
```

此訊息表示：
- ✅ SessionStart hook 成功執行
- ✅ API 服務正常連接
- ✅ 記憶上下文已注入對話

如果記憶內容為空（只有分類標題），表示尚未儲存任何記憶。

### 快速健康檢查

```bash
curl http://localhost:8000/health
```

成功回應：
```json
{"status":"ok","version":"0.1.0"}
```

### 自動儲存條件詳解

Stop Hook 會分析對話內容，只儲存符合條件的資訊：

#### 會儲存的內容（需符合 pattern + 長度門檻）

| Pattern 類型 | 範例 | 最小加權長度 |
|-------------|------|-------------|
| 偏好表達 | `我喜歡...`、`I prefer...`、`偏好...` | 10 |
| 決定陳述 | `決定使用...`、`chosen...`、`selected...` | 10 |
| 設定記錄 | `設定...`、`config...`、`專案使用...` | 10 |
| 事實陳述 | `工作於...`、`住在...`、`located...` | 10 |
| 無 pattern | 一般內容 | 35 |

> **加權長度計算**：CJK 字元 × 2.5 + 其他字元 × 1

#### 會過濾掉的雜訊

| 類型 | 範例 |
|------|------|
| 短回覆 | `好的`、`OK`、`是的`、`沒問題` |
| 感謝語 | `謝謝`、`thanks` |
| 問句 | `什麼是...`、`怎麼做...`、`how...` |
| 錯誤訊息 | `error`、`錯誤`、`failed` |

#### 其他限制

- **去重複**：24 小時內相同內容不重複儲存
- **數量限制**：每次對話最多儲存 3 筆
- **非同步執行**：Stop Hook 以 async 模式執行，不阻塞對話

## 故障排除

### 服務無法連接

```bash
# 檢查服務狀態
curl http://localhost:8000/health

# 重啟服務
cd ~/zoo/kiroku-memory
docker compose restart
uv run uvicorn kiroku_memory.api:app --reload
```

### Hooks 未執行

1. 確認 `~/.claude/settings.json` 有 hooks 設定
2. 重新啟動 Claude Code
3. 使用 `claude --debug` 檢視 hook 執行情況

### 記憶未儲存

- 確認內容符合儲存模式
- 檢查 `~/.cache/kiroku-memory/recent_saves.json` 去重複快取

## 移除整合

```bash
# 1. 從 settings.json 移除 hooks 設定

# 2. 刪除 skill 目錄
rm -rf ~/.claude/skills/kiroku-memory/

# 3. 清除快取
rm -rf ~/.cache/kiroku-memory/
```

## 技術細節

### Hook 資料流

```
SessionStart
     │
     ▼
┌─────────────────────┐
│ session-start.py    │
│ - 讀取 stdin JSON   │
│ - 取得 cwd          │
│ - 呼叫 /context API │
│ - 輸出到 stdout     │
└─────────────────────┘
     │
     ▼
 Context 注入到對話

     ...對話進行...

Stop
     │
     ▼
┌─────────────────────┐
│ stop.py             │
│ - 讀取 transcript   │
│ - 過濾重要內容      │
│ - 去重複檢查        │
│ - 呼叫 /ingest API  │
│ - 呼叫 /extract API │
└─────────────────────┘
     │
     ▼
 記憶已儲存
```

### API 端點使用

| 功能 | 端點 | 方法 |
|------|------|------|
| 載入 context | `/context` | GET |
| 儲存記憶 | `/ingest` | POST |
| 抽取事實 | `/extract` | POST |
| 搜尋記憶 | `/retrieve` | GET |
| 健康檢查 | `/health` | GET |
