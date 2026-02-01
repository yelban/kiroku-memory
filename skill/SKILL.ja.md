# Kiroku Memory

> AI エージェント向け階層型検索メモリシステム

セッション間・プロジェクト間で永続化可能な AI エージェント長期記憶システム。

## コマンド

| コマンド | 説明 |
|----------|------|
| `/remember <内容>` | 記憶を保存 |
| `/recall <クエリ>` | 記憶を検索 |
| `/forget <クエリ>` | 記憶を削除/アーカイブ |
| `/memory-status` | システム状態を確認 |

## 使用例

```bash
# 記憶を保存
/remember ユーザーはダークモードを好む

# カテゴリ指定で保存
/remember --category preferences Neovim を使うのが好き

# グローバル記憶として保存
/remember --global ニックネームは吹吹

# 記憶を検索
/recall エディタの好み

# 完全なコンテキストを取得
/recall --context

# 状態を確認
/memory-status
```

## 記憶スコープ

- **グローバル** (`global:user`)：プロジェクト横断、個人設定
- **プロジェクト** (`project:<name>`)：プロジェクト固有、アーキテクチャ決定

デフォルト動作：
- プロジェクトディレクトリ内 → プロジェクト記憶に保存
- プロジェクトコンテキストなし → グローバル記憶に保存

## カテゴリ

| カテゴリ | 優先度 | 説明 |
|----------|--------|------|
| `preferences` | 1.0 | ユーザー設定（最高優先） |
| `facts` | 0.9 | 事実情報 |
| `goals` | 0.7 | 目標・計画 |
| `skills` | 0.6 | スキル・専門知識 |
| `relationships` | 0.5 | 人間関係 |
| `events` | 0.4 | イベント・活動（最低優先） |

## 優先順位ソートとスマート切り詰め

### ハイブリッド優先度モデル

カテゴリはアルファベット順ではなく優先度順でソート：
- **静的重み**：上記で定義された基本優先度
- **動的要素**：使用頻度 + 新鮮度

```
priority = static_weight × (1.0 + usage_weight × usage_score + recency_weight × recency_score)
```

### スマート切り詰め

コンテキストが制限を超える場合（デフォルト 2000 文字）：
- **カテゴリ途中で切り詰めない**：完全なカテゴリを削除
- **優先度ベース**：低優先度カテゴリから先に削除
- **フォーマット維持**：壊れた markdown にならない

## ドキュメント

- [API 仕様](references/api-contract.md)
- [記憶スコープ](references/scopes.md)
- [フィルタリングルール](references/filtering-rules.md)
- [検索ポリシー](references/retrieval-policy.md)

## インストール

### 方法1：Plugin Marketplace（推奨）

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add https://github.com/yelban/kiroku-memory.git

# 2. プラグインをインストール
/plugin install kiroku-memory
```

### 方法2：npx Skills CLI

```bash
npx skills add yelban/kiroku-memory
# または
npx add-skill yelban/kiroku-memory
# または
npx openskills install yelban/kiroku-memory
```

### 方法3：インストールスクリプト

```bash
curl -fsSL https://raw.githubusercontent.com/yelban/kiroku-memory/main/skill/assets/install.sh | bash
```

インストーラーが作成するもの：
- `~/.claude/skills/kiroku-memory/` - メインスキル（スクリプトとフック）
- `~/.claude/skills/remember/` - `/remember` コマンドエイリアス
- `~/.claude/skills/recall/` - `/recall` コマンドエイリアス
- `~/.claude/skills/forget/` - `/forget` コマンドエイリアス
- `~/.claude/skills/memory-status/` - `/memory-status` コマンドエイリアス

## 前提条件

Kiroku Memory サービスが起動している必要があります：

```bash
cd ~/path/to/kiroku-memory
docker compose up -d
uv run uvicorn kiroku_memory.api:app --reload
```

デフォルト API エンドポイント：`http://localhost:8000`（`KIROKU_API` 環境変数で上書き可能）

## 機能

- **自動読み込み**：SessionStart フックが自動的にメモリコンテキストを注入
- **二段階保存**：Fast Path + Slow Path ハイブリッドアーキテクチャ
- **重複排除**：24時間 TTL で重複保存を防止
- **結論抽出**：Claude の応答からキー結論を抽出

## 自動保存：二段階メモリキャプチャ

Stop Hook は**ファスト＆スロー**二段階アーキテクチャを採用：

### Phase 1: Fast Path (<1秒、同期)

正規表現パターンマッチングで即座にキャプチャ：

| パターンタイプ | 例 |
|---------------|-----|
| 好み | `好き...`、`prefer...` |
| 決定 | `に決めた...`、`選択...` |
| 発見 | `発見...`、`解決策は...` |
| 学習 | `学んだ...`、`原因は...`、`問題は...` |

Claude の応答から**結論マーカー**も抽出：
- `解決方案/Solution`、`発見/Discovery`、`結論/Conclusion`
- `建議/Recommendation`、`根因/Root cause`

### Phase 2: Slow Path (5-15秒、非同期)

Claude CLI を使用したバックグラウンド LLM 分析：

- 分離されたサブプロセスで実行（Claude Code をブロックしない）
- 直近 6 件の user + 4 件の assistant メッセージを分析
- 最大 5 件のメモリをタイプ/信頼度付きで抽出
- メモリタイプ：`discovery`、`decision`、`learning`、`preference`、`fact`
- ログは `~/.cache/kiroku-memory/llm-worker.log` に記録

両フェーズは 24 時間重複排除キャッシュを共有。

## 翻訳

- [English](SKILL.md)
- [繁體中文](SKILL.zh-TW.md)
