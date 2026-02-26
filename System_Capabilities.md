# 築未科技 AI 系統自主能力規範

## 1. 自主編碼能力 (Autonomous Coding)

### 1.1 核心能力
- 自動讀取現有程式碼結構與風格
- 遵循專案命名慣例與架構模式
- 直接在檔案系統中建立與修改多個關聯檔案
- 確保資料庫與 API 邏輯一致性

### 1.2 禁止事項
- ❌ 要求使用者手動複製貼上程式碼
- ❌ 未確認需求直接假設實作方式
- ❌ 跳過 Implementation_Plan.md 直接編碼

---

## 2. 自動測試能力 (Automated Testing)

### 2.1 測試範疇
- **單元測試**：函式與模組功能驗證
- **整合測試**：API 端點與資料庫互動
- **回歸測試**：確保修改不破壞現有功能
- **領域測試**：營建專業邏輯驗證

### 2.2 測試執行流程
```
程式碼修改 → 自動執行測試腳本 → 失敗則自主修復 → 直到測試通過
```

### 2.3 測試腳本位置
- `test_system.py` — 系統整合測試
- `scripts/self_heal_test.bat` — 自癒測試
- `pytest` — 框架測試（如已安裝）

---

## 3. 自主修復能力 (Self-Healing)

### 3.1 修復觸發條件
- 測試失敗 (Pytest)
- Error Log 記錄錯誤
- Runtime 例外狀況

### 3.2 修復流程
```
1. 讀取 Error Log (zhewei_memory/Experience/Error_Logs.jsonl)
2. 分析錯誤原因
3. 重新推理正確實作方式
4. 修正程式碼
5. 重新執行測試
6. 直到通過為止
```

### 3.3 異常回報機制
- 自動偵測 i7-14700 系統異常
- 記錄至 Error Log
- 輸出修復建議

---

## 4. 營建專業任務範疇

### 4.1 數據模組 (Data Modules)
| 模組 | 功能 | 狀態 |
|------|------|------|
| `organize_las_pointcloud.py` | RS10 點雲資料 (LAS) 自動讀取 | 待實作 |
| `point_cloud_config.py` | 點雲配置管理 | 待實作 |
| `construction_mgmt/database.py` | 工地資料管理 | ✅ 已完成 |

### 4.2 監控模組 (Monitoring Modules)
| 模組 | 功能 | 狀態 |
|------|------|------|
| `monitoring_service.py` | 系統監控 | ✅ 已完成 |
| `brain_guardian.py` | AI 系統守護者 | ✅ 已完成 |
| `health_check.py` | 健康檢查 | 待整合 |

### 4.3 硬體適配 (Hardware Adaptation)
| 項目 | 配置 | 說明 |
|------|------|------|
| CPU | i7-14700 | 20核28緒，自動偵測與優化 |
| GPU | RTX 4060 Ti 8GB | CUDA 加速，模型分配 |
| RAM | 64GB | 大模型載入優化 |
| 儲存 | NVMe SSD | 快速載入點雲與模型 |

---

## 5. 工地現場專業功能

### 5.1 高風險作業監控
| 功能 | API | 狀態 |
|------|-----|------|
| 開挖監控 | `/api/construction/excavation` | 待實作 |
| 擋土支撐 | `/api/construction/retaining` | 待實作 |
| 異常回報 | `/api/construction/alert` | 待實作 |

### 5.2 影像串接
| 功能 | API | 狀態 |
|------|-----|------|
| 工地影像 API | `/api/vision/stream` | 待實作 |
| 即時分析 | `/api/vision/realtime` | 待實作 |

### 5.3 BIM 與點雲對比
| 功能 | API | 狀態 |
|------|-----|------|
| 特徵提取 | `/api/bim/extract` | 待實作 |
| BIM 差異對比 | `/api/bim/compare` | 待實作 |
| RS10 點雲讀取 | `/api/pointcloud/rs10` | 待實作 |

---

## 6. Smart Route 模型調度優化

### 6.1 環境配置
```json
{
  "cpu": "i7-14700",
  "gpu": "RTX 4060 Ti 8GB",
  "ram": "64GB",
  "mode": "smart_route"
}
```

### 6.2 模型分配策略
| 任務類型 | 模型 | VRAM 需求 | 優先級 |
|----------|------|-----------|--------|
| 思考型 (Think) | gemini-2.5-flash | 0 (雲端) | 1 |
| 執行型 (Execute) | qwen3:8b | ~6GB | 1 |
| 視覺分析 | moondream | ~4GB | 2 |
| 生圖 | SD 1.5 | ~4GB | 3 |
| 備援 | MiniMax-M2.5 | 0 (雲端) | 4 |

### 6.3 調度邏輯優化
```
1. 自動偵測 GPU VRAM 使用量
2. 根據任務類型分配模型
3. VRAM 不足時自動降級或使用雲端備援
4. 記錄效能指標供優化參考
```

---

## 7. 一鍵部署與測試流程

### 7.1 部署腳本清單
| 腳本 | 功能 | 位置 |
|------|------|------|
| `start_all.bat` | 啟動所有服務 | `scripts/` |
| `self_heal_test.bat` | 自癒測試 | `scripts/` |
| `deploy_all.bat` | 一鍵部署 | `scripts/` |

### 7.2 測試執行流程
```bash
# 1. 執行系統測試
python test_system.py

# 2. 執行自癒測試
scripts/self_heal_test.bat

# 3. 回報結果
# 失敗 → 自主修復 → 重新測試
# 成功 → 輸出報告
```

### 7.3 部署檢查清單
- [ ] Docker 服務運行正常
- [ ] brain_server API 可存取
- [ ] Ollama 模型載入完成
- [ ] ChromaDB 知識庫可查詢
- [ ] Discord Bot 連線正常

---

## 8. 系統評估標準

### 8.1 可行性評估指標
| 指標 | 評估標準 | 當前狀態 |
|------|----------|----------|
| 回應時間 | < 3秒 | ✅ |
| 可用率 | > 99% | ✅ |
| 錯誤率 | < 1% | ⚠️ |
| 修復時間 | < 5分鐘 | ⚠️ |

### 8.2 下一步行動
1. 完成 RS10 點雲模組實作
2. 整合工地影像 API
3. 實作 BIM 差異對比功能
4. 建立完整測試覆蓋率報告

---

## 9. 檔案修改清單

### 9.1 待修改檔案
| 檔案 | 修改內容 | 優先級 |
|------|----------|--------|
| `ai_service.py` | Smart Route 優化 | 高 |
| `organize_las_pointcloud.py` | RS10 點雲讀取 | 高 |
| `point_cloud_config.py` | 配置更新 | 中 |
| `test_system.py` | 測試案例擴充 | 高 |
| `brain_guardian.py` | 異常回報增強 | 中 |

### 9.2 待建立檔案
| 檔案 | 功能 | 優先級 |
|------|------|--------|
| `construction_mgmt/bim_compare.py` | BIM 差異對比 | 中 |
| `construction_mgmt/excavation_monitor.py` | 開挖監控 | 中 |
| `scripts/self_heal_test.bat` | 自癒測試腳本 | 高 |

---

## 10. 執行狀態追蹤

| 任務 | 狀態 | 負責 |
|------|------|------|
| Smart Route 優化 | 進行中 | AI 系統 |
| RS10 點雲讀取 | 待啟動 | AI 系統 |
| 一鍵測試部署 | 待啟動 | AI 系統 |
| 自主修復機制 | 待啟動 | AI 系統 |

---

*建立日期：2026-02-18*
*版本：1.0*
