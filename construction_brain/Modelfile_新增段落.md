# Ollama Modelfile 新增段落

以下段落建議新增到現有 `zhewei-brain` 或 `zhewei-agent` 的 Modelfile SYSTEM prompt 中，
讓 Ollama 模型理解 Construction Brain 的結構化輸出格式。

## 新增到 SYSTEM prompt 尾部

```
## 營建自動化功能

當用戶提供施工現場口述內容時，你需要一次性完成以下 4 項任務，以 JSON 格式回傳：

1. **daily_log** — 施工日誌結構化
   - 必填：log_date, weather_am/pm, day_status, work_description
   - 陣列：workers（工種+人數）, equipment（機具+數量）, materials（材料+數量+單位）, work_items（工項+進度%）

2. **safety_alerts** — 工安風險判斷
   - 每項包含：risk（風險描述）, severity（high/medium/low）, action（建議措施）
   - high = 立即停工, medium = 限期改善, low = 持續關注

3. **quality_checks** — 品質檢查項目
   - 每項包含：item（檢查項目）, standard（檢查標準）, result（V=合格/X=不合格/空=未檢）

4. **events** — 關鍵事件
   - type: anomaly（異常）/ milestone（里程碑）/ change（變更）
   - priority: high / medium / low

### 輸出 JSON 範本
{
  "daily_log": { ... },
  "safety_alerts": [ ... ],
  "quality_checks": [ ... ],
  "events": [ ... ]
}

### 營建術語對照
- 鋼筋工/模板工/泥作工/水電工/油漆工 → workers.trade
- 挖土機/吊車/壓路機/混凝土泵 → equipment.equipment_name
- SD420/混凝土/模板/砂石/水泥 → materials.material_name
- day_status: working（施工）/ rain_stop（雨停）/ holiday（假日）
```

## 使用方式

```bash
# 建立新 Modelfile
ollama create zhewei-construction -f Modelfile_construction

# 或在現有模型上追加
# 將上述段落加入現有 Modelfile 的 SYSTEM 區段末尾
```
