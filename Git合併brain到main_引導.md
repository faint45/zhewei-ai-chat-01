# 把 brain 合併進 main — 引導步驟

**目前狀態**：本地 zhe-wei-tech 已推到遠端分支 **brain**；遠端 **main** 是另一套歷史（築未科技 AI 對話窗口／統一 API）。你要二選一：**開 PR 合併** 或 **強制覆蓋 main**。

---

## 選哪一種？

| 做法 | 適合情況 | 結果 |
|------|----------|------|
| **A. 開 PR 合併** | 想保留遠端 main 的歷史、或要審核後再合併 | main = main 舊歷史 + brain 的變更（或選「用 brain 取代」的合併方式） |
| **B. 強制覆蓋 main** | 確定不要遠端 main 現有內容，只要 brain 當主線 | main 完全變成 brain 的內容，遠端 main 舊歷史被改寫 |

---

## 做法 A：在 GitHub 開 PR，把 brain 合併進 main

### 步驟 1：打開「建立 Pull Request」頁面

1. 用瀏覽器開啟：  
   **https://github.com/faint45/zhewei-ai-chat-01/compare/main...brain**
2. 若 GitHub 要求登入，請先登入 **faint45** 帳號。

### 步驟 2：建立 PR

1. 頁面會顯示 **base: main** ← **compare: brain**（即：把 brain 的變更合併進 main）。
2. 點綠色按鈕 **「Create pull request」**。
3. **Title**：可填 `合併 brain（築未大腦／八階段）到 main`。
4. **Description**：可簡述「將本地 zhe-wei-tech（brain 分支）合併進 main，作為主線」。
5. 再點 **「Create pull request」** 完成建立。

### 步驟 3：合併 PR（二選一）

- **選項 1 — 一般合併（保留兩邊歷史）**  
  在 PR 頁面點 **「Merge pull request」** → 選 **「Create a merge commit」** → **「Confirm merge」**。  
  結果：main 會包含原本 main 的歷史 + brain 的變更。

- **選項 2 — 用 brain 的內容當 main（等同取代）**  
  在 PR 頁面點 **「Merge pull request」** 旁的小箭頭 → 選 **「Squash and merge」** 或 **「Rebase and merge」**（依你偏好）。  
  若你希望 main 的「檔案內容」完全和 brain 一致，但保留一個合併記錄，可用 **Squash and merge**，然後在合併後視需要刪除舊檔案。

### 步驟 4：本機與遠端同步（PR 合併完成後）

在 PowerShell 執行：

```powershell
cd c:\Users\user\Desktop\zhe-wei-tech
git fetch origin
git checkout main
git pull origin main
```

之後本機 main 就會和遠端 main 一致；若要繼續在 main 上開發，照常 `git add`、`git commit`、`git push origin main` 即可。

---

## 做法 B：強制用 brain 覆蓋遠端 main（改寫歷史）

**注意**：這會讓遠端 **main** 的現有內容與歷史被 **brain** 完全取代，無法用 GitHub 介面簡單還原，請先確認可接受。

### 步驟 1：確認本機在 main、且要推的就是目前內容

```powershell
cd c:\Users\user\Desktop\zhe-wei-tech
git branch
```

應顯示 `* main`。再確認你要推的 commit 都已在本機（例如剛做過 commit）。

### 步驟 2：強制推送到遠端 main

```powershell
git push origin main --force
```

若出現認證視窗，登入 GitHub 或輸入 Personal Access Token。

### 步驟 3：確認結果

1. 開啟 https://github.com/faint45/zhewei-ai-chat-01  
2. 預設分支應為 **main**，內容應與你本機 main（brain 那套）一致。  
3. 遠端分支 **brain** 仍可保留或到 **Branches** 頁刪除，不影響 main。

### 之後本機若要與遠端 main 對齊

```powershell
git pull origin main
```

（通常本機就是 main 且剛 force push，不需再 pull。）

---

## 對照表

| 項目 | 做法 A（開 PR） | 做法 B（--force） |
|------|-----------------|-------------------|
| 遠端 main 舊歷史 | 保留（或經合併） | 被改寫、不再保留 |
| 操作位置 | 主要在 GitHub 網頁 | 本機 PowerShell |
| 還原難度 | 較容易（可依 PR 還原） | 較難（需用 git 或 GitHub 救回） |
| 適合 | 要審核、保留紀錄 | 確定只要 brain 當主線 |

---

## 建議

- 若不確定是否還要遠端 main 的舊程式碼：選 **做法 A**，用 PR 合併，必要時還可關閉 PR 或還原。  
- 若確定遠端 main 可以完全換成 brain：可用 **做法 B**，一次到位。

完成其中一種後，後續就是：**完整跑八階段**（.env 填 GEMINI_API_KEY、啟動 Ollama、執行「啟動完整跑.bat」）與 **外網 brain.zhe-wei.net**（.env 填完整 CLOUDFLARE_TOKEN、`docker compose up -d`）。詳細步驟見 **剩下的如何處理.md**。
