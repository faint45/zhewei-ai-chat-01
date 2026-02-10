@echo off
chcp 65001 >nul
cls
echo ================================================
echo     築未科技 - 自定義域名配置工具
echo ================================================
echo.

echo 🌐 域名配置選項：
echo.

echo 1. 🆓 免費二級域名（推薦）
echo     • zhuwei-tech.vercel.app（Vercel提供）
echo     • zhuwei-tech.netlify.app（Netlify提供）
echo     • 無需購買域名，立即可用
echo.

echo 2. 💰 購買自定義域名
echo     • zhuwei-tech.com（國際域名）
echo     • zhuwei-tech.cn（中國域名）
echo     • 築未科技.中國（中文域名）
echo.

echo 3. 🔄 配置現有域名
echo     • 如果您已有域名
echo     • 需要修改DNS記錄
echo.

choice /c 123 /n /m "請選擇：1)免費域名 2)購買域名 3)配置現有域名"
if errorlevel 3 goto existing
if errorlevel 2 goto purchase
if errorlevel 1 goto free

:free
echo.
echo 🆓 免費域名配置：
echo.
echo 📋 雲服務商提供的免費域名：
echo     • Vercel: zhuwei-tech.vercel.app
echo     • Netlify: zhuwei-tech.netlify.app
echo     • CloudBase: zhuwei-tech.tcloudbaseapp.com
echo.
echo 🔧 配置步驟：
echo     1. 部署到雲服務（已準備好）
echo     2. 自動獲得免費域名
echo     3. 無需額外配置
echo.
echo 💡 優點：完全免費，立即可用
echo ⚠️  缺點：域名較長，包含服務商名稱
echo.
goto end

:purchase
echo.
echo 💰 購買自定義域名：
echo.
echo 🌍 推薦域名註冊商：
echo     • 阿里雲（萬網）: https://wanwang.aliyun.com/
echo     • 騰訊雲: https://dnspod.cn/
echo     • GoDaddy: https://www.godaddy.com/
echo     • Namecheap: https://www.namecheap.com/
echo.
echo 📋 推薦域名：
echo     • zhuwei-tech.com（約¥60/年）
echo     • zhuwei-tech.cn（約¥30/年）
echo     • zhuwei.com（若可用，約¥500/年）
echo     • zhuwei.net（若可用，約¥100/年）
echo.
echo 🔧 購買步驟：
echo     1. 訪問域名註冊商網站
echo     2. 搜索並選擇合適的域名
echo     3. 完成購買和實名認證
echo     4. 配置DNS解析
echo.
start https://wanwang.aliyun.com/domain/
goto end

:existing
echo.
echo 🔄 配置現有域名：
echo.
echo 📋 DNS配置指南：
echo.
echo 如果您已有域名，需要配置DNS記錄：
echo.
echo 🔧 Vercel配置：
echo     • 記錄類型: CNAME
echo     • 主機名: www（或@）
echo     • 目標: cname.vercel-dns.com
echo.
echo 🔧 Netlify配置：
echo     • 記錄類型: CNAME
echo     • 主機名: www（或@）
echo     • 目標: your-site.netlify.app
echo.
echo 🔧 CloudBase配置：
echo     • 記錄類型: CNAME
echo     • 主機名: www（或@）
echo     • 目標: your-app.tcloudbaseapp.com
echo.
echo 💡 配置完成後，通常需要1-48小時生效
echo.
start https://vercel.com/docs/concepts/projects/custom-domains
goto end

:end
echo.
echo ✅ 域名配置指南已顯示
echo 💡 建議：先使用免費域名測試，確認功能正常後再購買自定義域名
echo.
pause