# 分層檢索策略

## 概述

SessionStart hook 會在對話開始時載入記憶上下文，使用分層策略確保重要資訊優先顯示。

## 檢索層級

### Tier 1: 分類摘要 (Category Summaries)

- **數量**: 每個分類 1 條摘要
- **來源**: Kiroku Memory 的 `/context` API
- **用途**: 快速概覽，了解用戶整體偏好

### Tier 2: 近期事實 (Recent Facts)

- **數量**: 最多 10 條
- **排序**: 按建立時間倒序
- **用途**: 詳細資訊，支援深入查詢

## 上下文格式

注入到對話的格式：

```xml
<kiroku-memory>
## User Memory Context

### Preferences
用戶偏好深色模式，喜歡使用 Neovim...

### Facts
用戶在 Google 工作，是軟體工程師...
</kiroku-memory>
```

## 大小限制

| 項目 | 限制 |
|------|------|
| 總上下文 | 2000 字元 |
| 超過時 | 截斷並加 `...(truncated)` |

## 範圍策略

### 全域 + 專案合併

SessionStart hook 會同時載入：

1. **全域記憶** (`global:user`)
2. **專案記憶** (`project:<current-project>`)

合併後注入到上下文。

### 範圍識別

專案名稱從 hook 的 `cwd` 欄位提取：
```python
project_name = os.path.basename(cwd)
```

## 效能考量

### 逾時設定

- SessionStart hook 逾時: **5 秒**
- API 請求逾時: **5 秒**

### 優雅降級

如果 Kiroku Memory API 無法連接：
- 不顯示錯誤給用戶
- 靜默跳過，繼續對話
- 在 stderr 記錄警告（debug 模式可見）

## 調整設定

### 修改上下文大小

編輯 `~/.claude/skills/kiroku-memory/hooks/session-start.py`：
```python
MAX_CONTEXT_CHARS = 2000  # 調整此值
```

### 修改逾時

編輯 `~/.claude/settings.json`：
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "timeout": 5  // 秒
      }]
    }]
  }
}
```
