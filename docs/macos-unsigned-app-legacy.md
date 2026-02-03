# macOS: First Launch (Unsigned App) - Legacy Documentation

> **Note**: This documentation is for historical reference only. As of v0.1.13, Kiroku Memory is signed with an Apple Developer ID certificate and notarized by Apple. Users no longer need to perform these steps.

---

## English

The app is not signed with an Apple Developer certificate. On first launch, macOS will block it.

**If you see "damaged and can't be opened":**

Run this command in Terminal to remove the quarantine attribute:

```bash
xattr -cr /Applications/Kiroku\ Memory.app
```

**If you see "can't be opened because Apple cannot check it":**

1. Right-click (or Control-click) on **Kiroku Memory.app**
2. Select **Open** from the context menu
3. Click **Open** in the dialog

Or go to **System Settings** → **Privacy & Security** → Click **Open Anyway**

After allowing once, the app will open normally in the future.

---

## 繁體中文

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

---

## 日本語

このアプリは Apple 開発者証明書で署名されていません。初回起動時、macOS がブロックします。

**「破損しているため開けません」と表示された場合：**

ターミナルで以下のコマンドを実行して隔離属性を削除します：

```bash
xattr -cr /Applications/Kiroku\ Memory.app
```

**「Apple では確認できないため開けません」と表示された場合：**

1. **Kiroku Memory.app** を右クリック（または Control + クリック）
2. コンテキストメニューから「**開く**」を選択
3. ダイアログで「**開く**」をクリック

または「**システム設定**」→「**プライバシーとセキュリティ**」→「**このまま開く**」をクリック

一度許可すれば、以降は正常に開けます。
