"""
築未科技 — 點雲斷面 AI 分析器（本地 Ollama）
使用本地模型對斷面進行智慧判讀，0 雲端 token 消耗。

功能：
  - 斷面特徵描述（結構形態、尺寸摘要）
  - 工程問題偵測（裂縫、變形、偏移）
  - 施工建議生成
  - 多斷面比較報告
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11460"
DEFAULT_MODEL = "zhewei-brain-v5-structured"
FALLBACK_MODEL = "zhewei-brain-v5"


@dataclass
class AnalysisReport:
    """AI 分析報告"""
    section_type: str
    position: float
    summary: str = ""
    features: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    model_used: str = ""
    raw_response: str = ""


def analyze_section(
    section_result,
    model: str = DEFAULT_MODEL,
    context: str = "",
) -> AnalysisReport:
    """
    使用本地 Ollama 模型分析斷面。

    Args:
        section_result: SectionResult 物件
        model: Ollama 模型名稱
        context: 額外上下文（工程名稱、位置描述等）
    Returns:
        AnalysisReport
    """
    # 準備斷面統計資料
    stats = _compute_section_stats(section_result)
    prompt = _build_analysis_prompt(section_result, stats, context)

    report = AnalysisReport(
        section_type=section_result.section_type.value,
        position=section_result.position,
        measurements=stats,
    )

    # 呼叫本地 Ollama
    try:
        response = _call_ollama(prompt, model)
        report.model_used = model
        report.raw_response = response

        # 解析回應
        parsed = _parse_response(response)
        report.summary = parsed.get("summary", response[:200])
        report.features = parsed.get("features", [])
        report.issues = parsed.get("issues", [])
        report.recommendations = parsed.get("recommendations", [])

    except Exception as e:
        logger.warning(f"Ollama 分析失敗 ({model}): {e}，嘗試 fallback")
        try:
            response = _call_ollama(prompt, FALLBACK_MODEL)
            report.model_used = FALLBACK_MODEL
            report.raw_response = response
            parsed = _parse_response(response)
            report.summary = parsed.get("summary", response[:200])
            report.features = parsed.get("features", [])
            report.issues = parsed.get("issues", [])
            report.recommendations = parsed.get("recommendations", [])
        except Exception as e2:
            logger.error(f"Ollama 完全失敗: {e2}，使用規則式分析")
            report = _rule_based_analysis(section_result, stats, report)

    return report


def compare_sections(
    results: list,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    多斷面比較分析。

    Args:
        results: SectionResult 列表
        model: Ollama 模型
    Returns:
        比較報告文字
    """
    if not results:
        return "無斷面資料可比較"

    summaries = []
    for r in results:
        stats = _compute_section_stats(r)
        summaries.append({
            "type": r.section_type.value,
            "position": r.position,
            "width": stats.get("width", 0),
            "height": stats.get("height", 0),
            "n_points": r.n_points,
            "n_contours": len(r.contours),
            "area": stats.get("area", 0),
        })

    prompt = f"""你是營建工程的點雲分析專家。請比較以下 {len(summaries)} 個斷面的差異：

{json.dumps(summaries, indent=2, ensure_ascii=False)}

請分析：
1. 各斷面的形態差異
2. 尺寸變化趨勢
3. 是否有異常或需注意的地方
4. 施工品質評估建議

用繁體中文回答，簡潔扼要。"""

    try:
        return _call_ollama(prompt, model)
    except Exception:
        return _rule_based_comparison(summaries)


def _compute_section_stats(result) -> dict:
    """計算斷面統計值"""
    stats = {}
    if result.n_points == 0:
        return stats

    pts = result.points_2d
    stats["n_points"] = result.n_points
    stats["width"] = float(pts[:, 0].max() - pts[:, 0].min())
    stats["height"] = float(pts[:, 1].max() - pts[:, 1].min())
    stats["centroid_x"] = float(pts[:, 0].mean())
    stats["centroid_y"] = float(pts[:, 1].mean())
    stats["std_x"] = float(pts[:, 0].std())
    stats["std_y"] = float(pts[:, 1].std())
    stats["n_contours"] = len(result.contours)

    # 面積估算（凸包）
    try:
        from scipy.spatial import ConvexHull
        if len(pts) >= 3:
            hull = ConvexHull(pts)
            stats["area"] = float(hull.volume)  # 2D 凸包 volume = area
            stats["perimeter"] = float(hull.area)  # 2D 凸包 area = perimeter
    except Exception:
        pass

    return stats


