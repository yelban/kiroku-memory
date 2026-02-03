# Kiroku Memory デスクトップ版

> AI Agent 長期記憶管理のためのスタンドアロン macOS アプリケーション

[English](README.md) | [繁體中文](README.zh-TW.md)

## Kiroku Memory とは？

Kiroku Memory は、セッションを跨いで情報を保存・整理・検索できる AI Agent 記憶システムです。会話終了後にすべてを忘れてしまう従来のチャットボットとは異なり、Kiroku Memory は永続的な記憶を実現します。

**デスクトップ版の特徴：**
- **設定不要** - Python、Docker、データベースのセットアップは不要
- **ワンクリック起動** - ダブルクリックですぐに使用開始
- **安全なストレージ** - API キーは macOS キーチェーンに保存
- **組み込みデータベース** - SurrealDB がローカルで動作、データは完全にプライベート

## インストール方法

### 方法1：DMG ダウンロード（推奨）

1. [Releases](https://github.com/yelban/kiroku-memory/releases) から `Kiroku Memory_x.x.x_aarch64.dmg` をダウンロード
2. DMG ファイルを開く
3. **Kiroku Memory** を **アプリケーション** フォルダにドラッグ
4. アプリケーションから起動

### 方法2：ソースからビルド

```bash
# リポジトリをクローン
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory

# Python ランタイムをビルド（初回のみ）
bash tools/packaging/build-python.sh

# デスクトップアプリをビルド
cd desktop
npm install
npm run tauri build
```

ビルドされたアプリは以下に生成されます：`desktop/src-tauri/target/release/bundle/macos/Kiroku Memory.app`

## 使い方

### 1. アプリを起動

**Kiroku Memory.app** をダブルクリック。アプリは：
- 組み込み Python サービスを自動起動
- ローカル SurrealDB データベースを初期化
- 準備完了時に緑のステータスインジケータを表示

### 2. OpenAI API キーを設定（オプション）

**ほとんどの機能は API キーなしで動作します。** セマンティック検索が必要な場合のみ設定してください：

| 機能 | API キーなし | API キーあり |
|------|-------------|-------------|
| 記憶を保存 | ✅ | ✅ |
| 記憶を閲覧 | ✅ | ✅ |
| キーワード検索 | ✅ | ✅ |
| **セマンティック検索** | ❌ | ✅ |

セマンティック検索を有効にするには：

1. **設定**タブに移動
2. OpenAI API キーを入力
3. **保存**をクリック

キーは macOS キーチェーンに安全に保存され、プレーンテキストファイルには保存されません。

### 3. 使用開始

**ステータスダッシュボード**
- サービスの健全性とバージョンを確認
- メモリ統計を監視
- データベース状態を確認

**メモリブラウザ**
- 保存された記憶を閲覧
- キーワード検索
- カテゴリでフィルター（好み、事実、目標など）
- 詳細なメモリ情報を表示

**設定**
- OpenAI API キーを設定（オプション）
- サービス自動起動を切り替え

**メンテナンス**
- サービスを再起動
- データディレクトリの場所を確認
- Finder でデータ場所を開く

## 仕組み

```
┌─────────────────────────────────────────────────────────┐
│                   Kiroku Memory.app                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   React     │    │   Tauri     │    │   Python    │ │
│  │ フロントエンド│◄──►│   (Rust)    │◄──►│   FastAPI   │ │
│  │             │    │             │    │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                              │          │
│                                              ▼          │
│                                        ┌─────────────┐ │
│                                        │  SurrealDB  │ │
│                                        │  (組み込み)   │ │
│                                        └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**技術スタック：**
- **フロントエンド**：React 19 + Vite + Tailwind CSS + shadcn/ui
- **シェル**：Tauri v2 (Rust)
- **バックエンド**：Python 3.11（バンドル）+ FastAPI
- **データベース**：SurrealDB（組み込み、ファイルベース）

## データストレージ

すべてのデータはお使いのマシンのローカルに保存されます：

```
~/Library/Application Support/com.kiroku.memory/
├── surrealdb/
│   └── kiroku/          # データベースファイル
└── settings.json        # アプリ設定（非機密）
```

OpenAI API キーはセキュリティのため **macOS キーチェーン**に個別に保存されます。

## Claude Code との統合

Kiroku Memory デスクトップ版は [Claude Code Skill](../skill/SKILL.ja.md) と連携できます：

| 機能 | デスクトップ版 | Claude Code Skill |
|------|---------------|-------------------|
| メモリストレージ | ローカル SurrealDB | 同じ API |
| メモリ検索 | GUI ブラウザ | `/recall` コマンド |
| 自動キャプチャ | 手動 | SessionStart/Stop フック |
| ユースケース | 視覚的管理 | 会話中のメモリ |

どちらも同じ API（`http://127.0.0.1:8000`）に接続できます。

## トラブルシューティング

### サービスが起動しない

1. ポート 8000 が使用中か確認：
   ```bash
   lsof -i :8000
   ```
2. メンテナンスタブから再起動を試す
3. Console.app でエラーログを確認

### メモリが表示されない

1. サービスステータスが「Running」（緑インジケータ）であることを確認
2. OpenAI API キーが設定されているか確認（抽出に必要）
3. メモリブラウザで手動更新を試す

### アプリが起動時にクラッシュ

1. アプリデータを削除して再試行：
   ```bash
   rm -rf ~/Library/Application\ Support/com.kiroku.memory/
   ```
2. アプリを再ダウンロードして再インストール

## システム要件

- **OS**：macOS 10.15 (Catalina) 以降
- **アーキテクチャ**：Apple Silicon (aarch64) または Intel (x86_64)
- **ディスク容量**：約 200 MB（アプリ + データ）
- **メモリ**：最低 512 MB

## プライバシーとセキュリティ

- **すべてのデータはローカルに保存** - クラウド同期なし、テレメトリなし
- **API キーはキーチェーンに保存** - プレーンテキストでは保存されない
- **ネットワーク不要** - 完全オフラインで動作（OpenAI 機能を除く）

## ライセンス

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) - 詳細は [LICENSE](../LICENSE) をご覧ください。商用利用には別途ライセンスが必要です。

## 関連リンク

- [Kiroku Memory API ドキュメント](../docs/user-guide.md)
- [Claude Code 統合ガイド](../docs/claude-code-integration.md)
- [アーキテクチャ概要](../docs/architecture.md)
