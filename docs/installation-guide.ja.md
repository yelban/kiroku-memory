# インストールガイド

> macOS に Kiroku Memory をインストールする手順

**言語**: [English](installation-guide.md) | [繁體中文](installation-guide.zh-TW.md) | [日本語](installation-guide.ja.md)

---

## 前提条件

- **macOS**（現在サポート対象）
- **OpenAI API キー**（[こちらで取得](https://platform.openai.com/api-keys)）

---

## ステップ 1：Docker Desktop のインストール

Docker は Kiroku Memory が必要とする PostgreSQL データベースを実行します。

1. こちらからダウンロード：https://www.docker.com/products/docker-desktop
2. ダウンロードした `.dmg` ファイルを開く
3. Docker をアプリケーションフォルダにドラッグ
4. アプリケーションから Docker を起動
5. Docker が完全に起動するまで待機

**成功の確認**：メニューバー（画面右上）にクジラアイコン 🐳 が表示される

**トラブルシューティング**：
- Docker が権限を要求した場合、「OK」をクリックして許可
- 初回起動は初期化に 1-2 分かかる場合があります

---

## ステップ 2：uv のインストール（Python パッケージマネージャー）

uv は pip の代わりに使用する高速な Python パッケージマネージャーです。

ターミナルを開いて実行：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール完了後、**ターミナルを再起動**するか、以下を実行：

```bash
source ~/.zshrc
```

**インストールの確認**：

```bash
uv --version
```

以下のような出力が表示されるはずです：`uv 0.5.x`

---

## ステップ 3：Kiroku Memory のダウンロード

プロジェクト用のディレクトリを選択（例：`~/projects`）：

```bash
# ディレクトリが存在しない場合は作成
mkdir -p ~/projects
cd ~/projects

# リポジトリをクローン
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory
```

---

## ステップ 4：環境変数の設定

```bash
# サンプルファイルをコピー
cp .env.example .env

# エディタで開く
open -e .env   # テキストエディットで開く
# または：nano .env / vim .env / code .env
```

**ファイルを編集して OpenAI API キーを設定**：

```
OPENAI_API_KEY=sk-あなたの実際の-api-key
```

ファイルを保存して閉じます。

---

## ステップ 5：データベースの起動

```bash
docker compose up -d
```

**成功の確認**：
```
✔ Container kiroku-memory-db  Started
```

**トラブルシューティング**：
- 「Cannot connect to the Docker daemon」と表示された場合、Docker Desktop が実行中か確認
- 初回実行時は PostgreSQL イメージのダウンロード（約 400MB）が必要なため、しばらくお待ちください

---

## ステップ 6：Python 依存関係のインストール

```bash
uv sync
```

仮想環境を作成し、必要なパッケージをすべてインストールします。

**成功の確認**：エラーなく、パッケージのインストールが完了

---

## ステップ 7：API サービスの起動

```bash
uv run uvicorn kiroku_memory.api:app --reload
```

**成功の確認**：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

**このターミナルウィンドウは開いたまま** - API はフォアグラウンドで実行されます。

**動作確認**（新しいターミナルで）：

```bash
curl http://localhost:8000/health
```

期待されるレスポンス：
```json
{"status":"ok","version":"0.1.0"}
```

---

## ステップ 8：Claude Code Skill のインストール

**新しいターミナルウィンドウ**を開き（API は実行したまま）、以下を実行：

```bash
cd ~/projects/kiroku-memory
./skill/assets/install.sh
```

skill ファイルが `~/.claude/skills/kiroku-memory/` にコピーされます。

---

## ステップ 9：Claude Code の再起動

1. Claude Code を完全に終了
2. Claude Code を再度開く

**成功の確認**：会話開始時に以下が表示される：
```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context
...
</kiroku-memory>
```

---

## インストール完了！🎉

以下のコマンドが使用可能になりました：

| コマンド | 説明 |
|----------|------|
| `/remember <テキスト>` | メモリを保存 |
| `/recall <クエリ>` | メモリを検索 |
| `/memory-status` | システムステータスを確認 |

---

## 上級：API サービスの自動起動（launchd）

毎回手動で API を起動したくない？launchd でログイン時に自動起動するよう設定できます。

### plist ファイルの作成

```bash
cat > ~/Library/LaunchAgents/com.kiroku-memory.api.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kiroku-memory.api</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/.local/bin/uv</string>
        <string>run</string>
        <string>uvicorn</string>
        <string>kiroku_memory.api:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/projects/kiroku-memory</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/YOUR_USERNAME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/kiroku-api.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/kiroku-api.err</string>
</dict>
</plist>
EOF
```

**重要**：`YOUR_USERNAME` を実際の macOS ユーザー名に置き換えてください。

ユーザー名を確認：
```bash
whoami
```

### plist ファイルの編集

```bash
# YOUR_USERNAME を実際のユーザー名に置換
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### サービスの読み込み

```bash
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### 実行中か確認

```bash
# サービスステータスを確認
launchctl list | grep kiroku

# API をテスト
curl http://localhost:8000/health
```

### ログの確認

```bash
# 標準出力
tail -f /tmp/kiroku-api.log

# エラーログ
tail -f /tmp/kiroku-api.err
```

### サービスの停止/アンロード

```bash
# 停止してアンロード
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# 変更後に再起動する場合
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

---

## トラブルシューティング

### API にアクセスすると「Connection refused」

1. Docker が実行中か確認（メニューバーにクジラアイコン）
2. データベースコンテナが実行中か確認：`docker ps`
3. API が実行中か確認：`curl http://localhost:8000/health`

### 「uv: command not found」

ターミナルを再起動するか、以下を実行：
```bash
source ~/.zshrc
```

### 「OPENAI_API_KEY not set」

以下を確認：
1. `.env` ファイルを作成したか：`cp .env.example .env`
2. 実際の API キーを追加したか（プレースホルダーではなく）

### API が起動後すぐに終了する

エラーログを確認：
```bash
cat /tmp/kiroku-api.err
```

よくある原因：
- OpenAI API キーが無効
- データベースが起動していない
- ポート 8000 が既に使用中

### launchd サービスが起動しない

1. plist の構文エラーを確認：
   ```bash
   plutil -lint ~/Library/LaunchAgents/com.kiroku-memory.api.plist
   ```

2. パスが存在するか確認：
   ```bash
   ls -la ~/.local/bin/uv
   ls -la ~/projects/kiroku-memory
   ```

---

## アンインストール

```bash
# launchd サービスを停止（インストール済みの場合）
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist 2>/dev/null
rm ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# Claude Code skill を削除
rm -rf ~/.claude/skills/kiroku-memory

# Docker コンテナを停止して削除
cd ~/projects/kiroku-memory
docker compose down -v

# プロジェクトディレクトリを削除
rm -rf ~/projects/kiroku-memory
```
