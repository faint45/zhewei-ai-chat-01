@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 雲服務部署方案
echo ================================================
echo.

echo 🌐 推薦的雲服務提供商：
echo.

echo 🚀 方案1：騰訊雲CloudBase（推薦）
echo     • 免費額度：1GB存儲 + 5GB流量/月
echo     • 部署簡單：一鍵部署
echo     • 國內訪問快
echo     • 無需端口轉發
echo.

echo 🌍 方案2：Vercel（國際）
echo     • 完全免費
echo     • 全球CDN加速
echo     • 自動SSL證書
echo     • 支持自定義域名
echo.

echo 💻 方案3：Netlify
echo     • 免費套餐
echo     • 簡單部署
echo     • GitHub集成
echo.

echo 📊 對比本地部署 vs 雲部署：
echo.
echo | 特性 | 本地部署 | 雲部署 |
echo |------|----------|--------|
echo | 穩定性 | 依賴本地網絡 | 99.9%% 可用性 |
echo | 訪問速度 | 依賴網絡環境 | 全球CDN加速 |
echo | 配置複雜度 | 高（端口轉發） | 低（一鍵部署） |
echo | 成本 | 免費（電費） | 有免費額度 |
echo.

echo 🔧 立即行動：
echo     1. 運行此腳本開啟雲部署配置嚮導
echo     2. 選擇雲服務提供商
echo     3. 上傳網站文件
echo     4. 獲取永久訪問地址
echo.

echo 💡 建議：對於企業官網，推薦使用雲服務確保穩定訪問
echo.

choice /c 123 /n /m "請選擇操作：1)騰訊雲 2)Vercel 3)Netlify"
if errorlevel 3 goto netlify
if errorlevel 2 goto vercel
if errorlevel 1 goto tcloud

:tcloud
echo.
echo 🚀 配置騰訊雲CloudBase...
echo     訪問：https://console.cloud.tencent.com/tcb
echo     創建環境 → 上傳靜態網站 → 獲取域名
echo.
goto end

:vercel
echo.
echo 🌍 配置Vercel...
echo     訪問：https://vercel.com/
echo     使用GitHub登錄 → 導入項目 → 部署
echo.
goto end

:netlify
echo.
echo 💻 配置Netlify...
echo     訪問：https://www.netlify.com/
echo     拖拽文件夾上傳 → 獲取域名
echo.

:end
echo ✅ 雲服務配置指南已顯示
echo 💡 建議優先考慮騰訊雲，國內訪問速度最佳
echo.
pause