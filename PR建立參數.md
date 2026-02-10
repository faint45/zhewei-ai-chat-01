# PR 建立／合併參數（供工具或手動使用）

## 儲存庫資訊

| 欄位 | 值 |
|------|-----|
| **儲存庫名稱（Repository name）** | `zhewei-ai-chat-01` |
| **儲存庫擁有者（Owner）** | `faint45` |
| **來源分支** | `brain` |
| **目標分支** | `main` |

---

## 你想執行哪個步驟？

- ☑ **建立新的 PR（從 brain 分支到 main）**
- ☐ 合併現有的 PR
- ☐ 同步本機的 main 分支

---

## 建立 PR 時使用的內容

### PR 標題

```
合併 brain（築未大腦／八階段）到 main
```

### PR 描述（可選）

```
將遠端分支 brain（來自本機 zhe-wei-tech 專案）合併進 main，作為主線。

- brain 內容：築未大腦、八階段流程、D 槽部屬、Railway、brain_server、/chat 手機對話頁等。
- 合併後 main 將包含上述功能，可依需求再調整或部署。
```

---

## 手動建立 PR 的連結

1. **直接開「比較並建立 PR」**  
   https://github.com/faint45/zhewei-ai-chat-01/compare/main...brain?expand=1

2. 在頁面中貼上上述**標題**與**描述**，再點 **Create pull request**。

---

## 若改為「合併現有 PR」或「同步本機 main」

- **合併現有 PR**：需先建立 PR，取得 PR 編號後，在 GitHub 該 PR 頁點 **Merge pull request**。
- **同步本機 main**（PR 已合併後執行）：
  ```powershell
  cd c:\Users\user\Desktop\zhe-wei-tech
  git fetch origin
  git checkout main
  git pull origin main
  ```
