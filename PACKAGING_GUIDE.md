# 築未科技大腦 - 軟件打包指南

## 📦 打包流程總覽

本指南説明如何將築未科技 AI 大腦系統打包成可分發的 Windows 軟件。

## 🎯 打包目標

- ✅ 單一可執行檔（或單資料夾）
- ✅ 包含所有 Python 依賴
- ✅ 包含靜態資源（HTML/CSS/JS）
- ✅ 配置向導與啟動腳本
- ✅ 用戶友好的使用說明

## 🛠️ 所需工具

### 1. Python 環境
```bash
python --version  # 需要 3.8+
```

### 2. PyInstaller
```bash
pip install pyinstaller
```

### 3. 項目依賴
```bash
pip install -r requirements-brain.txt
```

## 📋 打包步驟

### 方法 1: 使用自動化腳本（推薦）

執行打包腳本：
```bash
build_installer.bat
```

腳本會自動：
1. ✅ 檢查 Python 和 PyInstaller
2. ✅ 安裝依賴套件
3. ✅ 清理舊構建
4. ✅ 執行 PyInstaller 打包
5. ✅ 複製配置文件和啟動腳本

### 方法 2: 手動打包

#### 步驟 1: 安裝依賴
```bash
pip install -r requirements-brain.txt
pip install pyinstaller
```

#### 步驟 2: 清理舊構建
```bash
rmdir /s /q build dist
```

#### 步驟 3: 執行打包
```bash
pyinstaller brain_server.spec
```

#### 步驟 4: 複製資源
```bash
# 複製配置文件
copy .env.example dist\ZheweiTechBrain\

# 複製使用說明
copy README_軟件使用說明.md dist\ZheweiTechBrain\

# 創建啟動腳本
echo @echo off > dist\ZheweiTechBrain\啟動大腦.bat
echo ZheweiTechBrain.exe >> dist\ZheweiTechBrain\啟動大腦.bat
```

## 📁 打包配置文件

### brain_server.spec

這是 PyInstaller 的核心配置文件：

```python
# 主要配置項：
a = Analysis(
    ['brain_server.py'],  # 主程式入口
    datas=[
        ('brain_workspace/static', 'brain_workspace/static'),  # 靜態資源
        ('.env.example', '.'),
    ],
    hiddenimports=[  # 隱藏導入（動態加載的模組）
        'uvicorn.logging',
        'fastapi',
        'google.generativeai',
        'anthropic',
        # ... 其他模組
    ],
)
```

### 關鍵配置說明

1. **datas**：需要包含的數據文件
   - 靜態資源（HTML/CSS/JS）
   - 配置範例文件
   - JSON 配置文件

2. **hiddenimports**：運行時動態導入的模組
   - FastAPI 相關模組
   - AI 服務 SDK
   - WebSocket 組件

3. **excludes**：排除不需要的模組
   - tkinter（GUI 相關）
   - matplotlib（圖表庫）
   - pytest（測試框架）

## 🎁 打包產出

成功打包後的目錄結構：

```
dist/ZheweiTechBrain/
├── ZheweiTechBrain.exe     # 主執行檔
├── 啟動大腦.bat             # 啟動腳本
├── .env.example            # 配置範例
├── README_軟件使用說明.md   # 使用說明
├── brain_workspace/        # 靜態資源
│   └── static/
│       ├── index.html
│       ├── chat.html
│       └── ...
├── _internal/              # PyInstaller 內部文件
│   ├── *.dll
│   ├── *.pyd
│   └── ...
```

## 📦 分發準備

### 創建安裝包

使用 7-Zip 或 WinRAR 壓縮：
```bash
# 壓縮整個資料夾
"C:\Program Files\7-Zip\7z.exe" a -tzip ZheweiTechBrain_v1.0.zip dist\ZheweiTechBrain\*
```

### 檔案命名建議
```
ZheweiTechBrain_v1.0.0_Windows_x64.zip
```

格式：`產品名_版本號_平台_架構.擴展名`

## 🧪 測試打包結果

### 1. 清潔環境測試

在**未安裝 Python** 的電腦上測試：
1. 解壓縮打包檔案
2. 執行 `setup_wizard.bat` 配置
3. 執行 `啟動大腦.bat` 啟動
4. 瀏覽器訪問 http://localhost:8002

### 2. 功能驗證清單

