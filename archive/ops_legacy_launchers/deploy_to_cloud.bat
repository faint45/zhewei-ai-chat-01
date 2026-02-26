@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 雲端一鍵部署系統
echo ================================================
echo.

setlocal enabledelayedexpansion

:menu
echo 🌐 請選擇雲服務提供商：
echo.
echo 1) 🚀 Vercel（國際，推薦）
echo     • 完全免費
echo     • 全球CDN加速
echo     • 自動SSL證書
echo.
echo 2) 🇨🇳 騰訊雲CloudBase（國內，推薦）
echo     • 國內訪問速度快
echo     • 免費額度充足
echo     • 中文界面
echo.
echo 3) 💻 Railway（開發者友好）
echo     • Docker支持
echo     • 數據庫集成
echo     • 自動擴展
echo.
echo 4) 📊 顯示雲端口配置信息
echo.
echo 5) 🔧 生成雲部署配置文件
echo.

choice /c 12345 /n /m "請選擇操作（1-5）："

if errorlevel 5 goto generate_config
if errorlevel 4 goto show_info
if errorlevel 3 goto railway
if errorlevel 2 goto cloudbase
if errorlevel 1 goto vercel

:vercel
echo.
echo 🚀 配置Vercel雲部署...
echo.
echo 📝 部署步驟：
echo   1. 訪問 https://vercel.com/
echo   2. 使用GitHub賬號登錄
echo   3. 點擊 "New Project"
echo   4. 導入當前文件夾
echo   5. 等待自動部署完成
echo.
echo 🔗 您將獲得類似以下的永久訪問地址：
echo   • API接口: https://zhewei-ai.vercel.app/v1/execute
echo   • 管理面板: https://zhewei-ai.vercel.app/dashboard
echo   • 文檔: https://zhewei-ai.vercel.app/docs
echo.
echo 💡 提示：Vercel會自動處理端口和SSL證書
echo.
goto end

:cloudbase
echo.
echo 🇨🇳 配置騰訊雲CloudBase...
echo.
echo 📝 部署步驟：
echo   1. 訪問 https://console.cloud.tencent.com/tcb
echo   2. 創建新環境（選擇免費套餐）
echo   3. 上傳項目文件
echo   4. 配置雲函數
echo   5. 綁定自定義域名（可選）
echo.
echo 🔗 您將獲得類似以下的訪問地址：
echo   • API接口: https://your-enviroment.service.tcloudbase.com/v1/execute
echo   • 管理面板: https://your-enviroment.service.tcloudbase.com/dashboard
echo.
echo 💡 提示：CloudBase自動處理國內網絡加速
echo.
goto end

:railway
echo.
echo 💻 配置Railway...
echo.
echo 📝 部署步驟：
echo   1. 訪問 https://railway.app/
echo   2. 使用GitHub賬號登錄
echo   3. 創建新項目
echo   4. 連接GitHub倉庫
echo   5. 自動部署
echo.
echo 🔗 您將獲得類似以下的訪問地址：
echo   • 主服務: https://your-project.up.railway.app
echo   • API接口: https://your-project.up.railway.app/v1/execute
echo.
echo 💡 提示：Railway支持Docker和數據庫集成
echo.
goto end

:show_info
echo.
echo 📊 雲端口配置信息：
echo.
echo 🏢 VERCEL:
echo   端口: 自動分配（80/443）
echo   協議: HTTPS
echo   特性: 全球CDN、自動SSL、無需端口配置
echo.
echo 🏢 CLOUDBASE:
echo   端口: 自動分配（80/443）
echo   協議: HTTPS
echo   特性: 國內加速、自動備份、中文支持
echo.
echo 🏢 RAILWAY:
echo   端口: 動態分配（$PORT環境變量）
echo   協議: HTTPS
echo   特性: Docker支持、自動擴展、數據庫集成
echo.
echo 💡 雲端優勢:
echo   • 無需手動配置路由器端口轉發
echo   • 自動HTTPS加密
echo   • 全球/國內CDN加速
echo   • 99.9%%服務可用性
echo.
goto end

:generate_config
echo.
echo 🔧 生成雲部署配置文件...
python cloud_port_config.py
echo.
echo ✅ 配置文件已生成：
echo   - vercel_api.json
echo   - cloudbase.json
echo   - railway.toml
echo   - .env.cloud
echo.
echo 📁 您可以將這些文件上傳到對應的雲平台
echo.
goto end

:end
echo.
echo ================================================
echo 🌟 築未科技雲端部署指南完成
echo ================================================
echo.
echo 💡 下一步行動建議：
echo   1. 選擇一個雲服務提供商
echo   2. 按照步驟部署
echo   3. 測試API接口
echo   4. 配置機器人使用雲端地址
echo.
echo 🔗 統一API系統特性：
echo   • Unified API: 單一/v1/execute接口
echo   • Auth Manager: 統一用戶驗證
echo   • Context Bridge: 跨平台對話連續性
echo.
pause