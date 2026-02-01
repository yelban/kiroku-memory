# Kiroku Memory

AI Agent 跨 session、跨專案記憶系統。

## 命令

透過 `scripts/` 執行：

| 命令 | 腳本 | 參數 |
|------|------|------|
| `/remember` | `remember.py` | `<內容> [--category CAT] [--global]` |
| `/recall` | `recall.py` | `<查詢> [--context]` |
| `/forget` | `forget.py` | `<查詢>` |
| `/memory-status` | `memory-status.py` | (無) |

## 記憶範圍

- `global:user` — 跨專案（個人偏好）
- `project:<name>` — 專案特定（架構決策）

預設：專案目錄 → 專案範圍；否則 → 全域範圍。

## 分類（依優先級）

`preferences` (1.0) > `facts` (0.9) > `goals` (0.7) > `skills` (0.6) > `relationships` (0.5) > `events` (0.4)

## Hooks

- **SessionStart**：透過 `/context` API 自動載入記憶
- **Stop**：自動儲存重要內容（雙階段：regex + 非同步 LLM）

## 參考文件

- [API 規格](references/api-contract.md) — 端點規格
- [記憶範圍](references/scopes.md) — 範圍解析邏輯
- [過濾規則](references/filtering-rules.md) — 儲存條件
- [檢索策略](references/retrieval-policy.md) — 優先級與截斷
- [自動儲存](references/auto-save.md) — 雙階段記憶捕捉細節
