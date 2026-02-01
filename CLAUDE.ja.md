# Kiroku Memory

> AI エージェント向け階層型検索メモリシステム

Rohit の "How to Build an Agent That Never Forgets" の設計理念に基づいた AI エージェント長期記憶システム。

**コア機能**：
- Hybrid Memory Stack：append-only ログ、構造化 facts、カテゴリ別サマリーを統合
- Tiered Retrieval：サマリー優先、必要に応じて詳細へ
- Time Decay：記憶の信頼度が時間とともに減衰
- Conflict Resolution：矛盾の自動検出と解決

## クイックスタート

```bash
# PostgreSQL + pgvector を起動
docker compose up -d

# API を起動
uv run uvicorn kiroku_memory.api:app --reload

# ヘルスチェック
curl http://localhost:8000/health
```

## 環境変数

`.env.example` を `.env` にコピーして設定：

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/memory
OPENAI_API_KEY=sk-xxx  # 必須
```

## API エンドポイント

### コア機能
| Method | Path | 説明 |
|--------|------|------|
| POST | /ingest | 生メッセージを取り込み |
| GET | /retrieve | 階層型検索 |
| GET | /context | エージェントプロンプト用コンテキスト |

### インテリジェンス
| Method | Path | 説明 |
|--------|------|------|
| POST | /extract | facts を抽出 |
| POST | /summarize | サマリーを生成 |

### メンテナンス
| Method | Path | 説明 |
|--------|------|------|
| POST | /jobs/nightly | 日次メンテナンス |
| POST | /jobs/weekly | 週次メンテナンス |
| POST | /jobs/monthly | 月次メンテナンス |

### 監視
| Method | Path | 説明 |
|--------|------|------|
| GET | /health | ヘルスチェック |
| GET | /metrics | アプリケーションメトリクス |

## 統合例

### 他のエージェントでの使用

```javascript
// メモリコンテキストを取得
const context = await fetch("http://localhost:8000/context").then(r => r.json());

// システムプロンプトに追加
const enhancedPrompt = `${context.context}\n\n${originalPrompt}`;

// 会話後に重要な情報を保存
await fetch("http://localhost:8000/ingest", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ content: "ユーザーは...", source: "my-agent" })
});
```

## Claude Code 統合

完全な Claude Code 統合を実装：

```
~/.claude/skills/kiroku-memory/
├── SKILL.md              # ドキュメント（EN）
├── SKILL.zh-TW.md        # 繁體中文
├── SKILL.ja.md           # 日本語
├── scripts/              # /remember, /recall, /forget, /memory-status
├── references/           # 参考ドキュメント
└── assets/               # インストールスクリプト
```

**機能**：
- SessionStart hook がメモリコンテキストを自動読み込み
- Stop hook が重要な会話を知的に保存
- **優先順位ソート**：preferences > facts > goals（ハイブリッド静的+動的重み付け）
- **スマート切り詰め**：カテゴリの途中で切り詰めない、完全性を維持
- 手動コマンドでメモリ管理

詳細は `docs/claude-code-integration.md` を参照。

## ドキュメント

- `docs/architecture.md` - アーキテクチャ設計
- `docs/development-journey.md` - 開発経緯
- `docs/user-guide.md` - ユーザーガイド
- `docs/integration-guide.md` - 統合ガイド
- `docs/claude-code-integration.md` - Claude Code 統合ガイド
- `docs/renaming-changelog.md` - リネーム履歴

## プロジェクト構成

```
kiroku-memory/
├── kiroku_memory/       # コアモジュール
│   ├── api.py           # FastAPI エンドポイント
│   ├── ingest.py        # リソース取り込み
│   ├── extract.py       # Fact 抽出
│   ├── classify.py      # 分類器
│   ├── conflict.py      # 衝突解決
│   ├── summarize.py     # サマリー生成
│   ├── embedding.py     # ベクトル検索
│   ├── observability.py # 監視
│   ├── db/              # データベース
│   └── jobs/            # メンテナンスジョブ
├── tests/               # テスト
├── docs/                # ドキュメント
├── docker-compose.yml   # PostgreSQL 設定
└── pyproject.toml       # プロジェクト設定
```

## 開発

- 言語：Python 3.11+
- フレームワーク：FastAPI + SQLAlchemy 2.x
- データベース：PostgreSQL 16 + pgvector
- パッケージマネージャー：uv
- テスト：pytest + pytest-asyncio

## よく使うコマンド

```bash
# テスト実行
uv run pytest

# フォーマット
uv run ruff format .

# 型チェック
uv run mypy kiroku_memory/
```

## トラブルシューティング

### `.venv` スクリプトが "No such file or directory" と表示されるがファイルは存在する

原因：`.venv` 作成時に `VIRTUAL_ENV` 環境変数が別のプロジェクトを指していたため、shebang パスが不正。

```bash
# shebang を確認
head -1 .venv/bin/uvicorn
# 別のプロジェクトのパスが表示される場合、venv を再作成

# 修正
unset VIRTUAL_ENV
rm -rf .venv
uv sync
```

### `/extract` が空の結果を返すが LLM は正しく応答している

原因：OpenAI が `"object": null` を返すことがあり、Pydantic バリデーションが失敗。

修正済み：`kiroku_memory/extract.py` の `ExtractedFact.object` を `Optional[str]` に変更。

## 翻訳

- [English](CLAUDE.md)
- [繁體中文](CLAUDE.zh-TW.md)
