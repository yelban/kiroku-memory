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

| カテゴリ | 説明 |
|----------|------|
| `preferences` | ユーザー設定 |
| `facts` | 事実情報 |
| `events` | イベント・活動 |
| `relationships` | 人間関係 |
| `skills` | スキル・専門知識 |
| `goals` | 目標・計画 |

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
- **スマート保存**：Stop フックが重要な事実を知的に保存
- **重複排除**：24時間 TTL で重複保存を防止
- **パターンマッチング**：設定、決定、事実のみを保存（ノイズを無視）

## 翻訳

- [English](SKILL.md)
- [繁體中文](SKILL.zh-TW.md)
