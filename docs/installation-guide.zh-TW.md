# 安裝指南

> macOS 系統的 Kiroku Memory 安裝步驟指南

**語言**: [English](installation-guide.md) | [繁體中文](installation-guide.zh-TW.md) | [日本語](installation-guide.ja.md)

---

## 選擇安裝方式

| 方式 | 適合對象 | 安裝時間 | 需求 |
|------|---------|---------|------|
| **[方式 A：桌面應用程式](#方式-a桌面應用程式推薦)** | 所有人 | ~2 分鐘 | 無 |
| **[方式 B：開發者安裝](#方式-b開發者安裝)** | 自訂系統 | ~15 分鐘 | Docker、Python |

---

## 方式 A：桌面應用程式（推薦）

> **不需要 Docker、不需要 Python、不需要設定。** 最簡單的開始方式！

### 步驟 1：下載應用程式

從 [GitHub Releases](https://github.com/yelban/kiroku-memory/releases) 下載：

| 平台 | 架構 | 格式 |
|------|------|------|
| macOS | Apple Silicon (M1/M2/M3) | `.dmg` |
| macOS | Intel | `.dmg` |
| Windows | x86_64 | `.msi` |
| Linux | x86_64 | `.AppImage` |

### 步驟 2：安裝並啟動

1. **macOS**：開啟 `.dmg`，將應用程式拖曳到「應用程式」資料夾
2. **Windows**：執行 `.msi` 安裝程式
3. **Linux**：將 `.AppImage` 設為可執行並執行

#### macOS：首次啟動（未簽署的 App）

此 App 未使用 Apple 開發者憑證簽署。首次啟動時，macOS 會阻擋。

**如果出現「已損毀，無法打開」：**

```bash
xattr -cr /Applications/Kiroku\ Memory.app
```

**如果出現「無法打開，因為 Apple 無法檢查」：**

1. 右鍵點擊 **Kiroku Memory.app** → 選擇「**打開**」→ 點擊「**打開**」
2. 或：「**系統設定**」→「**隱私與安全性**」→「**強制打開**」

### 步驟 3：安裝 Claude Code Skill

```bash
npx skills add yelban/kiroku-memory
```

### 步驟 4：重新啟動 Claude Code

1. 完全關閉 Claude Code
2. 重新開啟 Claude Code

**成功指標**：對話開始時會顯示：
```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context
...
</kiroku-memory>
```

### 完成！🎉

現在可以使用：
- `/remember <文字>` - 儲存記憶
- `/recall <查詢>` - 搜尋記憶
- `/memory-status` - 檢查系統狀態

---

## 方式 B：開發者安裝

適合想從原始碼執行或自訂系統的開發者。

### 前置需求

- **macOS**（目前僅支援）
- **OpenAI API Key**（[在此取得](https://platform.openai.com/api-keys)）

---

### 步驟 1：安裝 Docker Desktop

Docker 用來執行 Kiroku Memory 需要的 PostgreSQL 資料庫。

1. 從此處下載：https://www.docker.com/products/docker-desktop
2. 開啟下載的 `.dmg` 檔案
3. 將 Docker 拖曳到「應用程式」資料夾
4. 從「應用程式」啟動 Docker
5. 等待 Docker 完全啟動

**成功指標**：畫面右上角選單列會出現鯨魚圖示 🐳

**疑難排解**：
- 若 Docker 要求權限，請點選「確定」授予
- 首次啟動可能需要 1-2 分鐘初始化

---

## 步驟 2：安裝 uv（Python 套件管理器）

uv 是我們使用的快速 Python 套件管理器，取代 pip。

開啟終端機並執行：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝完成後，**重新啟動終端機**或執行：

```bash
source ~/.zshrc
```

**驗證安裝**：

```bash
uv --version
```

應輸出類似：`uv 0.5.x`

---

## 步驟 3：下載 Kiroku Memory

選擇專案目錄（例如 `~/projects`）：

```bash
# 若目錄不存在則建立
mkdir -p ~/projects
cd ~/projects

# 複製儲存庫
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory
```

---

## 步驟 4：設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 用編輯器開啟
open -e .env   # 用「文字編輯」開啟
# 或用：nano .env / vim .env / code .env
```

**編輯檔案並填入你的 OpenAI API Key**：

```
OPENAI_API_KEY=sk-你的實際-api-key
```

儲存並關閉檔案。

---

## 步驟 5：啟動資料庫

```bash
docker compose up -d
```

**成功指標**：
```
✔ Container kiroku-memory-db  Started
```

**疑難排解**：
- 若顯示「Cannot connect to the Docker daemon」，請確認 Docker Desktop 正在執行
- 首次執行會下載 PostgreSQL 映像檔（約 400MB），請稍候

---

## 步驟 6：安裝 Python 依賴

```bash
uv sync
```

這會建立虛擬環境並安裝所有必要套件。

**成功指標**：無錯誤訊息，以套件安裝完成結束

---

## 步驟 7：啟動 API 服務

```bash
uv run uvicorn kiroku_memory.api:app --reload
```

**成功指標**：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

**保持此終端機視窗開啟** - API 在前景執行。

**驗證運作正常**（開新終端機）：

```bash
curl http://localhost:8000/health
```

預期回應：
```json
{"status":"ok","version":"0.1.0"}
```

---

## 步驟 8：安裝 Claude Code Skill

開啟**新的終端機視窗**（保持 API 執行），然後：

```bash
cd ~/projects/kiroku-memory
./skill/assets/install.sh
```

這會將 skill 檔案複製到 `~/.claude/skills/kiroku-memory/`。

---

## 步驟 9：重新啟動 Claude Code

1. 完全關閉 Claude Code
2. 重新開啟 Claude Code

**成功指標**：對話開始時會顯示：
```
SessionStart:startup hook success: <kiroku-memory>
## User Memory Context
...
</kiroku-memory>
```

---

## 安裝完成！🎉

現在可以使用：

| 指令 | 說明 |
|------|------|
| `/remember <文字>` | 儲存記憶 |
| `/recall <查詢>` | 搜尋記憶 |
| `/memory-status` | 檢查系統狀態 |

---

## 進階：API 服務自動啟動（launchd）

不想每次手動啟動 API？用 launchd 設定登入時自動啟動。

### 建立 plist 檔案

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

**重要**：將 `YOUR_USERNAME` 替換為你的實際 macOS 使用者名稱。

查看你的使用者名稱：
```bash
whoami
```

### 編輯 plist 檔案

```bash
# 將 YOUR_USERNAME 替換為實際使用者名稱
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### 載入服務

```bash
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

### 驗證執行中

```bash
# 檢查服務狀態
launchctl list | grep kiroku

# 測試 API
curl http://localhost:8000/health
```

### 檢視日誌

```bash
# 標準輸出
tail -f /tmp/kiroku-api.log

# 錯誤日誌
tail -f /tmp/kiroku-api.err
```

### 停止/卸載服務

```bash
# 停止並卸載
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# 修改後重新啟動
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist
launchctl load ~/Library/LaunchAgents/com.kiroku-memory.api.plist
```

---

## 疑難排解

### 存取 API 時「Connection refused」

1. 檢查 Docker 是否執行中（選單列有鯨魚圖示）
2. 檢查資料庫容器是否執行中：`docker ps`
3. 檢查 API 是否執行中：`curl http://localhost:8000/health`

### 「uv: command not found」

重新啟動終端機，或執行：
```bash
source ~/.zshrc
```

### 「OPENAI_API_KEY not set」

確認你已經：
1. 建立 `.env` 檔案：`cp .env.example .env`
2. 填入實際的 API key（不是範例文字）

### API 啟動後立即結束

檢查錯誤日誌：
```bash
cat /tmp/kiroku-api.err
```

常見原因：
- OpenAI API key 無效
- 資料庫未執行
- Port 8000 已被佔用

### launchd 服務無法啟動

1. 檢查 plist 語法錯誤：
   ```bash
   plutil -lint ~/Library/LaunchAgents/com.kiroku-memory.api.plist
   ```

2. 驗證路徑存在：
   ```bash
   ls -la ~/.local/bin/uv
   ls -la ~/projects/kiroku-memory
   ```

---

## 解除安裝

```bash
# 停止 launchd 服務（若已安裝）
launchctl unload ~/Library/LaunchAgents/com.kiroku-memory.api.plist 2>/dev/null
rm ~/Library/LaunchAgents/com.kiroku-memory.api.plist

# 移除 Claude Code skill
rm -rf ~/.claude/skills/kiroku-memory

# 停止並移除 Docker 容器
cd ~/projects/kiroku-memory
docker compose down -v

# 移除專案目錄
rm -rf ~/projects/kiroku-memory
```
