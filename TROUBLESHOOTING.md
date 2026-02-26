# 築未科技大腦 - 故障排除指南

## 🐛 打包問題

### 問題 1: "pyinstaller is not recognized"

**症狀**：
```
'pyinstaller' is not recognized as an internal or external command
```

**原因**：PyInstaller 未添加到系統 PATH

**解決方案**：
使用 `build_simple.bat` 替代 `build_installer.bat`，或手動執行：
```bash
python -m PyInstaller brain_server.spec
```

---

### 問題 2: 缺少隱藏導入

**症狀**：
```
ModuleNotFoundError: No module named 'xxx'
```

**原因**：動態導入的模組未被 PyInstaller 檢測到

**解決方案**：
在打包命令中添加：
```bash
python -m PyInstaller --hidden-import=模組名稱 brain_server.py
```

或在 `brain_server.spec` 的 `hiddenimports` 列表中添加。

---

### 問題 3: 靜態文件未打包

**症狀**：
```
FileNotFoundError: brain_workspace/static/index.html
```

**原因**：靜態資源路徑配置錯誤

**解決方案**：
1. 確認 `brain_workspace/static` 目錄存在
2. 檢查 spec 文件中的 `datas` 配置
3. Windows 使用分號 `;`，Linux/Mac 使用冒號 `:`：
   ```bash
   # Windows
   --add-data="源路徑;目標路徑"

   # Linux/Mac
   --add-data="源路徑:目標路徑"
   ```

---

### 問題 4: 打包檔案過大（>500MB）

**原因**：包含了不必要的依賴

**優化方案**：
1. 使用虛擬環境打包（只安裝必要依賴）
2. 排除不需要的模組：
   ```bash
   python -m PyInstaller --exclude-module=tkinter --exclude-module=matplotlib brain_server.py
   ```
3. 啟用 UPX 壓縮（需另外下載 UPX）

---

## 🚀 運行問題

### 問題 5: 啟動後立即閃退

**診斷步驟**：
1. 在命令行啟動查看錯誤：
   ```bash
   cd dist\ZheweiTechBrain
   ZheweiTechBrain.exe
   ```

2. 常見原因：
   - 缺少 `.env` 文件 → 複製 `.env.example` 為 `.env`
   - 端口被占用 → 修改端口或結束占用進程
   - 權限不足 → 以管理員身份運行

---

### 問題 6: AI 服務無法連接

**症狀**：對話無回應或報錯

**檢查清單**：
- [ ] API 金鑰是否正確填寫在 `.env`
- [ ] 網路連接是否正常
- [ ] 防火牆是否阻擋
- [ ] Ollama 是否正在運行（如使用本地 AI）

**測試命令**：
```bash
# 測試 Ollama
curl http://localhost:11434/api/tags

# 測試網路
ping 8.8.8.8
```

---

### 問題 7: 無法訪問管理介面

**症狀**：瀏覽器顯示無法連接

**檢查步驟**：
1. 確認服務正在運行（查看控制台輸出）
2. 確認端口正確（預設 8002）
3. 嘗試不同瀏覽器
4. 檢查防火牆設置
5. 確認使用正確的 URL：
   - `http://localhost:8002`（不是 https）
   - `http://127.0.0.1:8002`（替代地址）

---

## 🔧 配置問題

### 問題 8: 忘記管理員密碼

**解決方案**：
1. 編輯 `.env` 文件
2. 修改或添加：
   ```
   ADMIN_USER=admin
   ADMIN_PASSWORD=新密碼
   ```
3. 重啟系統

---

### 問題 9: 資料目錄權限錯誤

**症狀**：
```
PermissionError: [Errno 13] Permission denied
```

**解決方案**：
1. 選擇有寫入權限的目錄（如 `D:\brain_workspace`）
2. 以管理員身份運行
3. 檢查防毒軟體是否阻擋

---

## 🌐 網路問題

### 問題 10: 外部無法訪問

**需求**：區域網路其他設備訪問

**配置步驟**：
1. 修改 `brain_server.py`：
   ```python
   uvicorn.run(app, host="0.0.0.0", port=8002)
   ```

2. 配置防火牆規則：
   ```bash
   netsh advfirewall firewall add rule name="Brain" dir=in action=allow protocol=TCP localport=8002
   ```

3. 查找本機 IP：
   ```bash
   ipconfig | findstr IPv4
   ```

4. 其他設備訪問：`http://你的IP:8002`

---

## 📦 依賴問題

### 問題 11: 依賴安裝失敗

**症狀**：
```
ERROR: Could not install packages due to an OSError
```

**解決方案**：
1. 使用管理員權限執行命令提示字元
2. 升級 pip：
   ```bash
   python -m pip install --upgrade pip
   ```
3. 清除快取：
   ```bash
   python -m pip cache purge
   ```
4. 重新安裝：
   ```bash
   python -m pip install -r requirements-brain.txt --user
   ```

---

### 問題 12: DLL 缺失錯誤

**症狀**：
```
The program can't start because xxx.dll is missing
```

**解決方案**：
安裝 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## 🎯 性能問題

### 問題 13: 響應速度慢

**優化建議**：
1. 使用更快的 AI 服務（Groq 速度最快）
2. 減少文檔上下文長度
3. 關閉不需要的功能
4. 使用本地 Ollama（需要好的 GPU）

---

### 問題 14: 記憶體使用過高

**解決方案**：
1. 使用較小的模型
2. 限制並發連接數
3. 定期重啟服務
4. 升級系統記憶體

---

## 🔍 除錯技巧

### 啟用詳細日誌

編輯 `brain_server.py`，添加：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看日誌文件

日誌位置：
- Windows: `logs/brain.log`
- 查看最新日誌：
  ```bash
  type logs\brain.log | more
  ```

### 測試模式啟動

```bash
python brain_server.py --reload --log-level debug
```

---

## 📞 獲取幫助

如果以上方法都無法解決問題：

1. **收集信息**：
   - 錯誤信息截圖
   - 日誌文件內容
   - 系統信息（Windows 版本、Python 版本）
   - `.env` 配置（隱藏敏感信息）

2. **尋求支援**：
   - GitHub Issues
   - 技術支援郵件
   - 用戶社群

3. **臨時替代方案**：
   - 使用開發模式：`python brain_server.py`
   - 使用線上版本（如已部署）
   - 切換到備用 AI 服務

---

## ✅ 預防性維護

定期執行：
```bash
# 更新依賴
python -m pip install --upgrade -r requirements-brain.txt

# 清理快取
python -m pip cache purge

# 檢查系統健康
python system_health_check.py

# 備份配置
copy .env .env.backup
```

---

**提示**：大多數問題都能透過重新安裝依賴或重啟系統解決。遇到問題不要慌，按照本指南逐步排查。
