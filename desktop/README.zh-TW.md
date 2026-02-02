# Kiroku Memory 桌面版

> 為 AI Agent 長期記憶管理打造的獨立 macOS 應用程式

[English](README.md) | [日本語](README.ja.md)

## 什麼是 Kiroku Memory？

Kiroku Memory 是一個 AI Agent 記憶系統，可以跨對話儲存、整理和檢索資訊。不同於傳統聊天機器人在每次對話結束後就忘記一切，Kiroku Memory 能夠實現持久化記憶。

**桌面版功能：**
- **零配置** - 不需要安裝 Python、Docker 或資料庫
- **一鍵啟動** - 雙擊即可開始使用
- **安全儲存** - API Key 儲存在 macOS 鑰匙圈
- **內嵌資料庫** - SurrealDB 在本機運行，資料完全私密

## 安裝方式

### 方式一：下載 DMG（推薦）

1. 從 [Releases](https://github.com/yelban/kiroku-memory/releases) 下載 `Kiroku Memory_x.x.x_aarch64.dmg`
2. 開啟 DMG 檔案
3. 將 **Kiroku Memory** 拖曳到 **應用程式** 資料夾
4. 從應用程式啟動

#### macOS：首次啟動（未簽署的 App）

此 App 未使用 Apple 開發者憑證簽署。首次啟動時，macOS 會阻擋。

**如果出現「已損毀，無法打開」：**

在終端機執行以下指令移除隔離屬性：

```bash
xattr -cr /Applications/Kiroku\ Memory.app
```

**如果出現「無法打開，因為 Apple 無法檢查」：**

1. 右鍵點擊（或 Control + 點擊）**Kiroku Memory.app**
2. 從選單中選擇「**打開**」
3. 在對話框中點擊「**打開**」

或到「**系統設定**」→「**隱私與安全性**」→ 點擊「**強制打開**」

允許一次後，App 之後就能正常開啟。

### 方式二：從原始碼建構

```bash
# 複製儲存庫
git clone https://github.com/yelban/kiroku-memory.git
cd kiroku-memory

# 建構 Python runtime（僅首次需要）
bash tools/packaging/build-python.sh

# 建構桌面應用程式
cd desktop
npm install
npm run tauri build
```

建構完成的應用程式位於：`desktop/src-tauri/target/release/bundle/macos/Kiroku Memory.app`

## 開始使用

### 1. 啟動應用程式

雙擊 **Kiroku Memory.app**。應用程式會：
- 自動啟動內嵌的 Python 服務
- 初始化本機 SurrealDB 資料庫
- 當服務就緒時顯示綠色狀態指示燈

### 2. 設定 OpenAI API Key（選用）

**大部分功能不需要 API Key。** 只有需要語意搜尋時才需要設定：

| 功能 | 無 API Key | 有 API Key |
|------|-----------|------------|
| 儲存記憶 | ✅ | ✅ |
| 瀏覽記憶 | ✅ | ✅ |
| 關鍵字搜尋 | ✅ | ✅ |
| **語意搜尋** | ❌ | ✅ |

若要啟用語意搜尋：

1. 前往**設定**頁籤
2. 輸入您的 OpenAI API Key
3. 點擊**儲存**

您的 Key 會安全地儲存在 macOS 鑰匙圈中，而非明文檔案。

### 3. 開始使用

**狀態儀表板**
- 檢視服務健康狀態和版本
- 監控記憶統計資料
- 查看資料庫狀態

**記憶瀏覽器**
- 瀏覽已儲存的記憶
- 依關鍵字搜尋
- 依分類篩選（偏好、事實、目標等）
- 檢視詳細記憶資訊

**設定**
- 設定 OpenAI API Key（選用）
- 切換自動啟動服務

**維護**
- 重啟服務
- 檢視資料目錄位置
- 在 Finder 中開啟資料位置

## 運作原理

```
┌─────────────────────────────────────────────────────────┐
│                   Kiroku Memory.app                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   React     │    │   Tauri     │    │   Python    │ │
│  │   前端      │◄──►│   (Rust)    │◄──►│   FastAPI   │ │
│  │             │    │             │    │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                              │          │
│                                              ▼          │
│                                        ┌─────────────┐ │
│                                        │  SurrealDB  │ │
│                                        │  (內嵌式)    │ │
│                                        └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**技術棧：**
- **前端**：React 19 + Vite + Tailwind CSS + shadcn/ui
- **外殼**：Tauri v2 (Rust)
- **後端**：Python 3.11（內嵌）+ FastAPI
- **資料庫**：SurrealDB（內嵌式，檔案型）

## 資料儲存

所有資料都儲存在您的電腦本機：

```
~/Library/Application Support/com.kiroku.memory/
├── surrealdb/
│   └── kiroku/          # 資料庫檔案
└── settings.json        # 應用程式設定（非敏感）
```

OpenAI API Key 單獨儲存在 **macOS 鑰匙圈**中以確保安全。

## 與 Claude Code 整合

Kiroku Memory 桌面版可與 [Claude Code Skill](../skill/SKILL.zh-TW.md) 協同運作：

| 功能 | 桌面版 | Claude Code Skill |
|------|--------|-------------------|
| 記憶儲存 | 本機 SurrealDB | 相同 API |
| 記憶檢索 | 圖形介面瀏覽器 | `/recall` 指令 |
| 自動擷取 | 手動 | SessionStart/Stop hooks |
| 使用情境 | 視覺化管理 | 對話中記憶 |

兩者都可連接到相同的 API：`http://127.0.0.1:8000`

## 疑難排解

### 服務無法啟動

1. 檢查 8000 埠是否被佔用：
   ```bash
   lsof -i :8000
   ```
2. 嘗試從維護頁籤重啟
3. 在 Console.app 檢查錯誤日誌

### 記憶沒有出現

1. 確認服務狀態顯示「運行中」（綠色指示燈）
2. 檢查是否已設定 OpenAI API Key（萃取功能需要）
3. 在記憶瀏覽器中嘗試手動重新整理

### 應用程式啟動時當機

1. 刪除應用程式資料後重試：
   ```bash
   rm -rf ~/Library/Application\ Support/com.kiroku.memory/
   ```
2. 重新下載並安裝應用程式

## 系統需求

- **作業系統**：macOS 10.15 (Catalina) 或更新版本
- **架構**：Apple Silicon (aarch64) 或 Intel (x86_64)
- **磁碟空間**：約 200 MB（應用程式 + 資料）
- **記憶體**：最低 512 MB

## 隱私與安全

- **所有資料保留在本機** - 無雲端同步，無遙測
- **API Key 在鑰匙圈中** - 絕不以明文儲存
- **無需網路** - 完全離線運作（除 OpenAI 功能外）

## 授權

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) - 詳見 [LICENSE](../LICENSE)。商業使用需另行授權。

## 相關連結

- [Kiroku Memory API 文件](../docs/user-guide.md)
- [Claude Code 整合指南](../docs/claude-code-integration.md)
- [架構概覽](../docs/architecture.md)
