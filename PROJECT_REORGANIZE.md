# 築未科技 — 根目錄重整計畫

> 89 個 .py 檔案分類歸檔（增量執行，不破壞現有 import）

## 現狀：89 個 .py 散落根目錄

## 目標結構

```
d:\zhe-wei-tech\
├── core/                    # 核心服務（不可隨意動）
│   ├── ai_service.py
│   ├── brain_server.py
│   ├── agent_logic.py
│   ├── agent_memory.py
│   ├── agent_tools.py
│   ├── auth_manager.py
│   ├── role_manager.py
│   ├── smart_bridge.py
│   └── portal_server.py
│
├── services/                # 獨立微服務
│   ├── ai_api_proxy.py
│   ├── discord_bot.py
│   ├── memu_bridge.py
│   ├── monitoring_service.py
│   ├── monitoring_dashboard.py
│   ├── payment_ecpay.py
│   ├── website_server.py
│   └── remote_control_server.py
│
├── config/                  # 配置模組
│   ├── brain_data_config.py
│   ├── client_config.py
│   ├── cloud_port_config.py
│   ├── config_ai.py
│   ├── data_location_config.py
│   └── db_postgres.py
│
├── commercial/              # 商用模組
│   ├── license_manager.py
│   ├── kb_snapshot.py
│   ├── usage_metering.py
│   ├── ai_usage_tracker.py
│   └── ai_usage_alerts.py
│
├── ops/                     # 運維/監控/守護
│   ├── brain_guardian.py
│   ├── guardian_master.py
│   ├── self_check.py
│   ├── ops_notify.py
│   ├── net_audit.py
│   └── network_diagnostics.py
│
├── clients/                 # 外部 API 客戶端
│   ├── ollama_client.py
│   ├── gemini_client.py
│   ├── cursor_client.py
│   └── ollama_learning_controller.py
│
├── legacy/                  # 一次性/歷史腳本（可安全忽略）
│   ├── add_all_domains.py
│   ├── add_domains_now.py
│   ├── check_dns.py
│   ├── fix_dns.py
│   ├── fix_frontend_warnings.py
│   ├── check_frontend_errors.py
│   ├── generate_icons.py
│   ├── generate_password_hash.py
│   ├── archive_zhewei_to_folder.py
│   ├── comprehensive_test.py
│   ├── test_*.py
│   └── boost.py
│
├── ai_modules/              # 已存在 ✅
├── brain_modules/           # 已存在 ✅
├── brain_core/              # 已存在 ✅
├── construction_mgmt/       # 已存在 ✅
├── construction_brain/      # 已存在 ✅
├── mcp_servers/             # 已存在 ✅
└── tools/                   # 已存在 ✅
```

## 執行策略（增量、不破壞）

### Phase 1：低風險（legacy 腳本）
移動一次性腳本到 `legacy/`，這些檔案沒有被其他模組 import：
- add_all_domains.py, add_domains_now.py, check_dns.py, fix_dns.py
- fix_frontend_warnings.py, check_frontend_errors.py
- generate_icons.py, generate_password_hash.py
- archive_zhewei_to_folder.py, boost.py
- comprehensive_test.py, test_*.py

### Phase 2：中風險（config 模組）
移動配置檔到 `config/`，需在新目錄加 `__init__.py` 重導出。

### Phase 3：高風險（core 服務）
需同步更新 docker-compose.yml command 路徑 + 所有 import 語句。
**建議在 CI/CD 測試覆蓋率達 80% 後才執行。**

## 注意事項
- docker-compose.yml 的 command 引用了 `smart_bridge.py`, `portal_server.py` 等
- 13+ 個檔案 import from ai_service
- brain_server.py 是 Docker 入口點
- 移動前必須 grep 所有 import 引用並同步更新
