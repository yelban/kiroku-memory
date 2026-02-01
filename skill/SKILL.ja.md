# Kiroku Memory

AI エージェント向けセッション間・プロジェクト間メモリシステム。

## コマンド

`scripts/` で実行：

| コマンド | スクリプト | 引数 |
|----------|-----------|------|
| `/remember` | `remember.py` | `<内容> [--category CAT] [--global]` |
| `/recall` | `recall.py` | `<クエリ> [--context]` |
| `/forget` | `forget.py` | `<クエリ>` |
| `/memory-status` | `memory-status.py` | (なし) |

## スコープ

- `global:user` — プロジェクト横断（個人設定）
- `project:<name>` — プロジェクト固有（アーキテクチャ決定）

デフォルト：プロジェクトディレクトリ → プロジェクトスコープ；それ以外 → グローバルスコープ。

## カテゴリ（優先度順）

`preferences` (1.0) > `facts` (0.9) > `goals` (0.7) > `skills` (0.6) > `relationships` (0.5) > `events` (0.4)

## フック

- **SessionStart**：`/context` API でメモリを自動読み込み
- **Stop**：重要な内容を自動保存（二段階：regex + 非同期 LLM）

## 参照ドキュメント

- [API 仕様](references/api-contract.md) — エンドポイント仕様
- [スコープ](references/scopes.md) — スコープ解決ロジック
- [フィルタリングルール](references/filtering-rules.md) — 保存条件
- [検索ポリシー](references/retrieval-policy.md) — 優先度と切り詰め
- [自動保存](references/auto-save.md) — 二段階メモリキャプチャ詳細