- [ ] 系統正常啟動
- [ ] 配置向導可運行
- [ ] Web 介面可訪問
- [ ] AI 服務可連接
- [ ] WebSocket 通訊正常
- [ ] 靜態資源正確加載
- [ ] 登入認證功能正常

## 🐛 常見打包問題

### 問題 1: 缺少模組

**錯誤訊息**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解決方案**：
在 `brain_server.spec` 的 `hiddenimports` 中添加缺少的模組：
```python
hiddenimports=[
    'xxx',  # 添加缺少的模組
    # ...
],
```

### 問題 2: 靜態文件找不到

**錯誤訊息**：
```
FileNotFoundError: [Errno 2] No such file or directory: 'brain_workspace/static/index.html'
```

**解決方案**：
1. 檢查 `datas` 配置中的路徑
2. 確認源文件存在
3. 使用絕對路徑或相對於 spec 文件的路徑

### 問題 3: DLL 缺失

**錯誤訊息**：
```
The program can't start because xxx.dll is missing
```

**解決方案**：
1. 安裝 Visual C++ Redistributable
2. 在 `binaries` 中手動包含 DLL：
```python
binaries=[
    ('C:/path/to/xxx.dll', '.'),
],
```

### 問題 4: 打包檔案過大

**問題**：打包後超過 200MB

**優化方案**：
1. 排除不需要的模組（excludes）
2. 使用 UPX 壓縮：
```python
upx=True,
upx_exclude=[],
```
3. 考慮使用單文件模式（但啟動較慢）

## 🚀 進階打包選項

### 單文件模式

將所有文件打包成單一 .exe：

修改 `brain_server.spec`：
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 包含二進制文件
    a.zipfiles,  # 包含壓縮文件
    a.datas,     # 包含數據文件
    [],
    name='ZheweiTechBrain',
    debug=False,
    onefile=True,  # 啟用單文件模式
    # ...
)
```

⚠️ 注意：單文件模式啟動較慢，因為需要先解壓到臨時目錄。

### 添加圖標

1. 準備 .ico 文件（256x256）
2. 修改 spec：
```python
exe = EXE(
    # ...
    icon='icon.ico',  # 指定圖標
)
```

### 隱藏控制台窗口

如果不需要看到命令行：
```python
exe = EXE(
    # ...
    console=False,  # 隱藏控制台
    # ...
)
```

⚠️ 建議開發階段保持 `console=True` 以便查看錯誤信息。

## 📊 版本管理

### 版本號規範

使用語義化版本：`主版本.次版本.修訂號`

- **主版本**：重大架構變更
- **次版本**：新功能添加
- **修訂號**：錯誤修復

範例：
- `1.0.0` - 首次發布
- `1.1.0` - 添加新 AI 服務
- `1.1.1` - 修復登入錯誤

### 更新日誌

維護 `CHANGELOG.md` 記錄變更：
```markdown
## [1.1.0] - 2026-02-15
### 新增
- 支援 Claude 3.5 Sonnet
- 添加語音輸入功能

### 修復
- 修復 WebSocket 斷線問題
- 優化記憶體使用

### 變更
- 更新 Gemini API 版本
```

## 🔐 安全注意事項

### 1. 不要包含敏感資訊

確保打包時**不包含**：
- ❌ `.env` 文件（包含 API 金鑰）
- ❌ 用戶數據庫
- ❌ 日誌文件
- ❌ 個人配置

只包含：
- ✅ `.env.example`（範例配置）
- ✅ 程式碼
- ✅ 靜態資源

### 2. 代碼簽名（可選）

使用數位簽章增加信任度：
```python
exe = EXE(
    # ...
    codesign_identity='Your Certificate Name',
)
```

## 📚 相關文檔

- [PyInstaller 官方文檔](https://pyinstaller.org/)
- [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/)
- [Windows 應用程式分發](https://docs.microsoft.com/en-us/windows/apps/package/)

## 🎓 最佳實踐

1. **版本控制**：使用 Git 標籤標記發布版本
2. **自動化**：使用 CI/CD 自動化打包流程
3. **測試**：在多種 Windows 環境測試
4. **文檔**：保持使用說明更新
5. **反饋**：收集用戶反饋持續改進

## 🛟 支援與聯繫

打包相關問題請參考：
- GitHub Issues
- 技術文檔
- 開發團隊聯繫方式

---

**築未科技** | 讓 AI 觸手可及
