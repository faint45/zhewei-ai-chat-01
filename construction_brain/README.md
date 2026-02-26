# 🏗️ Construction Brain — 營建自動化大腦

> 築未科技核心模組：語音/照片 → 事件抽取 → 日報/工安/進度 → 自動輸出

## 架構

```
construction_brain/
├── core/
│   ├── extract_work_events.py    ← 語音/文字 → JSON 事件抽取（統一 prompt）
│   ├── ingest.py                 ← 語音+照片+文字入庫分類
│   ├── daily_report_writer.py    ← 施工日誌引擎（合併+LLM生成+DB寫入）
│   └── safety_engine.py          ← 工安檢查引擎（關鍵詞+YOLO+LLM三層）
├── schedule/
│   ├── schedule_engine.py        ← 進度管理引擎（排程+差異計算）
│   └── scurve_writer.py          ← S-Curve 數據+圖表輸出
├── knowledge/
│   ├── kb_ingest.py              ← 知識庫匯入（ChromaDB）
│   └── kb_query.py               ← 知識庫語意搜尋
├── integrations/
│   └── line_receiver.py          ← LINE Webhook 接收+自動回覆
├── auth/
│   └── license_validator.py      ← 離線授權驗證（複用 license_manager.py）
├── env.example                   ← 環境變數範本
├── requirements.txt              ← 依賴清單
├── setup.ps1                     ← Windows 一鍵安裝
├── Modelfile_新增段落.md          ← Ollama 模型 prompt 擴充
└── README.md
```

## 複用現有模組

| 功能 | 來源 | 備註 |
|------|------|------|
| 語音辨識 | `construction_mgmt/voice_service.py` | faster-whisper, GPU1 |
| YOLO 偵測 | `tools/vision_edge_service.py` | TensorRT 加速, GPU1 |
| LLM 推理 | `ai_service.py` + Ollama | qwen3:32b, GPU0 |
| 知識庫 | `Jarvis_Training/chroma_db` | 14,600+ 筆 |
| License | `license_manager.py` | HMAC-SHA256 簽章 |
| 推播 | `mod-ntfy-push.js` | Ntfy 即時通知 |

## 快速開始

```powershell
# 1. 安裝
powershell -ExecutionPolicy Bypass -File construction_brain\setup.ps1

# 2. 測試事件抽取
python -c "
from construction_brain.core.extract_work_events import extract_events
result = extract_events('今天晴天，鋼筋工5人綁紮三樓柱筋，模板工3人組立二樓牆模板，混凝土5立方澆置完成')
print(result)
"

# 3. 測試日報生成
python -c "
from construction_brain.core.daily_report_writer import DailyReportWriter
writer = DailyReportWriter(project_id='001', project_name='B棟新建工程')
# 加入語音事件
from construction_brain.core.extract_work_events import extract_events
events = extract_events('鋼筋工5人綁紮柱筋，安全帽都有戴')
writer.add_events(events)
report = writer.generate_report()
print(report['report_text'][:500])
"
```

## 核心流程

```
LINE 訊息 / APP 語音 / 手動輸入
         │
         ▼
    ┌─────────┐
    │  ingest  │  語音→faster-whisper / 照片→YOLO+VLM / 文字
    └────┬────┘
         │
         ▼
┌──────────────────┐
│ extract_events() │  單次 LLM 呼叫 → 日報+工安+品質+事件
└────┬───┬───┬────┘
     │   │   │
     ▼   ▼   ▼
  日報  工安  進度
  引擎  引擎  引擎
     │   │   │
     ▼   ▼   ▼
  JSON  警報  S-Curve
  報告  推送  圖表
```

## GPU 分工

```
RTX 5070 Ti (16GB) → GPU0 → LLM 推理（Ollama qwen3:32b）
RTX 4060 Ti (8GB)  → GPU1 → YOLO 偵測 + faster-whisper 語音辨識
```

## 授權等級

| 功能 | Free | Professional | Enterprise |
|------|:----:|:------------:|:----------:|
| 基礎日報 | ✅ | ✅ | ✅ |
| 語音辨識 | ✅ | ✅ | ✅ |
| 關鍵詞工安 | ✅ | ✅ | ✅ |
| LLM 日報生成 | ❌ | ✅ | ✅ |
| LLM 工安分析 | ❌ | ✅ | ✅ |
| 照片工安偵測 | ❌ | ✅ | ✅ |
| 知識庫匯入 | ❌ | ✅ | ✅ |
| 進度追蹤 | ❌ | ✅ | ✅ |
| S-Curve | ❌ | ✅ | ✅ |
| LINE 整合 | ❌ | ✅ | ✅ |
| 多工程（3個） | ❌ | ✅ | ✅ |
| 無限工程 | ❌ | ❌ | ✅ |
| Multi-LoRA | ❌ | ❌ | ✅ |
| API 存取 | ❌ | ❌ | ✅ |

## 環境變數

參見 `env.example`。主要設定：

```env
OLLAMA_BASE_URL=http://localhost:11460
CB_LLM_MODEL=qwen3:32b
WHISPER_DEVICE_INDEX=1    # GPU1 for Whisper
YOLO_DEVICE=1             # GPU1 for YOLO
```
