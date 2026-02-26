import { Code2, Play, Wand2, Bug, Zap, Terminal } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function CodeSimPage() {
  return (
    <ServicePageLayout
      title="CodeSim 代碼模擬器"
      subtitle="Online Code Simulator"
      description="線上程式碼執行環境，支援 Python / JavaScript / TypeScript，內建 AI 程式碼分析與優化。"
      icon={Code2}
      color="#f97316"
      bgColor="bg-orange-50"
      ctaText="開始使用"
      ctaLink="/codesim"
      highlights={[
        '支援 Python / JavaScript / TypeScript',
        'AI 程式碼分析與優化建議',
        '即時執行與結果預覽',
        '30 秒安全沙箱超時保護',
        '專案管理與檔案系統',
      ]}
      features={[
        {
          icon: Play,
          title: '即時執行',
          desc: '在瀏覽器中直接執行 Python、JavaScript、TypeScript 程式碼，即時查看輸出結果。',
        },
        {
          icon: Wand2,
          title: 'AI 程式碼生成',
          desc: '描述需求，AI 自動生成程式碼。支援工程計算、資料處理、自動化腳本等場景。',
        },
        {
          icon: Bug,
          title: 'AI 除錯修復',
          desc: '貼上有問題的程式碼，AI 自動分析錯誤原因並提供修復建議。',
        },
        {
          icon: Zap,
          title: '效能優化',
          desc: 'AI 分析程式碼效能瓶頸，提供優化建議，提升執行速度與記憶體使用效率。',
        },
        {
          icon: Terminal,
          title: '安全沙箱',
          desc: '所有程式碼在隔離沙箱中執行，30 秒超時保護，確保系統安全穩定。',
        },
        {
          icon: Code2,
          title: '專案管理',
          desc: '支援多專案管理、檔案系統、版本記錄，方便組織和管理程式碼片段。',
        },
      ]}
    />
  );
}
