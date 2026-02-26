import { Eye, Shield, Camera, AlertTriangle, BarChart3, Scan } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function VisionPage() {
  return (
    <ServicePageLayout
      title="視覺辨識系統"
      subtitle="AI Vision Detection"
      description="運用 YOLO + VLM 深度分析技術，自動檢測工地安全、品質缺陷，即時預警並生成標註報告。"
      icon={Eye}
      color="#3b82f6"
      bgColor="bg-blue-50"
      highlights={[
        'YOLO 物件偵測 + VLM 視覺語言模型',
        '工地安全帽、反光背心自動偵測',
        '施工品質缺陷自動標註',
        '即時預警通知（Ntfy 推播）',
        '自動生成標註報告與統計圖表',
      ]}
      features={[
        {
          icon: Scan,
          title: '物件偵測',
          desc: '基於 YOLO 模型，即時偵測工地人員、設備、安全裝備，準確率達 96.8%。',
        },
        {
          icon: Shield,
          title: '安全合規檢查',
          desc: '自動檢測安全帽、反光背心、安全帶等防護裝備佩戴情況，違規即時告警。',
        },
        {
          icon: AlertTriangle,
          title: '缺陷偵測',
          desc: '識別混凝土裂縫、鋼筋外露、滲水等施工品質問題，提前預防重大缺陷。',
        },
        {
          icon: Camera,
          title: 'VLM 圖片分析',
          desc: '透過 Gemini Vision 視覺語言模型，對工地照片進行深度語意分析與描述。',
        },
        {
          icon: BarChart3,
          title: '統計報表',
          desc: '自動彙整偵測結果，生成日報、週報、月報，追蹤安全與品質趨勢。',
        },
        {
          icon: Eye,
          title: '即時監控',
          desc: '支援攝影機串流即時分析，24/7 不間斷監控工地安全狀況。',
        },
      ]}
    />
  );
}
