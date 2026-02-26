# 築未科技 — 檔案修改清單與部署計畫

## 1. 環境評估摘要

### 1.1 硬體配置
| 元件 | 型號 | 狀態 |
|------|------|------|
| CPU | Intel Core i7-14700 | ✅ 20核28緒，效能充足 |
| GPU | NVIDIA RTX 4060 Ti 8GB | ⚠️ VRAM 有限，SD 3.0 需升級 |
| RAM | 64GB DDR5 | ✅ 充裕，可載入多模型 |
| 儲存 | NVMe SSD | ✅ 快速載入 |

### 1.2 軟體環境
- Python 3.12+ (Jarvis_Training .venv312)
- Ollama (localhost:11434/11460)
- Docker Compose
- Cloudflare Tunnel

---

## 2. Smart Route 模型調度邏輯優化

### 2.1 當前配置 (ai_service.py)
```python
AI_COST_MODE = os.environ.get("AI_COST_MODE", "smart_route").strip().lower()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
```

### 2.2 優化目標
- 根據 VRAM 使用量動態分配模型
- 實現 i7-14700 自動偵測與優化
- 增強異常回報機制

### 2.3 待修改檔案
| 檔案 | 修改內容 | 優先級 |
|------|----------|--------|
| `ai_service.py` | 新增 VRAM 偵測與模型分配邏輯 | 高 |
| `ai_service.py` | 實作 i7-14700 CPU 優化參數 | 中 |
| `ai_service.py` | 增強錯誤回報與 fallback 機制 | 高 |

---

## 3. 具體檔案修改清單

### 3.1 AI 服務模組
| 檔案 | 修改類型 | 修改內容 | 狀態 |
|------|----------|----------|------|
| `ai_service.py` | 修改 | 新增 `SmartRouter` 類別，實作 VRAM 感知調度 | 待執行 |
| `ai_service.py` | 修改 | 新增 `detect_hardware_capabilities()` 函式 | 待執行 |
| `ai_service.py` | 修改 | 實作 `auto_retry_with_fallback()` 機制 | 待執行 |
| `ai_modules/ai_providers.py` | 修改 | 更新 Provider 介面以支援動態配置 | 待執行 |

### 3.2 監控與守護模組
| 檔案 | 修改類型 | 修改內容 | 狀態 |
|------|----------|----------|------|
| `brain_guardian.py` | 修改 | 新增 i7-14700 自動偵測與效能優化 | 待執行 |
| `brain_guardian.py` | 修改 | 實作異常回報自動修復流程 | 待執行 |
| `monitoring_service.py` | 修改 | 增強 GPU/CPU 監控指標 | 待執行 |

### 3.3 測試與部署模組
| 檔案 | 修改類型 | 修改內容 | 狀態 |
|------|----------|----------|------|
| `test_system.py` | 修改 | 新增 RS10 點雲測試案例 | 待執行 |
| `test_system.py` | 修改 | 新增 BIM 對比測試案例 | 待執行 |
| `test_system.py` | 修改 | 實作自動修復觸發機制 | 待執行 |
| `scripts/self_heal_test.bat` | 新建 | 一鍵自癒測試腳本 | 待執行 |

### 3.4 營建專業模組
| 檔案 | 修改類型 | 修改內容 | 狀態 |
|------|----------|----------|------|
| `organize_las_pointcloud.py` | 修改 | 實作 RS10 點雲自動讀取 | 待執行 |
| `point_cloud_config.py` | 修改 | 新增 RS10 特定配置 | 待執行 |
| `construction_mgmt/bim_compare.py` | 新建 | BIM 差異對比功能 | 待執行 |
| `construction_mgmt/excavation_monitor.py` | 新建 | 開挖監控模組 | 待執行 |

---

## 4. 一鍵自主部署與測試流程

### 4.1 部署腳本清單
```bash
# 腳本位置：scripts/
start_all.bat          # 啟動所有服務
deploy_all.bat         # 一鍵部署
self_heal_test.bat     # 自癒測試（新建）
run_tests.bat          # 執行測試（新建）
```

### 4.2 測試執行流程
```
1. 執行 test_system.py
2. 失敗 → 讀取 Error Log
3. 自主修復 → 重新測試
4. 通過 → 輸出報告
```

### 4.3 部署檢查清單
- [ ] Docker 服務運行正常
- [ ] brain_server API 可存取
- [ ] Ollama 模型載入完成
- [ ] ChromaDB 知識庫可查詢
- [ ] Discord Bot 連線正常
- [ ] GPU 加速可用

---

## 5. 優先執行順序

### Phase 1: 核心修復（這週）
| 順序 | 任務 | 檔案 | 預計時間 |
|------|------|------|----------|
| 1 | Smart Route 優化 | ai_service.py | 2 小時 |
| 2 | 自癒測試腳本 | scripts/self_heal_test.bat | 1 小時 |
| 3 | Error Log 整合 | brain_guardian.py | 1 小時 |

### Phase 2: 營建功能（下週）
| 順序 | 任務 | 檔案 | 預計時間 |
|------|------|------|----------|
| 4 | RS10 點雲讀取 | organize_las_pointcloud.py | 3 小時 |
| 5 | BIM 對比 | construction_mgmt/bim_compare.py | 4 小時 |
| 6 | 開挖監控 | construction_mgmt/excavation_monitor.py | 4 小時 |

### Phase 3: 測試與部署（完成後）
| 順序 | 任務 | 檔案 | 預計時間 |
|------|------|------|----------|
| 7 | 測試案例擴充 | test_system.py | 2 小時 |
| 8 | 一鍵部署腳本 | scripts/deploy_all.bat | 1 小時 |

---

## 6. Error Log 處理流程

### 6.1 錯誤記錄位置
- 主要：`zhewei_memory/Experience/Error_Logs.jsonl`
- 備援：`brain_workspace/logs/`

### 6.2 自主修復觸發條件
```python
if error_count > threshold:
    read_error_log()
    analyze_root_cause()
    generate_fix()
    apply_fix()
    rerun_test()
```

### 6.3 修復驗證標準
- Pytest 通過率 > 95%
- API 響應時間 < 3秒
- 無新增 Error Log 項目

---

## 7. 風險評估與對策

| 風險 | 機率 | 影響 | 對策 |
|------|------|------|------|
| VRAM 不足 | 中 | SD 3.0 失敗 | 降級至 SD 1.5 |
| API Key 過期 | 低 | 雲端服務中斷 | 啟用 MiniMax 備援 |
| Docker 崩潰 | 低 | 服務停止 | brain_guardian 自動重啟 |
| 網路斷線 | 中 | 外網不可達 | Contabo Failover 備援 |

---

## 8. 驗收標準

### 8.1 功能驗收
- [ ] Smart Route 正常運作
- [ ] RS10 點雲可自動讀取
- [ ] BIM 差異對比功能正常
- [ ] 開挖監控可運作

### 8.2 效能驗收
- [ ] API 響應時間 < 3秒
- [ ] GPU 利用率 > 60%
- [ ] 記憶體使用率 < 80%

### 8.3 穩定性驗收
- [ ] 72小時無崩潰
- [ ] Error Log 無新增 critical 項目
- [ ] 自動修復成功率 > 90%

---

*建立日期：2026-02-18*
*版本：1.0*
