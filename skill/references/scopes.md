# 記憶範圍 (Scopes)

## 概述

Kiroku Memory 使用 `source` 欄位區分記憶範圍，支援全域和專案兩種層級。

## 範圍類型

### 全域記憶 (`global:user`)

- **用途**：跨專案共享的個人偏好、通用知識
- **範例**：
  - 喜歡深色模式
  - 偏好使用 Neovim
  - 常用的程式語言是 Python
  - 暱稱叫「吹吹」

### 專案記憶 (`project:<name>`)

- **用途**：專案特定的決策、架構、模式
- **範例**：
  - 專案使用 PostgreSQL + pgvector
  - API 端點使用 RESTful 風格
  - 資料庫表名使用 snake_case

## 自動偵測規則

1. **有 Git 專案**：使用 git 根目錄名稱
   ```bash
   git rev-parse --show-toplevel | xargs basename
   # → kiroku-memory
   ```

2. **無 Git 但在目錄中**：使用當前目錄名稱
   ```bash
   basename $(pwd)
   # → my-project
   ```

3. **在家目錄或無專案**：使用 `global:user`

## 命令行覆蓋

```bash
# 強制存為全域記憶
/remember --global 喜歡咖啡

# 指定專案名稱
/remember --project other-project 使用 MongoDB
```

## 檢索範圍

```bash
# 只搜尋當前專案
/recall --project 資料庫設計

# 只搜尋全域
/recall --global 個人偏好

# 搜尋所有（預設）
/recall 偏好
```

## Context 注入

PrePrompt hook 會同時載入：

1. 全域摘要（3-5 條）
2. 全域事實（5 條）
3. 專案摘要（3-5 條）
4. 專案事實（10 條）

格式範例：

```
## Kiroku Memory Context

### Global
- 用戶喜歡深色模式
- 暱稱叫「吹吹」

### Project: kiroku-memory
- 使用 PostgreSQL + pgvector
- API 使用 FastAPI 框架
```