def _build_analysis_prompt(result, stats: dict, context: str) -> str:
    """構建分析 prompt"""
    type_names = {
        "plan": "平面圖（水平切面）",
        "elev_x": "X方向立面圖",
        "elev_y": "Y方向立面圖",
        "cross": "剖面圖",
    }
    section_name = type_names.get(result.section_type.value, result.section_type.value)

    prompt = f"""你是營建工程的點雲斷面分析專家。請分析以下斷面資料：

## 斷面資訊
- 類型：{section_name}
- 位置：{result.position:.2f} 公尺
- 點數：{stats.get('n_points', 0):,}
- 寬度：{stats.get('width', 0):.3f} m
- 高度：{stats.get('height', 0):.3f} m
- 面積：{stats.get('area', 0):.3f} m²
- 周長：{stats.get('perimeter', 0):.3f} m
- 輪廓數：{stats.get('n_contours', 0)}
- 質心：({stats.get('centroid_x', 0):.2f}, {stats.get('centroid_y', 0):.2f})
"""
    if context:
        prompt += f"\n## 額外資訊\n{context}\n"

    prompt += """
請以 JSON 格式回應（繁體中文）：
{
  "summary": "一句話描述此斷面的主要特徵",
  "features": ["特徵1", "特徵2"],
  "issues": ["可能的問題1"],
  "recommendations": ["建議1"]
}
只輸出 JSON，不要加其他文字。"""

    return prompt


def _call_ollama(prompt: str, model: str, timeout: int = 30) -> str:
    """呼叫本地 Ollama API"""
    import urllib.request
    import urllib.error

    url = f"{OLLAMA_URL}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Ollama 未啟動或連線失敗: {e}")
    except Exception as e:
        raise RuntimeError(f"Ollama 呼叫失敗: {e}")


def _parse_response(text: str) -> dict:
    """解析 Ollama 回應的 JSON"""
    # 嘗試直接解析
    text = text.strip()

    # 移除 markdown code block
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # 嘗試找 JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 嘗試找 { } 區塊
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return {"summary": text[:300]}


def _rule_based_analysis(result, stats: dict, report: AnalysisReport) -> AnalysisReport:
    """規則式 fallback 分析（無需 AI）"""
    report.model_used = "rule_based"
    w = stats.get("width", 0)
    h = stats.get("height", 0)
    area = stats.get("area", 0)
    n_contours = stats.get("n_contours", 0)

    report.summary = f"斷面尺寸 {w:.2f}×{h:.2f}m，面積 {area:.2f}m²，{n_contours} 條輪廓線"

    if w > 0 and h > 0:
        ratio = w / h
        if ratio > 3:
            report.features.append("寬扁形斷面（可能為道路或平台）")
        elif ratio < 0.33:
            report.features.append("窄高形斷面（可能為柱或牆）")
        else:
            report.features.append("均勻比例斷面")

    if n_contours == 0:
        report.issues.append("未檢測到輪廓線，可能點密度不足或降噪過度")
        report.recommendations.append("建議增加切片厚度或降低降噪強度")
    elif n_contours > 5:
        report.issues.append("輪廓線過多，可能存在雜訊或複雜結構")

    if result.n_points < 50:
        report.issues.append("切面點數過少，分析結果可能不準確")
        report.recommendations.append("建議調整切面位置到點密度較高的區域")

    return report


def _rule_based_comparison(summaries: list) -> str:
    """規則式比較分析"""
    lines = ["## 多斷面比較報告\n"]

    widths = [s["width"] for s in summaries if s["width"] > 0]
    heights = [s["height"] for s in summaries if s["height"] > 0]

    if widths:
        lines.append(f"- 寬度範圍: {min(widths):.2f} ~ {max(widths):.2f} m")
        lines.append(f"- 寬度變異: {np.std(widths):.3f} m")
    if heights:
        lines.append(f"- 高度範圍: {min(heights):.2f} ~ {max(heights):.2f} m")
        lines.append(f"- 高度變異: {np.std(heights):.3f} m")

    for s in summaries:
        lines.append(f"\n### {s['type']} @ {s['position']:.1f}m")
        lines.append(f"  寬={s['width']:.2f}m 高={s['height']:.2f}m 點數={s['n_points']}")

    return "\n".join(lines)
